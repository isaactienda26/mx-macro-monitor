"""
MX Macro Monitor — 60-second video for LinkedIn (4:5, 1080×1350, 30 fps).

Pipeline
  1. `python src/video.py script`  -> bulletins/video/script.json: one narration line per scene,
     built from data/latest.json (every figure comes from the snapshot).
  2. Narration and music are generated with ElevenLabs and saved as
     bulletins/video/vo_<scene>.mp3 and bulletins/video/music.mp3.
  3. `python src/video.py render`  -> bulletins/video/mx_macro_monitor_n<N>.mp4
     Scene lengths follow the narration clips; captions are burned in for muted autoplay.

Design: same tokens, logo and HarfBuzz typesetting as the carousel (src/brand.py, src/typeset.py).
Sign convention: negative = the currency weakens (docs/METODOLOGIA.md §6).
"""

from __future__ import annotations

import json
import math
import subprocess
import sys
from dataclasses import dataclass
from multiprocessing import Pool
from pathlib import Path
from typing import Callable, Dict, List

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import calendario  # noqa: E402
from brand import (BLUE, BLUE_LT, DISPLAY, GREEN, INK, MUTED, OCHRE, PAPER, RED, RULE, SANS, SERIF_D,  # noqa: E402
                   WHITE, draw_logo, draw_mark)
from config import AUTHOR, DATA_DIR, OUTPUT_DIR, RAW_DIR  # noqa: E402
from magazine import CTX, EMAIL, MES_L, Page, n, track  # noqa: E402

FPS = 30
W, H, M = 1080, 1350, 72
CW = W - 2 * M
OUT = OUTPUT_DIR / "video"
GAP = 0.30            # silence between scenes (s)
TAIL = 1.5            # hold on the last frame (s)
STATE = {"estable": ("Estable", GREEN), "vigilancia": ("Vigilancia", OCHRE), "tension": ("Tensión", RED)}


# --- easing --------------------------------------------------------------------------------------
def clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


def ease(x: float) -> float:
    x = clamp(x)
    return 1 - (1 - x) ** 3


def seg(t: float, a: float, b: float) -> float:
    """Progress 0..1 of t inside [a, b], eased."""
    return ease((t - a) / max(b - a, 1e-6))


# --- data & script --------------------------------------------------------------------------------
def snapshot() -> dict:
    return json.loads((DATA_DIR / "latest.json").read_text(encoding="utf-8"))


def fmt_pesos(x: float) -> str:
    return f"{x:,.0f}"


def build_script(s: dict) -> List[dict]:
    """Narration per scene. Plain words for non-economists; one figure per sentence."""
    f, v = s["fx"], s["value_add"]
    rk, db, sc, ic, pr = v["fx_rank"], v["dollar"], v["thermo_score"], v["import_cost"], v["peers"]
    num = s.get("edition", 1)
    up = f["chg_1w_pct"] > 0
    since = pd.Timestamp(f["largest_since"]) if f.get("largest_since") else None
    worse = pd.Series(pd.to_datetime([w for w in rk.get("worse_dates", [])])) if rk.get("worse_dates") else None
    red = [r["key"] for r in v["thermometer"] if r["state"] == "tension"]
    red_es = {"fx": "el tipo de cambio", "expectations": "las expectativas de inflación", "inflation": "la inflación",
              "core": "la inflación subyacente", "real_rate": "la tasa real", "activity": "la actividad"}
    mx = next(r for r in pr["rows"] if r["c"] == "MX") if pr else None
    above = [r["c"] for r in pr["rows"][: pr["mx_rank"] - 1]] if pr else []
    names = {"BR": "Brasil", "CO": "Colombia", "CL": "Chile", "PE": "Perú", "US": "Estados Unidos"}
    nxt = calendario.issue_date(num + 1)
    dia = calendario.weekday(nxt, "es")
    ordw = ["", "primero", "segundo", "tercero", "cuarto", "quinto", "sexto"]

    hook = (f"El peso tuvo su peor semana desde {MES_L[since.month - 1]} de {since.year}." if (up and since)
            else f"El peso {'cayó' if up else 'subió'} {n(abs(f['chg_1w_pct']))}% en una semana.")
    peso = (f"El dólar subió a {n(f['value'], 2)} pesos: el peso perdió {n(abs(f['chg_1w_pct']))}% en una semana. "
            f"Desde 2018, solo {rk['n_larger']} semanas fueron peores.") if up else (
            f"El dólar bajó a {n(f['value'], 2)} pesos: el peso ganó {n(abs(f['chg_1w_pct']))}% en una semana.")
    lines = [
        {"id": "hook", "vo": f"{hook} Esto es MX Macro Monitor, número {num}."},
        {"id": "peso", "vo": peso},
    ]
    if db:
        strong = db["usd_broad"] >= db["usd_mxn_h10"] / 2
        lines.append({"id": "why", "vo": (
            f"¿Fue un dólar fuerte? Sí: subió {n(db['usd_broad'])}% frente a otras monedas." if strong else
            f"¿Fue un dólar fuerte? No. El real brasileño cayó más que el peso, y el dólar apenas subió "
            f"{n(db['usd_broad'])}% frente a otras monedas.")})
    lines.append({"id": "thermo", "vo": (
        f"En nuestro termómetro, {sc['tension']} de 6 señales están en rojo: " + " y ".join(red_es[k] for k in red) + ".")
        if red else "En nuestro termómetro, ninguna señal está en rojo."})
    if mx:
        lines.append({"id": "peers", "vo": (
            f"Por su tasa real, México es {ordw[pr['mx_rank']]} entre 6 economías"
            + (f": solo {' y '.join(names[c] for c in above)} la tienen más alta." if above else ": la más alta del grupo."))})
    thousands = int(abs(ic["diff"]) // 1000)
    lines.append({"id": "biz", "vo": (
        f"¿Y tu empresa? Importar cien mil dólares cuesta hoy unos {thousands} mil pesos "
        f"{'más' if ic['diff'] >= 0 else 'menos'} que hace una semana.")})
    lines.append({"id": "close", "vo": (
        f"Soy {AUTHOR}. El número {num + 1} sale el {dia} {nxt.day} de {MES_L[nxt.month - 1]}. Sígueme para recibirlo.")})
    return lines


# --- speech text --------------------------------------------------------------------------------
def to_speech(text: str) -> str:
    """Narration as the voice should read it: numbers in words (captions keep the digits)."""
    import re
    from num2words import num2words

    def w(x: int) -> str:
        return num2words(x, lang="es")

    def dec(m):
        i, d = m.group(1).replace(",", ""), m.group(2)
        frac = w(int(d)) if not d.startswith("0") or len(d) == 1 else "cero " + w(int(d))
        return f"{w(int(i))} punto {frac}"

    t = text.replace("MX Macro", "Eme Equis Macro")
    t = re.sub(r" (\d) de (enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)",
               lambda m: (" primero" if m.group(1) == "1" else " " + m.group(1)) + " de " + m.group(2), t)
    t = re.sub(r"(\d+)\.(\d+)", dec, t)
    t = re.sub(r"\d{1,3}(?:,\d{3})+", lambda m: w(int(m.group(0).replace(",", ""))), t)
    t = re.sub(r"\b\d+\b", lambda m: w(int(m.group(0))), t)
    t = t.replace("%", " por ciento").replace(" pp", " puntos porcentuales")
    t = t.replace("número uno.", "número uno.").replace("  ", " ")
    return t


# --- captions -------------------------------------------------------------------------------------
def caption_chunks(text: str, max_words: int = 7) -> List[str]:
    """Split narration into short caption chunks at punctuation, then by length."""
    import re
    parts = [p.strip() for p in re.split(r"(?<=[.,:;?])\s+", text) if p.strip()]
    out: List[str] = []
    for p in parts:
        w = p.split()
        while len(w) > max_words:
            k = math.ceil(len(w) / math.ceil(len(w) / max_words))
            out.append(" ".join(w[:k]))
            w = w[k:]
        out.append(" ".join(w))
    return out


# --- drawing helpers ------------------------------------------------------------------------------
def chrome(pg: Page, num: int, run: str, frac: float):
    draw_mark(pg.ax, M, 44, 46)
    pg.text(M + 62, 47, "MX MACRO MONITOR", 19, INK, "Archivo Exp", "extra bold")
    pg.text(M + 62, 71, "Boletín semanal de economía mexicana", 17, MUTED, SERIF_D, "medium", "italic")
    d = pd.Timestamp(run)
    pg.text(W - M, 47, f"Nº {num}", 19, INK, SANS, "extra bold", ha="right")
    pg.text(W - M, 72, f"{d.day} de {MES_L[d.month - 1]} de {d.year}", 17, MUTED, SANS, ha="right")
    pg.rect(M, 110, CW, 3.2, RULE)
    pg.rect(M, 110, CW * frac, 3.2, BLUE)


def caption(pg: Page, text: str, alpha: float = 1.0):
    if not text:
        return
    y0 = H - 210
    pg.rect(0, y0 - 24, W, 210 + 24, PAPER)
    lines = pg.wrap(text, 42, CW, SANS, "semibold")
    for k, words in enumerate(lines[:2]):
        pg.text(W / 2, y0 + k * 56, " ".join(words), 42, INK, SANS, "semibold", ha="center")
    pg.text(W / 2, H - 58, f"{AUTHOR}  ·  {EMAIL}", 19, MUTED, SANS, ha="center")


def kicker(pg: Page, y: float, s: str):
    pg.text(M, y, track(s.upper()), 24, BLUE, SANS, "extra bold")


def headline(pg: Page, y: float, text: str, size: float, p: float, color=INK) -> float:
    """Headline that rises into place."""
    lines = [text] if pg.width(text, size, DISPLAY, "extra bold") <= CW else _split(pg, text, size)
    dy = (1 - p) * 40
    for k, l in enumerate(lines):
        if p > 0:
            pg.text(M, y + dy + k * size, l, size, color, DISPLAY, "extra bold")
    return y + len(lines) * size


def _split(pg: Page, text: str, size: float) -> List[str]:
    w = text.split()
    best = min(range(1, len(w)), key=lambda k: max(pg.width(" ".join(w[:k]), size, DISPLAY, "extra bold"),
                                                    pg.width(" ".join(w[k:]), size, DISPLAY, "extra bold")))
    return [" ".join(w[:best]), " ".join(w[best:])]


# --- scenes ---------------------------------------------------------------------------------------
@dataclass
class Scene:
    id: str
    start: float
    dur: float
    draw: Callable


def scene_hook(pg: Page, t: float, d: float, s: dict, num: int):
    pg.rect(0, 0, W, H, BLUE)
    p = seg(t, 0.0, 0.7)
    draw_logo(pg.ax, M, 520 - 40 * (1 - p), 150, PAPER, PAPER, BLUE, accent=PAPER)
    q = seg(t, 0.5, 1.2)
    if q > 0:
        pg.text(W - M, 470, str(num), 300, PAPER, DISPLAY, "extra bold", ha="right")
        pg.text(W - M - pg.width(str(num), 300, DISPLAY, "extra bold") - 14, 485, "Nº", 56, PAPER, DISPLAY, "extra bold", ha="right")
    r = seg(t, 1.0, 1.6)
    if r > 0:
        d0 = pd.Timestamp(s["run_date"])
        pg.text(M, 760, track(f"{d0.day} de {MES_L[d0.month - 1]} de {d0.year}  ·  por {AUTHOR}".upper()), 22, PAPER, SANS, "semibold")
    f = s["fx"]
    h = seg(t, 1.6, 2.3)
    if h > 0:
        up = f["chg_1w_pct"] > 0
        pg.rect(M, 860, CW * h, 4, PAPER)
        pg.text(M, 900, f"EL PESO {'CAE' if up else 'SUBE'} {n(abs(f['chg_1w_pct']))}%", 110, PAPER, DISPLAY, "extra bold")


def scene_peso(pg: Page, t: float, d: float, s: dict, num: int):
    f = s["fx"]
    kicker(pg, 160, "Tipo de cambio")
    y = headline(pg, 200, f"EL PESO {'CAE' if f['chg_1w_pct'] > 0 else 'SUBE'} {n(abs(f['chg_1w_pct']))}%", 124, seg(t, 0, 0.5))
    fix = pd.read_csv(RAW_DIR / "fix.csv", parse_dates=["date"]).set_index("date")["value"]
    fix = fix[fix.index >= pd.Timestamp(f["date"]) - pd.Timedelta(days=730)]
    pg.text(M, y + 20, "Pesos por dólar (FIX de Banxico), últimos dos años", 22, MUTED, SANS)
    ax = pg.axes(M + 10, y + 70, CW - 170, H - 460 - (y + 70))
    draw_p = seg(t, 0.4, min(d * 0.55, 5.5))
    k = max(2, int(len(fix) * draw_p))
    sub = fix.iloc[:k]
    ax.fill_between(sub.index, fix.min() * 0.97, sub.values, color=BLUE, alpha=0.035, lw=0)
    ax.plot(sub.index, sub.values, color=INK, lw=2.6)
    ax.set_xlim(fix.index[0], fix.index[-1] + pd.Timedelta(days=20))
    ax.set_ylim(fix.min() * 0.97, fix.max() * 1.02)
    yt = np.arange(math.ceil(fix.min()), math.floor(fix.max() * 1.02) + 1, 1)
    ax.set_yticks(yt, [f"{v:.0f}" for v in yt])
    ax.set_xticks([pd.Timestamp(f"{y_}-01-01") for y_ in range(fix.index[0].year + 1, fix.index[-1].year + 1)],
                  [str(y_) for y_ in range(fix.index[0].year + 1, fix.index[-1].year + 1)])
    pg.fig.canvas.draw()
    from magazine import data_px
    if draw_p < 1:
        px, py = data_px(pg, ax, (sub.index[-1], sub.values[-1]))
        pg.text(px + 14, py, n(sub.values[-1], 2), 30, INK, DISPLAY, "extra bold", va="center")
    else:
        wk = fix[fix.index <= pd.Timestamp(f["date"]) - pd.Timedelta(days=7)]
        a = data_px(pg, ax, (wk.index[-1], wk.values[-1]))
        b = data_px(pg, ax, (fix.index[-1], fix.values[-1]))
        pg.ax.plot([b[0]], [b[1]], "o", ms=13, color=BLUE, mec=PAPER, mew=2.5, zorder=30)
        pg.text(b[0] + 18, b[1] - 6, n(fix.values[-1], 2), 44, BLUE, DISPLAY, "extra bold", va="center")
        pg.text(b[0] + 18, b[1] + 34, "hoy", 22, MUTED, SANS, va="center")
        pg.ax.plot([a[0]], [a[1]], "o", ms=10, color=CTX, mec=PAPER, mew=2, zorder=29)
        pg.ax.plot([a[0] - 6, a[0] - 60], [a[1] - 6, a[1] - 60], color=MUTED, lw=1.2, zorder=29)
        pg.text(a[0] - 66, a[1] - 66, f"{n(wk.values[-1], 2)} hace una semana", 24, MUTED, SANS, ha="right", va="center")
        q = seg(t, min(d * 0.55, 5.5) + 0.3, min(d * 0.55, 5.5) + 1.0)
        if q > 0:
            rk = s["value_add"]["fx_rank"]
            pg.rect(M, H - 370, CW * q, 96, INK)
            if q > 0.6:
                pg.text(M + 28, H - 322, f"Solo {rk['n_larger']} de {rk['n_weeks']} semanas desde 2018 fueron peores", 34, PAPER,
                        SERIF_D, "medium", "italic", va="center")


def scene_why(pg: Page, t: float, d: float, s: dict, num: int):
    db = s["value_add"]["dollar"]
    kicker(pg, 160, "¿Por qué cayó el peso?")
    y = headline(pg, 200, "NO FUE UN DÓLAR FUERTE", 124, seg(t, 0, 0.5))
    pg.text(M, y + 24, f"Variación del {pd.Timestamp(db['start']).day} al {pd.Timestamp(db['end']).day} de noviembre, % (Fed, H.10)",
            22, MUTED, SANS)
    items = [("Real brasileño", -db["usd_brl"], CTX), ("Peso mexicano", -db["usd_mxn_h10"], BLUE),
             ("Dólar frente a una canasta amplia", db["usd_broad"], INK)]
    lo = min(0, min(v for _, v, _ in items))
    hi = max(0, max(v for _, v, _ in items))
    room = 150
    scale = (CW - 2 * room) / (hi - lo)
    zero = M + room + (-lo) * scale
    y0 = y + 100
    step = (H - 330 - y0) / 3
    for k, (lab, val, col) in enumerate(items):
        p = seg(t, 0.6 + k * 0.9, 1.6 + k * 0.9)
        yy = y0 + k * step
        if p <= 0:
            continue
        pg.text(M, yy, lab, 32, INK, SANS, "extra bold" if col == BLUE else "regular")
        x0, x1 = sorted([zero, zero + val * scale * p])
        pg.rect(x0, yy + 48, max(x1 - x0, 3), 80, col)
        pg.rect(zero - 1, yy + 38, 2, 100, INK)
        lab_v = f"{n(val * p, 1, True)}%"
        if val < 0:
            pg.text(x0 - 14, yy + 88, lab_v, 46, INK, DISPLAY, "extra bold", ha="right", va="center")
        else:
            pg.text(x1 + 14, yy + 88, lab_v, 46, INK, DISPLAY, "extra bold", va="center")


def scene_thermo(pg: Page, t: float, d: float, s: dict, num: int):
    v = s["value_add"]
    sc = v["thermo_score"]
    kicker(pg, 160, "Termómetro MX Macro")
    y = headline(pg, 200, f"{sc['tension']} DE 6 SEÑALES EN ROJO", 124, seg(t, 0, 0.5)) + 30
    names = {"inflation": "Inflación general", "core": "Inflación subyacente", "expectations": "Expectativas de inflación",
             "real_rate": "Tasa real (ex ante)", "fx": "Peso frente al dólar (semanal)", "activity": "Actividad (mensual)"}
    order = {"tension": 0, "vigilancia": 1, "estable": 2, "na": 3}
    rows = sorted(v["thermometer"], key=lambda r: order[r["state"]])
    rh = (H - 330 - y) / 6
    for k, r in enumerate(rows):
        p = seg(t, 0.5 + k * 0.45, 1.0 + k * 0.45)
        if p <= 0:
            continue
        cy = y + k * rh + rh / 2
        word, col = STATE.get(r["state"], ("–", MUTED))
        dx = (1 - p) * 60
        pg.rect(M + dx, cy - 15, 30, 30, col)
        pg.text(M + 54 + dx, cy, names[r["key"]], 34, INK, SANS, "semibold", va="center")
        val = r["value"]
        if r["key"] == "fx" and val is not None:
            val = -val
        vs = (n(val, 1, r["key"] in ("fx", "activity")) + "%") if val is not None else "–"
        pg.text(M + 700, cy, vs, 54, INK, DISPLAY, "extra bold", ha="right", va="center")
        pg.text(W - M, cy, word, 30, col, SANS, "extra bold", ha="right", va="center")
        pg.rect(M, y + (k + 1) * rh, CW, 1, RULE)


def scene_peers(pg: Page, t: float, d: float, s: dict, num: int):
    pr = s["value_add"]["peers"]
    names = {"MX": "México", "BR": "Brasil", "CO": "Colombia", "CL": "Chile", "PE": "Perú", "US": "Estados Unidos"}
    ordn = ["", "PRIMERO", "SEGUNDO", "TERCERO", "CUARTO", "QUINTO", "SEXTO"]
    kicker(pg, 160, "México frente a sus pares")
    y = headline(pg, 200, f"MÉXICO, {ordn[pr['mx_rank']]} EN TASA REAL", 124, seg(t, 0, 0.5))
    pg.text(M, y + 24, "Tasa de política menos inflación observada (ex post), pp", 22, MUTED, SANS)
    rows = pr["rows"]
    y0 = y + 90
    avail = H - 330 - y0
    bh = min(72, avail / len(rows) * 0.6)
    gap = (avail - bh * len(rows)) / max(len(rows) - 1, 1)
    vmax = max(r["real"] for r in rows)
    vmin = min(0, min(r["real"] for r in rows))
    bx0 = M + 270
    scale = (CW - 270 - 110) / (vmax - vmin)
    zero = bx0 + (-vmin) * scale
    for k, r in enumerate(rows):
        p = seg(t, 0.4 + k * 0.25, 1.2 + k * 0.25)
        yy = y0 + k * (bh + gap)
        mx = r["c"] == "MX"
        pg.text(M, yy + bh / 2, names[r["c"]], 32, INK, SANS, "extra bold" if mx else "regular", va="center")
        x0, x1 = sorted([zero, zero + r["real"] * scale * p])
        pg.rect(x0, yy, max(x1 - x0, 3), bh, BLUE if mx else CTX)
        if p > 0.05:
            pg.text(max(x1, zero) + 14, yy + bh / 2, n(r["real"] * p), 42, INK, DISPLAY, "extra bold", va="center")
    pg.rect(zero - 1, y0 - 8, 2, avail + 8, INK)


def scene_biz(pg: Page, t: float, d: float, s: dict, num: int):
    ic = s["value_add"]["import_cost"]
    up = ic["diff"] >= 0
    kicker(pg, 160, "Para tu empresa")
    y = headline(pg, 200, "IMPORTAR CUESTA MÁS" if up else "IMPORTAR CUESTA MENOS", 124, seg(t, 0, 0.5)) + 40
    pg.text(M, y, "Por cada USD 100,000 importados pagas hoy:", 40, INK, SERIF_D, "medium", "italic")
    p = seg(t, 0.8, 2.8)
    val = abs(ic["diff"]) * p
    pg.text(M - 4, y + 90, fmt_pesos(val), 260, BLUE, DISPLAY, "extra bold")
    pg.text(M, y + 90 + 290, f"pesos {'más' if up else 'menos'} que hace una semana.", 40, INK, SERIF_D, "medium", "italic")


def scene_close(pg: Page, t: float, d: float, s: dict, num: int):
    pg.rect(0, 0, W, H, INK)
    p = seg(t, 0, 0.6)
    draw_logo(pg.ax, M, 120 - 30 * (1 - p), 120, PAPER, BLUE, WHITE, None, PAPER, accent=BLUE_LT)
    nxt = calendario.issue_date(num + 1)
    q = seg(t, 0.4, 1.0)
    if q > 0:
        pg.rect(M, 330, CW * q, 3.2, BLUE_LT)
        pg.text(M, 380, track("SIGUIENTE NÚMERO"), 24, BLUE_LT, SANS, "extra bold")
        pg.text(M, 430, f"Nº {num + 1}", 110, PAPER, DISPLAY, "extra bold")
        pg.text(M, 550, f"{calendario.weekday(nxt, 'es').upper()} {nxt.day} DE {MES_L[nxt.month - 1].upper()}", 96, PAPER, DISPLAY, "extra bold")
    r = seg(t, 1.2, 1.8)
    if r > 0:
        pg.text(M, 700, "Sígueme para recibirlo.", 48, PAPER, SERIF_D, "medium", "italic")
        pg.rect(M, 820, CW, 1, "#5E5A52")
        pg.text(M, 860, AUTHOR, 64, PAPER, DISPLAY, "extra bold")
        pg.text(M, 950, "Economista Senior", 34, "#CFC7B8", SERIF_D, "medium", "italic")
        pg.text(M, 1010, EMAIL, 34, BLUE_LT, SANS, "semibold")


DRAW = {"hook": scene_hook, "peso": scene_peso, "why": scene_why, "thermo": scene_thermo, "peers": scene_peers,
        "biz": scene_biz, "close": scene_close}


# --- timeline & rendering -------------------------------------------------------------------------
def audio_len(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def timeline(script: List[dict]) -> List[dict]:
    t = 0.3
    out = []
    for sc in script:
        dur = audio_len(OUT / f"vo_{sc['id']}.mp3")
        hold = {"hook": 0.4, "peso": 0.8, "biz": 0.8}.get(sc["id"], 0.4)
        out.append({**sc, "start": round(t, 3), "vo_dur": round(dur, 3), "dur": round(dur + hold, 3)})
        t += dur + hold + GAP
    return out


def caption_at(tl: List[dict], t: float) -> str:
    for sc in tl:
        if sc["start"] <= t < sc["start"] + sc["vo_dur"] + 0.15:
            chunks = caption_chunks(sc["vo"])
            weights = np.array([len(c) + 6 for c in chunks], float)
            edges = np.concatenate([[0], np.cumsum(weights) / weights.sum()]) * sc["vo_dur"]
            k = int(np.searchsorted(edges, t - sc["start"], side="right") - 1)
            return chunks[max(0, min(k, len(chunks) - 1))]
    return ""


def render_frame(args):
    i, tl, s, frames_dir = args
    t = i / FPS
    num = s.get("edition", 1)
    cur = tl[0]
    for sc in tl:
        if t >= sc["start"] - GAP / 2:
            cur = sc
    lt = max(0.0, t - cur["start"])
    dark = cur["id"] in ("hook", "close")
    pg = Page(BLUE if cur["id"] == "hook" else INK if cur["id"] == "close" else PAPER)
    if not dark:
        total = tl[-1]["start"] + tl[-1]["dur"]
        chrome(pg, num, s["run_date"], clamp(t / total))
    DRAW[cur["id"]](pg, lt, cur["dur"], s, num)
    if not dark:
        caption(pg, caption_at(tl, t))
    else:
        cap = caption_at(tl, t)
        if cap:
            col = PAPER
            lines = pg.wrap(cap, 42, CW, SANS, "semibold")
            for k, words in enumerate(lines[:2]):
                pg.text(W / 2, H - 230 + k * 56, " ".join(words), 42, col, SANS, "semibold", ha="center")
    pg.fig.savefig(frames_dir / f"{i:05d}.png", dpi=100, facecolor=pg.bg)
    plt.close(pg.fig)
    return i


def render(workers: int = 2) -> Path:
    s = snapshot()
    script = json.loads((OUT / "script.json").read_text(encoding="utf-8"))["scenes"]
    tl = timeline(script)
    total = tl[-1]["start"] + tl[-1]["dur"] + TAIL
    n_frames = int(total * FPS)
    frames = OUT / "frames"
    frames.mkdir(parents=True, exist_ok=True)
    for old in frames.glob("*.png"):
        old.unlink()
    with Pool(workers) as pool:
        for k, _ in enumerate(pool.imap_unordered(render_frame, [(i, tl, s, frames) for i in range(n_frames)], chunksize=8)):
            if k % 150 == 0:
                print(f"frame {k}/{n_frames}", flush=True)
    return encode(s, tl, total)


def encode(s: dict = None, tl: List[dict] = None, total: float = None) -> Path:
    s = s or snapshot()
    if tl is None:
        tl = timeline(json.loads((OUT / "script.json").read_text(encoding="utf-8"))["scenes"])
        total = tl[-1]["start"] + tl[-1]["dur"] + TAIL
    frames = OUT / "frames"
    # audio: narration clips at scene starts + music bed (ducked) + fades
    inputs, filters, labels = [], [], []
    for k, sc in enumerate(tl):
        inputs += ["-i", str(OUT / f"vo_{sc['id']}.mp3")]
        ms = int(sc["start"] * 1000)
        filters.append(f"[{k + 1}:a]adelay={ms}|{ms},apad[v{k}]")
        labels.append(f"[v{k}]")
    music = OUT / "music.mp3"
    mix = f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0,atrim=0:{total:.2f}[vo]"
    filters.append(mix)
    if music.exists():
        inputs += ["-i", str(music)]
        mi = len(tl) + 1
        filters.append(f"[{mi}:a]volume=0.16,afade=t=in:d=1.5,afade=t=out:st={total - 2.5:.2f}:d=2.5,"
                       f"apad,atrim=0:{total:.2f}[mu]")
        filters.append("[vo][mu]amix=inputs=2:normalize=0,alimiter=limit=0.95[aout]")
    else:
        filters.append("[vo]anull[aout]")
    num = s.get("edition", 1)
    out = OUT / f"mx_macro_monitor_n{num}.mp4"
    cmd = ["ffmpeg", "-y", "-v", "error", "-framerate", str(FPS), "-i", str(frames / "%05d.png"), *inputs,
           "-filter_complex", ";".join(filters), "-map", "0:v", "-map", "[aout]",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
           "-c:a", "aac", "-b:a", "192k", "-shortest", str(out)]
    subprocess.run(cmd, check=True)
    (OUT / "timeline.json").write_text(json.dumps(tl, ensure_ascii=False, indent=1), encoding="utf-8")
    write_srt(tl, OUT / f"mx_macro_monitor_n{num}.srt")
    return out


def write_srt(tl: List[dict], path: Path):
    def ts(x):
        h, r = divmod(x, 3600)
        m_, s_ = divmod(r, 60)
        return f"{int(h):02d}:{int(m_):02d}:{int(s_):02d},{int((s_ % 1) * 1000):03d}"
    out, k = [], 1
    for sc in tl:
        chunks = caption_chunks(sc["vo"])
        weights = np.array([len(c) + 6 for c in chunks], float)
        edges = np.concatenate([[0], np.cumsum(weights) / weights.sum()]) * sc["vo_dur"] + sc["start"]
        for c, a, b in zip(chunks, edges[:-1], edges[1:]):
            out.append(f"{k}\n{ts(a)} --> {ts(b)}\n{c}\n")
            k += 1
    path.write_text("\n".join(out), encoding="utf-8")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "render"
    OUT.mkdir(parents=True, exist_ok=True)
    if cmd == "script":
        sc = build_script(snapshot())
        (OUT / "script.json").write_text(json.dumps({"scenes": sc}, ensure_ascii=False, indent=1), encoding="utf-8")
        for x in sc:
            x["speech"] = to_speech(x["vo"])
        (OUT / "script.json").write_text(json.dumps({"scenes": sc}, ensure_ascii=False, indent=1), encoding="utf-8")
        for x in sc:
            print(f"[{x['id']}] {x['speech']}")
        print("palabras:", sum(len(x["vo"].split()) for x in sc))
    elif cmd == "encode":
        print(encode())
    else:
        print(render())

"""
MX Macro Monitor v5 — "revista económica de autor".

Six 1080×1350 px pages (LinkedIn 4:5 document):
  1. Portada: cabecera de marca, titular display, gráfica protagonista anotada, Dato·Lectura·Fuente
  2. Termómetro MX Macro (regla pública, 6 señales)
  3. México frente a sus pares (BIS) + ¿fue el peso o el dólar? (Fed H.10)
  4. Para tu empresa (traducción a pesos) + el cálculo de la semana
  5. En la mira (agenda) + nota firmada
  6. Contraportada: logo, siguiente número, contacto, método y fuentes

Every paragraph is justified (last line flush left). Charts carry no gridlines and
end with "Fuente: Elaboración propia con datos de …".
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyArrowPatch, Rectangle

from brand import (AXIS, BLUE, BLUE_LT, BODY, DISPLAY, GREEN, GREEN_LT, INK, MUTED, OCHRE, PAPER, RED, RULE, SANS,
                   SERIF, SERIF_D, WHITE, draw_logo, draw_mark, pt)
from config import AUTHOR

EMAIL = "isaac.tienda01@gmail.com"
W, H, M = 1080, 1350, 72
CW = W - 2 * M
CTX = "#8C8578"     # context marks (3.2:1 on paper)
PAPER_2 = "#EAE3D6"  # panel tint
ON_INK = "#CFC7B8"   # secondary text on ink (10.6:1)
STATE_COLOR = {"estable": GREEN, "vigilancia": OCHRE, "tension": RED}
TOTAL = 9
PAGE = 0  # current page, set by render()

MES = {"es": ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"],
       "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]}
MES_L = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre"]
MON_L = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
         "November", "December"]
NUM = {"es": ["NINGUNA", "UNA", "DOS", "TRES", "CUATRO", "CINCO", "SEIS"],
       "en": ["NONE", "ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX"]}
ORD = {"es": ["", "PRIMERO", "SEGUNDO", "TERCERO", "CUARTO", "QUINTO", "SEXTO"],
       "en": ["", "FIRST", "SECOND", "THIRD", "FOURTH", "FIFTH", "SIXTH"]}
EPISODES = {"2020-03": {"es": "COVID-19", "en": "COVID-19"}, "2024-06": {"es": "Elección", "en": "Election"}}


# --- formatting --------------------------------------------------------------------------------
def n(x: float, d: int = 1, sign: bool = False) -> str:
    s = f"{x:+,.{d}f}" if sign else f"{x:,.{d}f}"
    return s.replace("-", "−")


def dshort(iso: str, lang: str) -> str:
    t = pd.Timestamp(iso)
    return f"{t.day}-{MES[lang][t.month - 1]}" if lang == "es" else f"{MES[lang][t.month - 1]} {t.day}"


def mshort(iso: str, lang: str) -> str:
    t = pd.Timestamp(iso if len(iso) > 7 else iso + "-01")
    return f"{MES[lang][t.month - 1]}-{t.year}" if lang == "es" else f"{MES[lang][t.month - 1]} {t.year}"


def dlong(d: date, lang: str) -> str:
    return f"{d.day} de {MES_L[d.month - 1]} de {d.year}" if lang == "es" else f"{MON_L[d.month - 1]} {d.day}, {d.year}"


def track(s: str) -> str:
    return " ".join(s)


# --- page engine -------------------------------------------------------------------------------
class Page:
    def __init__(self, bg: str = PAPER):
        self.bg = bg
        self.fig = plt.figure(figsize=(10.8, 13.5), dpi=100)
        self.fig.patch.set_facecolor(bg)
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, W)
        self.ax.set_ylim(H, 0)
        self.ax.axis("off")
        self.r = self.fig.canvas.get_renderer()
        self._w: Dict[tuple, float] = {}

    def text(self, x, y, s, size=30, color=BODY, family=SANS, weight="regular", style="normal", ha="left",
             va="top", **kw):
        return self.ax.text(x, y, s, fontsize=pt(size), color=color, family=family, fontweight=weight,
                            fontstyle=style, ha=ha, va=va, **kw)

    def width(self, s, size, family=SANS, weight="regular", style="normal") -> float:
        key = (s, size, family, weight, style)
        if key not in self._w:
            t = self.text(0, 0, s, size, family=family, weight=weight, style=style)
            self._w[key] = t.get_window_extent(self.r).width
            t.remove()
        return self._w[key]

    def wrap(self, s, size, maxw, family=SANS, weight="regular", style="normal") -> List[List[str]]:
        lines, cur = [], []
        for word in s.split():
            trial = " ".join(cur + [word])
            if not cur or self.width(trial, size, family, weight, style) <= maxw:
                cur.append(word)
            else:
                lines.append(cur)
                cur = [word]
        return lines + ([cur] if cur else [])

    def justify(self, x, y, s, size=28, maxw=CW, lh=1.42, color=BODY, family=SERIF, weight="regular",
                style="normal", last_center=False) -> float:
        """Justified paragraph: inter-word space stretched so every line but the last meets both margins."""
        lines = self.wrap(s, size, maxw, family, weight, style)
        space = self.width("a a", size, family, weight, style) - self.width("aa", size, family, weight, style)
        for k, words in enumerate(lines):
            yy = y + k * size * lh + size * 0.80  # baseline: accented capitals must not shift a word
            last = k == len(lines) - 1
            ws = [self.width(w, size, family, weight, style) for w in words]
            gap = (maxw - sum(ws)) / (len(words) - 1) if len(words) > 1 else 0
            if last or gap > 3.2 * space:
                line = " ".join(words)
                if last and last_center:
                    self.text(x + maxw / 2, yy, line, size, color, family, weight, style, ha="center", va="baseline")
                else:
                    self.text(x, yy, line, size, color, family, weight, style, va="baseline")
                continue
            xx = x
            for w, wd in zip(words, ws):
                self.text(xx, yy, w, size, color, family, weight, style, va="baseline")
                xx += wd + gap
        return y + len(lines) * size * lh

    def even_size(self, s, sizes, maxw, family=SERIF, weight="regular", style="normal") -> float:
        """Font size whose justified lines need the smallest worst-case stretch of the word space."""
        best, score = None, 1e9
        for sz in sizes:
            lines = self.wrap(s, sz, maxw, family, weight, style)
            sp = self.width("a a", sz, family, weight, style) - self.width("aa", sz, family, weight, style)
            worst = 0.0
            for words in lines[:-1]:
                if len(words) > 1:
                    gap = (maxw - sum(self.width(w, sz, family, weight, style) for w in words)) / (len(words) - 1)
                    worst = max(worst, gap / sp)
            if len(lines[-1]) == 1 and len(lines) > 1:
                worst += 5  # avoid a single orphan word on the last line
            if worst < score:
                best, score = sz, worst
        return best

    def jheight(self, s, size, maxw, lh=1.42, family=SERIF, weight="regular", style="normal") -> float:
        return len(self.wrap(s, size, maxw, family, weight, style)) * size * lh

    def fit(self, lines: List[str], maxw: float, family=DISPLAY, weight="extra bold", cap=200) -> float:
        widest = max(self.width(l, 100, family, weight) for l in lines)
        return min(cap, 100 * maxw / widest)

    def rect(self, x, y, w, h, color, z=1):
        self.ax.add_patch(Rectangle((x, y), w, h, fc=color, ec="none", zorder=z))

    def hline(self, y, x0=M, x1=W - M, color=RULE, lw=1.0):
        self.ax.plot([x0, x1], [y, y], color=color, lw=lw, solid_capstyle="butt")

    def vline(self, x, y0, y1, color=RULE, lw=1.0):
        self.ax.plot([x, x], [y0, y1], color=color, lw=lw, solid_capstyle="butt")

    def axes(self, x, y, w, h):
        a = self.fig.add_axes([x / W, 1 - (y + h) / H, w / W, h / H])
        a.set_facecolor("none")
        for sp in a.spines.values():
            sp.set_visible(False)
        a.tick_params(length=0, labelsize=pt(21), colors=AXIS, labelfontfamily=SANS)
        a.grid(False)
        return a


# --- chrome ------------------------------------------------------------------------------------
def header(pg: Page, num: int, run: date, lang: str, page: int, dark: bool = False):
    fg, sub = (PAPER, ON_INK) if dark else (INK, MUTED)
    draw_mark(pg.ax, M, 44, 46)
    pg.text(M + 62, 47, "MX MACRO MONITOR", 19, fg, "Archivo Exp", "extra bold")
    pg.text(M + 62, 71, "Boletín semanal de economía mexicana" if lang == "es" else "Weekly bulletin on Mexico's economy",
            17, sub, SERIF_D, style="italic")
    pg.text(W - M, 47, f"Nº {num}", 19, fg, SANS, "extra bold", ha="right")
    pg.text(W - M, 72, dlong(run, lang).upper() if lang == "en" else dlong(run, lang), 17, sub, SANS, ha="right")
    pg.hline(110, color=BLUE, lw=3.2)


def footer(pg: Page, page: int, lang: str, dark: bool = False, swipe: bool = True, hook: Optional[str] = None,
           email: bool = True):
    """Author + email on the left; progress segments (one per page) on the right."""
    page = PAGE or page
    fg, sub = (PAPER, ON_INK) if dark else (INK, MUTED)
    y = H - 66
    pg.hline(y - 18, color=ON_INK if dark else RULE, lw=0.8)
    pg.text(M, y, AUTHOR, 19, fg, SANS, "semibold")
    if email:
        pg.text(M + pg.width(AUTHOR, 19, SANS, "semibold") + 14, y, f"·  {EMAIL}", 19, sub, SANS)
    sw, sg = 20, 6
    x0 = W - M - TOTAL * sw - (TOTAL - 1) * sg
    for k in range(TOTAL):
        on = k < page
        pg.rect(x0 + k * (sw + sg), y + 6, sw, 8, (BLUE_LT if dark else BLUE) if on else (MUTED if dark else RULE))
    if swipe and page < TOTAL:
        pg.text(x0 - 18, y, hook or ("Desliza  →" if lang == "es" else "Swipe  →"), 19 if not hook else 22,
                BLUE if (hook and not dark) else fg, SANS, "semibold" if not hook else "extra bold", ha="right")


def kicker(pg: Page, y: float, s: str, color=BLUE) -> float:
    pg.text(M, y, track(s.upper()), 22, color, SANS, "extra bold")
    return y + 40


def headline(pg: Page, y: float, lines: List[str], cap: float = 150, color=INK, maxw=CW) -> float:
    size = pg.fit(lines, maxw, cap=cap)
    for k, l in enumerate(lines):
        pg.text(M, y + k * size * 0.9, l, size, color, DISPLAY, "extra bold")
    return y + len(lines) * size * 0.9 + size * 0.12


def source(pg: Page, y: float, s: str, dark=False, x=M, maxw=CW) -> float:
    return pg.justify(x, y, s, 19, maxw, 1.35, ON_INK if dark else MUTED, SANS)


# --- copy --------------------------------------------------------------------------------------
def cover_copy(s: dict, v: dict, lead: str, lang: str) -> dict:
    f, i, a, p = s["fx"], s["inflation"], s.get("activity") or {}, s["policy"]
    es = lang == "es"
    if lead == "fx":
        up = f["chg_1w_pct"] > 0
        big = f["signal"] != "normal"
        lines = (["SACUDIDA", "CAMBIARIA"] if up else ["SÚPER", "PESO"]) if es else (["PESO", "SHOCK"] if up else ["SUPER", "PESO"])
        if not big:
            lines = ["PESO", "EN CALMA"] if es else ["PESO", "HOLDS"]
        rk = v["fx_rank"]
        since = mshort(f["largest_since"], lang) if f.get("largest_since") else None
        if es:
            dek = (f"El peso {'perdió' if up else 'ganó'} {n(abs(f['chg_1w_pct']))}% frente al dólar en una semana"
                   + (f": su peor caída desde {MES_L[int(f['largest_since'][5:7]) - 1]} de {f['largest_since'][:4]}" if up and since else "")
                   + f". De {rk['n_weeks']} semanas desde {mshort(rk['start'], 'es')}, solo {rk['n_larger']} fueron más bruscas.")
        else:
            dek = (f"The peso {'lost' if up else 'gained'} {n(abs(f['chg_1w_pct']))}% against the dollar in a week"
                   + (f": its worst fall since {MON_L[int(f['largest_since'][5:7]) - 1]} {f['largest_since'][:4]}" if up and since else "")
                   + f". Of {rk['n_weeks']} weeks since {mshort(rk['start'], 'en')}, only {rk['n_larger']} were sharper.")
        sig = {"es": {"atypical": "atípico", "unusual": "inusual", "normal": "normal"},
               "en": {"atypical": "atypical", "unusual": "unusual", "normal": "normal"}}[lang][f["signal"]]
        strip = {
            "dato": (f"{n(f['value'], 2)} pesos por dólar (FIX, {dshort(f['date'], lang)}); hace una semana, {n(f['value_1w_ago'], 2)}."
                     if es else f"{n(f['value'], 2)} pesos per dollar (FIX, {dshort(f['date'], lang)}); a week ago, {n(f['value_1w_ago'], 2)}."),
            "lectura": (f"Movimiento {sig}: {n(f['z_1w'])} desviaciones estándar respecto a cinco años de semanas previas."
                        if es else f"{sig.capitalize()} move: {n(f['z_1w'])} standard deviations against five years of prior weeks."),
            "fuente": "Elaboración propia con datos de Banxico (FIX)." if es else "Own elaboration with Banxico data (FIX).",
        }
        kick = "Tipo de cambio" if es else "Exchange rate"
    elif lead == "inflation":
        up = i["delta_pp"] >= 0
        lines = (["INFLACIÓN", "TERCA"] if up else ["INFLACIÓN", "CEDE"]) if es else (["STICKY", "INFLATION"] if up else ["INFLATION", "EASES"])
        dek = (f"La inflación anual {'subió' if up else 'bajó'} a {n(i['yoy'], 2)}% en {MES_L[int(i['period'][5:7]) - 1]}; la subyacente está en {n(i['core'], 2)}%."
               if es else f"Annual inflation {'rose' if up else 'fell'} to {n(i['yoy'], 2)}% in {MON_L[int(i['period'][5:7]) - 1]}; core stands at {n(i['core'], 2)}%.")
        strip = {"dato": f"{n(i['yoy'], 2)}% anual ({mshort(i['period'], lang)})", "lectura": dek,
                 "fuente": "Elaboración propia con datos de INEGI." if es else "Own elaboration with INEGI data."}
        kick = "Inflación" if es else "Inflation"
    elif lead == "activity":
        down = a.get("mom", 0) < 0
        lines = (["FRENO", "ECONÓMICO"] if down else ["LA ECONOMÍA", "REPUNTA"]) if es else (["ECONOMY", "STALLS"] if down else ["ECONOMY", "REBOUNDS"])
        dek = (f"El IGAE {'cayó' if down else 'creció'} {n(abs(a['mom']))}% mensual en {MES_L[int(a['period'][5:7]) - 1]}; a tasa anual, {n(a['yoy'], 1, True)}%."
               if es else f"IGAE {'fell' if down else 'grew'} {n(abs(a['mom']))}% m/m in {MON_L[int(a['period'][5:7]) - 1]}; {n(a['yoy'], 1, True)}% y/y.")
        strip = {"dato": f"IGAE {n(a['mom'], 1, True)}% m/m", "lectura": dek,
                 "fuente": "Elaboración propia con datos de INEGI." if es else "Own elaboration with INEGI data."}
        kick = "Actividad económica" if es else "Economic activity"
    else:
        lines = ["TASA", "NEUTRAL"] if es else ["NEUTRAL", "RATE"]
        dek = (f"La tasa objetivo está en {n(p['rate'], 2)}% y la tasa real ex ante en {n(p['real_ex_ante'], 2)}%."
               if es else f"The policy rate is {n(p['rate'], 2)}% and the ex-ante real rate {n(p['real_ex_ante'], 2)}%.")
        strip = {"dato": f"{n(p['rate'], 2)}%", "lectura": dek,
                 "fuente": "Elaboración propia con datos de Banxico." if es else "Own elaboration with Banxico data."}
        kick = "Política monetaria" if es else "Monetary policy"
    short = dek.split(":")[0].split(". ")[0].rstrip(".") + "."
    return {"kicker": kick, "lines": lines, "dek": dek, "short": short, "strip": strip}


# --- charts ------------------------------------------------------------------------------------
def data_px(pg: Page, ax, xy):
    import matplotlib.dates as mdates
    xv = mdates.date2num(xy[0]) if isinstance(xy[0], (pd.Timestamp, date)) else xy[0]
    disp = ax.transData.transform((xv, float(xy[1])))
    return pg.ax.transData.inverted().transform(disp)


def annotate(pg: Page, ax, xy, offset, label, color=INK, rad=0.3, size=27, ha="left"):
    """Hand-style annotation: italic serif label placed at `offset` px from the point, curved arrow to it."""
    px, py = data_px(pg, ax, xy)
    tx, ty = px + offset[0], py + offset[1]
    first = label.split("\n")[0]
    pg.text(tx, ty, label, size, color, SERIF_D, "medium", "italic", ha=ha, va="top", linespacing=1.0)
    lw_ = pg.width(first, size, SERIF_D, "medium", "italic")
    sx = tx - 8 if ha == "left" else tx + 8
    if ha == "left" and offset[0] < 0:
        sx = tx + lw_ + 8
    if ha == "right" and offset[0] > 0:
        sx = tx - lw_ - 8
    arr = FancyArrowPatch((sx, ty + size * 0.55), (px, py - 8), connectionstyle=f"arc3,rad={rad}",
                          arrowstyle="-|>,head_length=9,head_width=4.5", color=color, lw=1.6, zorder=20,
                          shrinkA=0, shrinkB=0)
    pg.ax.add_patch(arr)


def chart_fx_weeks(pg: Page, s: dict, v: dict, lang: str, x, y, w, h, simple: bool = False):
    wk = v["fx_rank"]["weeks"]
    dts = pd.to_datetime(wk["dates"])
    vals = np.array(wk["values"])
    es = lang == "es"
    pg.text(x, y, ("Cambio semanal del peso frente al dólar, % · arriba = peso más débil" if es
                   else "Weekly change of the peso vs the dollar, % · up = weaker peso"), 22, MUTED, SANS)
    ax = pg.axes(x + 44, y + 44, w - 44, h - 44)
    ax.bar(dts[:-1], vals[:-1], width=5.2, color=CTX, linewidth=0)
    ax.bar(dts[-1:], vals[-1:], width=16, color=BLUE, linewidth=0, zorder=5)
    ax.axhline(0, color=INK, lw=1.0)
    lo, hi = min(vals.min(), -4), max(vals.max(), 6) * 1.12
    ax.set_ylim(lo * 1.1, hi)
    ax.set_xlim(dts[0] - pd.Timedelta(days=20), dts[-1] + pd.Timedelta(days=40))
    ticks = [t for t in (-5, 0, 5, 10) if lo * 1.1 <= t <= hi]
    ax.set_yticks(ticks, [n(t, 0) if t else "0" for t in ticks])
    years = pd.date_range(f"{dts[0].year + 1}-01-01", dts[-1], freq="YS")
    ax.set_xticks(years, [str(t.year) for t in years])
    ax.tick_params(axis="x", pad=8)
    ax.tick_params(axis="y", pad=6)
    # annotations: this week + known episodes (largest move in each)
    pg.fig.canvas.draw()
    cur = vals[-1]
    annotate(pg, ax, (dts[-1], cur), (-30, -150), ("Esta semana" if es else "This week"),
             BLUE, rad=-0.35, size=32, ha="right")
    ser = pd.Series(vals, index=dts)
    for key, lab in EPISODES.items():
        sub = ser[ser.index.strftime("%Y-%m") == key]
        if sub.empty or sub.max() < cur:
            continue
        t = sub.idxmax()
        left = (t - dts[0]).days / (dts[-1] - dts[0]).days < 0.5
        annotate(pg, ax, (t, sub.max()), (70, -20) if left else (-70, -20), f"{lab[lang]}\n{mshort(key, lang)}", INK,
                 rad=0.3 if left else -0.3, size=26, ha="left" if left else "right")
    return ax


def chart_line(pg: Page, payload: dict, title: str, sub: str, x, y, w, h, band=None):
    dts = pd.to_datetime(payload["dates"])
    vals = np.array(payload["values"])
    pg.text(x, y, title, 22, INK, SANS, "semibold")
    pg.text(x, y + 32, sub, 19, MUTED, SANS)
    ax = pg.axes(x + 44, y + 74, w - 90, h - 74)
    if band:
        ax.axhspan(band[0], band[1], color=PAPER_2, lw=0)
    ax.plot(dts, vals, color=INK, lw=2.4)
    ax.plot(dts[-1:], vals[-1:], "o", ms=11, color=BLUE, mec=PAPER, mew=2)
    ax.text(dts[-1], vals[-1], f"  {n(vals[-1], 2)}", color=INK, fontsize=pt(26), family=SANS, fontweight="extra bold",
            va="center")
    return ax


# --- pages (v6: una idea por página, ≤ 25 palabras de lectura) -----------------------------------
HL = 124          # fixed inner headline size: same on every page
Y_KICK = 168
Y_HEAD = 206
Y_SRC = H - 168   # fixed source line


def inner(pg: Page, kick: str, lines: List[str], dek: Optional[str], num, run, lang, page) -> float:
    header(pg, num, run, lang, page)
    kicker(pg, Y_KICK, kick)
    y = Y_HEAD
    for k, l in enumerate(lines):
        pg.text(M, y + k * HL * 1.0, l, HL, INK, DISPLAY, "extra bold")
    y += len(lines) * HL * 1.0 + 22
    if dek:
        y = pg.justify(M, y, dek, 38, CW, 1.25, INK, SERIF_D, "medium", "italic") + 10
    return y + 36


def src_line(pg: Page, txt: str, dark=False):
    pg.text(M, Y_SRC, txt, 19, ON_INK if dark else MUTED, SANS)


def page_cover(s, v, t, lang, num, run) -> Page:
    es = lang == "es"
    pg = Page()
    lead = t["order"][0]
    cc = cover_copy(s, v, lead, lang)
    pg.rect(0, 0, W, 250, BLUE)
    draw_logo(pg.ax, M, 52, 104, PAPER, PAPER, BLUE, accent=PAPER)
    nw = pg.width(str(num), 170, DISPLAY, "extra bold")
    pg.text(W - M, 34, str(num), 170, PAPER, DISPLAY, "extra bold", ha="right", va="top")
    pg.text(W - M - nw - 10, 44, "Nº", 34, PAPER, DISPLAY, "extra bold", ha="right", va="top")
    pg.text(M, 204, (f"{dlong(run, 'es').upper()}  ·  POR {AUTHOR.upper()}" if es
                     else f"{dlong(run, 'en').upper()}  ·  BY {AUTHOR.upper()}"), 18, PAPER, SANS, "semibold")
    kicker(pg, 290, cc["kicker"])
    y = 330
    size = pg.fit(cc["lines"], CW, cap=150)
    for k, l in enumerate(cc["lines"]):
        pg.text(M, y + k * size * 0.9, l, size, INK, DISPLAY, "extra bold")
    y += len(cc["lines"]) * size * 0.9 + 34
    y = pg.justify(M, y, cc["short"], 40, CW, 1.22, INK, SERIF_D, "medium", "italic") + 34
    bottom = Y_SRC - 70
    if lead == "fx":
        chart_fx_weeks(pg, s, v, lang, M, y, CW, bottom - y, simple=True)
    elif lead == "inflation":
        chart_line(pg, s["inflation"]["chart"], "Inflación anual, %" if es else "Annual inflation, %",
                   "Franja: intervalo de Banxico (2%–4%)" if es else "Band: Banxico interval (2%–4%)", M, y, CW, bottom - y, band=(2, 4))
    elif lead == "activity":
        chart_line(pg, s["activity"]["yoy_chart"], "IGAE, variación anual, %" if es else "IGAE, annual change, %",
                   "Serie desestacionalizada" if es else "Seasonally adjusted", M, y, CW, bottom - y)
    else:
        chart_line(pg, s["policy"]["real_chart"], "Tasa real ex ante, %" if es else "Ex-ante real rate, %",
                   "Franja: rango neutral de Banxico" if es else "Band: Banxico neutral range", M, y, CW, bottom - y,
                   band=tuple(s["policy"]["neutral_range"]))
    src_line(pg, cc["strip"]["fuente"] if cc["strip"]["fuente"].startswith(("Fuente", "Source")) else
             ("Fuente: " if es else "Source: ") + cc["strip"]["fuente"])
    footer(pg, 1, lang, hook=("¿Qué tan grave es?  →" if es else "How bad is it?  →") if lead == "fx" else None)
    return pg


def page_rank(s, v, t, lang, num, run) -> Page:
    es = lang == "es"
    pg = Page()
    rk = v["fx_rank"]
    up = rk["chg"] > 0
    y = inner(pg, "El cálculo de la semana" if es else "This week's calculation",
              (["PEOR SEMANA", "EN AÑOS"] if up else ["MEJOR SEMANA", "EN AÑOS"]) if es else (["WORST WEEK", "IN YEARS"] if up else ["BEST WEEK", "IN YEARS"]),
              None, num, run, lang, 2)
    big = str(rk["rank"])
    y += max(0, (Y_SRC - 60 - y - 400 * 0.95 - 160) / 2)
    pg.text(M - 6, y - 20, big, 400, BLUE, DISPLAY, "extra bold")
    bw_ = pg.width(big, 400, DISPLAY, "extra bold")
    pg.text(M + bw_ + 28, y + 400 * 0.42, ("lugar" if es else "place"), 90, INK, DISPLAY, "extra bold", va="baseline")
    pg.text(M + bw_ + 28, y + 400 * 0.72, ("de " if es else "of ") + f"{rk['n_weeks']}", 90, INK, DISPLAY, "extra bold", va="baseline")
    y += 400 * 0.95
    worse = pd.Series(pd.to_datetime(rk["weeks"]["dates"][:-1]))[
        (pd.Series(rk["weeks"]["values"][:-1]) >= rk["chg"]) if up else (pd.Series(rk["weeks"]["values"][:-1]) <= rk["chg"])]
    yrs = worse.dt.year.value_counts().sort_index()
    if es:
        def word(c):
            return NUM["es"][c].lower() if c <= 6 else str(c)
        parts = [f"{word(c)} en {y_}" for y_, c in yrs.items()]
        st = pd.Timestamp(rk["start"])
        txt = (f"semanas desde {MES_L[st.month - 1]} de {st.year}. Peores: {', '.join(parts[:-1]) + ' y ' + parts[-1] if len(parts) > 1 else parts[0]}." if up
               else f"semanas desde {MES_L[st.month - 1]} de {st.year}.")
    else:
        st = pd.Timestamp(rk["start"])
        txt = (f"weeks since {MON_L[st.month - 1]} {st.year}. Worse: "
               f"{' and '.join(f'{c} in {y_}' for y_, c in yrs.items())}.")
    pg.justify(M, y, txt, 40, CW, 1.22, INK, SERIF_D, "medium", "italic")
    src_line(pg, "Fuente: Elaboración propia con datos de Banxico (FIX)." if es else "Source: Own elaboration with Banxico data (FIX).")
    footer(pg, 2, lang)
    return pg


def page_thermo(s, v, t, lang, num, run) -> Page:
    es = lang == "es"
    pg = Page()
    sc, rows = v["thermo_score"], v["thermometer"]
    hl = ([f"{NUM['es'][sc['tension']]} EN ROJO"] if es else [f"{NUM['en'][sc['tension']]} IN THE RED"]) if sc["tension"] else (
        ["TODO EN CALMA"] if es else ["ALL CALM"])
    dek = (f"De seis señales, {NUM['es'][sc['tension']].lower()} en tensión y {NUM['es'][sc['vigilancia']].lower()} en vigilancia." if es
           else f"Of six signals, {NUM['en'][sc['tension']].lower()} in tension and {NUM['en'][sc['vigilancia']].lower()} on watch.")
    y = inner(pg, "Termómetro MX Macro" if es else "MX Macro thermometer", hl, dek, num, run, lang, 3)
    names = {"es": {"inflation": "Inflación", "core": "Subyacente", "expectations": "Expectativas de inflación",
                    "real_rate": "Tasa real ex ante", "fx": "Tipo de cambio", "activity": "Actividad"},
             "en": {"inflation": "Inflation", "core": "Core", "expectations": "Inflation expectations",
                    "real_rate": "Ex-ante real rate", "fx": "Exchange rate", "activity": "Activity"}}[lang]
    word = {"es": {"estable": "Estable", "vigilancia": "Vigilancia", "tension": "Tensión", "na": "s. d."},
            "en": {"estable": "Stable", "vigilancia": "Watch", "tension": "Tension", "na": "n.a."}}[lang]
    order = {"tension": 0, "vigilancia": 1, "estable": 2, "na": 3}
    rh = (Y_SRC - 40 - y) / 6
    pg.hline(y, color=INK, lw=1.4)
    for r in sorted(rows, key=lambda r: order[r["state"]]):
        cy = y + rh / 2
        pg.rect(M, cy - 14, 28, 28, STATE_COLOR.get(r["state"], MUTED))
        pg.text(M + 52, cy, names[r["key"]], 36, INK, SANS, "semibold", va="center")
        val = r["value"]
        vs = (n(val, 1, r["key"] in ("fx", "activity")) + "%") if val is not None else "s. d."
        pg.text(M + 640, cy, vs, 58, INK, DISPLAY, "extra bold", ha="right", va="center")
        pg.text(W - M, cy, word[r["state"]], 32, STATE_COLOR.get(r["state"], MUTED), SANS, "extra bold", ha="right", va="center")
        y += rh
        pg.hline(y)
    src_line(pg, "Fuente: Elaboración propia con datos de INEGI y Banxico. Reglas en el texto del post." if es
             else "Source: Own elaboration with INEGI and Banxico data. Rules in the post text.")
    footer(pg, 3, lang)
    return pg


def page_peers(s, v, t, lang, num, run) -> Page:
    from valueadd import PEER_NAMES
    es = lang == "es"
    pg = Page()
    pr = v["peers"]
    if not pr:
        return None
    mx = next(r for r in pr["rows"] if r["c"] == "MX")
    nm = PEER_NAMES[lang]
    lines = [f"{ORD[lang][pr['mx_rank']]} DE {NUM['es'][pr['n']]}"] if es else [f"{ORD[lang][pr['mx_rank']]} OF {NUM['en'][pr['n']]}"]
    dek = (f"México tiene {n(mx['real'])} pp de tasa real." if es else f"Mexico has a {n(mx['real'])} pp real rate.")
    y = inner(pg, "México frente a sus pares" if es else "Mexico vs its peers", lines, dek, num, run, lang, 4)
    pg.text(M, y - 10, ("Tasa real ex post: tasa de política menos inflación anual, pp" if es
                        else "Ex-post real rate: policy rate minus annual inflation, pp"), 22, MUTED, SANS)
    y += 34
    rows = pr["rows"]
    avail = Y_SRC - 60 - y
    bh = min(84, avail / len(rows) * 0.62)
    gap = (avail - bh * len(rows)) / max(len(rows) - 1, 1)
    bx0 = M + 260
    vmax = max(r["real"] for r in rows)
    vmin = min(0, min(r["real"] for r in rows))
    scale = (CW - 260 - 110) / (vmax - vmin)
    zero = bx0 + (-vmin) * scale
    for k, r in enumerate(rows):
        yy = y + k * (bh + gap)
        mxr = r["c"] == "MX"
        pg.text(M, yy + bh / 2, nm[r["c"]], 32, INK, SANS, "extra bold" if mxr else "regular", va="center")
        x0, x1 = sorted([zero, zero + r["real"] * scale])
        pg.rect(x0, yy, max(x1 - x0, 3), bh, BLUE if mxr else CTX, z=3)
        pg.text(max(x1, zero) + 14, yy + bh / 2, n(r["real"]), 44, INK, DISPLAY, "extra bold", va="center")
    pg.vline(zero, y - 6, y + len(rows) * (bh + gap) - gap + 6, INK, 1.4)
    src_line(pg, f"Fuente: Elaboración propia con datos de BIS y Banxico; inflación de {mshort(pr['cpi_month'], 'es')}." if es
             else f"Source: Own elaboration with BIS and Banxico data; inflation as of {mshort(pr['cpi_month'], 'en')}.")
    footer(pg, 4, lang)
    return pg


def page_dollar(s, v, t, lang, num, run) -> Page:
    es = lang == "es"
    pg = Page()
    db = v["dollar"]
    if not db:
        return None
    peso_only = db["usd_broad"] < db["usd_mxn_h10"] / 2
    lines = (["NO FUE", "EL DÓLAR"] if peso_only else ["FUE", "EL DÓLAR"]) if es else (["NOT THE", "DOLLAR"] if peso_only else ["IT WAS THE", "DOLLAR"])
    if es:
        dek = ("El real y el peso cayeron; el dólar casi no se movió." if peso_only
               else "El dólar subió frente a casi todas las monedas.")
    else:
        dek = ("The real and the peso fell; the dollar barely moved." if peso_only
               else "The dollar rose against almost every currency.")
    y = inner(pg, "¿Fue el peso o el dólar?" if es else "Was it the peso or the dollar?", lines, dek, num, run, lang, 5)
    pg.text(M, y - 10, (f"Del {dshort(db['start'], 'es')} al {dshort(db['end'], 'es')}, %" if es
                        else f"From {dshort(db['start'], 'en')} to {dshort(db['end'], 'en')}, %"), 22, MUTED, SANS)
    y += 40
    items = [("Real brasileño: se depreció" if es else "Brazilian real: depreciated", db["usd_brl"], CTX, False),
             ("Peso mexicano: se depreció" if es else "Mexican peso: depreciated", db["usd_mxn_h10"], BLUE, True),
             ("Dólar frente a todas las monedas: se fortaleció" if es else "Dollar vs all currencies: strengthened", db["usd_broad"], INK, False)]
    vmax = max(abs(x) for _, x, _, _ in items)
    bw = CW - 150
    bh = 84
    step = (Y_SRC - 60 - y) / 3
    for k, (lab, val, col, bold) in enumerate(items):
        yy = y + k * step + (step - bh - 44) / 2
        pg.text(M, yy, lab, 30, INK, SANS, "extra bold" if bold else "regular")
        pg.rect(M, yy + 44, max(abs(val) / vmax * bw, 3), bh, col, z=3)
        pg.text(M + abs(val) / vmax * bw + 16, yy + 44 + bh / 2, f"{n(val, 1, True)}%", 40, INK, DISPLAY, "extra bold", va="center")
    src_line(pg, "Fuente: Elaboración propia con datos de la Reserva Federal (H.10); el FIX de Banxico usa otro corte de fechas." if es
             else "Source: Own elaboration with Federal Reserve data (H.10); Banxico's FIX uses a different date window.")
    footer(pg, 5, lang)
    return pg


def page_business(s, v, t, lang, num, run) -> Page:
    es = lang == "es"
    pg = Page()
    ic = v["import_cost"]
    up = ic["diff"] >= 0
    header(pg, num, run, lang, 6)
    kicker(pg, Y_KICK, "Para tu empresa" if es else "For your business")
    big = f"${abs(ic['diff']):,.0f}"
    size = pg.fit([big], CW, cap=290)
    block = 60 + size * 1.08 + 60
    y = Y_HEAD + (Y_SRC - 60 - Y_HEAD - block) / 2
    pg.text(M, y, ("Si importas USD 100,000, hoy pagas" if es else "If you import USD 100,000, today you pay"),
            42, INK, SERIF_D, "medium", "italic")
    pg.text(M - 4, y + 60, big, size, BLUE, DISPLAY, "extra bold")
    y = y + 60 + size * 1.08
    pg.text(M, y, ("pesos más que hace una semana." if up else "pesos menos que hace una semana.") if es
            else ("pesos more than a week ago." if up else "pesos less than a week ago."), 42, INK, SERIF_D, "medium", "italic")
    src_line(pg, "Fuente: Cálculo propio con el FIX de Banxico. La cuenta, en el texto del post." if es
             else "Source: Own calculation with Banxico's FIX. The math is in the post text.")
    footer(pg, 6, lang)
    return pg


def page_agenda(s, v, t, lang, num, run) -> Page:
    es = lang == "es"
    pg = Page()
    days: Dict[str, List[dict]] = {}
    for r in t["agenda"][:5]:
        days.setdefault(r["day"], []).append(r)
    days = dict(list(days.items())[:3])
    y = inner(pg, "Lo que viene" if es else "What's next", ["EN LA MIRA"] if es else ["ON THE RADAR"], None, num, run, lang, 7)
    rh = min(330, (Y_SRC - 60 - y) / max(len(days), 2))
    pg.hline(y, color=INK, lw=1.4)
    for day, evs in days.items():
        dd = day.split()
        pg.text(M, y + 34, dd[0].upper(), 26, BLUE, SANS, "extra bold")
        pg.text(M, y + 68, dd[1] if len(dd) > 1 else "", 64, INK, DISPLAY, "extra bold")
        for k, r in enumerate(evs[:2]):
            ey = y + 36 + k * 106
            pg.text(M + 250, ey, r["what"].split(" (")[0], 36, INK, SERIF)
            pg.text(M + 250, ey + 48, r["src"], 22, MUTED, SANS, "semibold")
        y += rh
        pg.hline(y)
    src_line(pg, "Fuente: calendarios oficiales de INEGI y Banxico." if es else "Source: INEGI and Banxico official calendars.")
    footer(pg, 7, lang)
    return pg


def page_note(s, v, t, lang, num, run) -> Page:
    es = lang == "es"
    note = t.get("note")
    if not note:
        return None
    pg = Page()
    header(pg, num, run, lang, 8)
    kicker(pg, Y_KICK, "Mi lectura" if es else "My take")
    quote = note.get("cita") or note["text"].split(":")[0].split(".")[0] + "."
    qs = pg.even_size(quote, range(50, 64, 2), CW, SERIF_D, "medium", "italic")
    qh = pg.jheight(quote, qs, CW, 1.2, SERIF_D, "medium", "italic")
    y = Y_HEAD + max(0, (Y_SRC - 60 - Y_HEAD - (170 + qh + 80)) / 2)
    pg.text(M - 10, y, "“", 260, BLUE, SERIF_D, "medium")
    y = pg.justify(M, y + 170, quote, qs, CW, 1.2, INK, SERIF_D, "medium", "italic") + 40
    pg.text(M, y, f"— {AUTHOR}", 32, INK, SANS, "semibold")
    src_line(pg, "Opinión personal del autor. La versión completa, en el texto del post." if es
             else "Author's personal view. Full version in the post text.")
    footer(pg, 8, lang)
    return pg


def page_back(s, v, t, lang, num, run) -> Page:
    es = lang == "es"
    pg = Page(INK)
    draw_logo(pg.ax, M, 120, 150, PAPER, BLUE, WHITE,
              "Boletín semanal de economía mexicana" if es else "Weekly bulletin on Mexico's economy", ON_INK, accent=BLUE_LT)
    nxt = _next_monday(run)
    y = 420
    pg.hline(y, color=BLUE_LT, lw=3.2)
    pg.text(M, y + 40, track(("Siguiente número" if es else "Next issue").upper()), 24, BLUE_LT, SANS, "extra bold")
    lines = [f"Nº {num + 1}", (f"LUNES {nxt.day} DE {MES_L[nxt.month - 1].upper()}" if es else f"MONDAY, {MON_L[nxt.month - 1].upper()} {nxt.day}")]
    size = pg.fit(lines, CW * 0.92, cap=120)
    for k, l in enumerate(lines):
        pg.text(M, y + 90 + k * size * 1.0, l, size, PAPER, DISPLAY, "extra bold")
    y = y + 90 + len(lines) * size * 1.0 + 40
    pg.text(M, y, "Sígueme para recibirlo." if es else "Follow me to get it.", 44, PAPER, SERIF_D, "medium", "italic")
    pg.text(M, Y_SRC - 80, track(("Contacto" if es else "Contact").upper()), 22, BLUE_LT, SANS, "extra bold")
    pg.text(M, Y_SRC - 44, EMAIL, 40, PAPER, SANS, "semibold")
    footer(pg, TOTAL, lang, dark=True, swipe=False, email=False)
    return pg


def render(s: dict, v: dict, t: dict, lang: str, out_dir: Path, num: int = 1) -> dict:
    global TOTAL, PAGE
    tl = t[lang]
    run = date.fromisoformat(s["run_date"])
    builders = [page_cover, page_rank, page_thermo, page_peers, page_dollar, page_business, page_agenda, page_note, page_back]
    if s["fx"]["chg_1w_pct"] is None or abs(v["fx_rank"]["chg"]) < 1:
        builders.remove(page_rank)  # the week's move is not news: skip the rank page
    if not v.get("peers"):
        builders.remove(page_peers)
    if not v.get("dollar"):
        builders.remove(page_dollar)
    if not tl.get("note"):
        builders.remove(page_note)
    TOTAL = len(builders)
    pages = []
    for k, b in enumerate(builders, 1):
        PAGE = k
        pages.append(b(s, v, tl, lang, num, run))
    PAGE = 0
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = out_dir / f"carousel_{lang}.pdf"
    png_dir = out_dir / f"slides_{lang}"
    png_dir.mkdir(exist_ok=True)
    for old in png_dir.glob("*.png"):
        old.unlink()
    meta = {"Title": f"MX Macro Monitor Nº {num}", "Author": f"{AUTHOR} <{EMAIL}>",
            "Subject": "Boletín semanal de economía mexicana" if lang == "es" else "Weekly bulletin on Mexico's economy"}
    with PdfPages(pdf_path, metadata=meta) as pdf:
        for k, pg in enumerate(pages, 1):
            pdf.savefig(pg.fig, facecolor=pg.bg)
            pg.fig.savefig(png_dir / f"{k:02d}.png", dpi=100, facecolor=pg.bg)
            plt.close(pg.fig)
    return {"pdf": pdf_path, "png_dir": png_dir, "n": len(pages)}


# --- post copy -----------------------------------------------------------------------------------
def edition_number(run: date, first_monday: date = date(2026, 11, 23)) -> int:
    """Nº 1 = ISO week of 23-nov-2026; one number per week."""
    return max(1, (run - first_monday).days // 7 + 1)


def _next_monday(run: date) -> date:
    return run + timedelta(days=(7 - run.weekday()) % 7 or 7)


def post_es(s: dict, v: dict, t: dict, num: int) -> str:
    """Post text. The pages carry one idea each; method, math and sources live here."""
    tl = t["es"]
    lead = tl["order"][0]
    cc = cover_copy(s, v, lead, "es")
    run = date.fromisoformat(s["run_date"])
    f, p, sc, pr, db, ic, rk = s["fx"], s["policy"], v["thermo_score"], v["peers"], v["dollar"], v["import_cost"], v["fx_rank"]
    names = {"inflation": "inflación", "core": "subyacente", "expectations": "expectativas", "real_rate": "tasa real",
             "fx": "tipo de cambio", "activity": "actividad"}
    red = [names[r["key"]] for r in v["thermometer"] if r["state"] == "tension"]
    lines = [f"→ Termómetro MX Macro: {sc['tension']} señales en rojo" + (f" ({' y '.join(red)})" if red else "")
             + f", {sc['vigilancia']} en vigilancia y {sc['estable']} estable" + ("s" if sc["estable"] != 1 else "") + "."]
    if pr:
        mx = next(r for r in pr["rows"] if r["c"] == "MX")
        lines.append(f"→ México, lugar {pr['mx_rank']} de {pr['n']} en tasa real ({n(mx['real'])}%).")
    if db:
        lines.append(f"→ Del {dshort(db['start'], 'es')} al {dshort(db['end'], 'es')}: real {n(db['usd_brl'], 1, True)}%, "
                     f"peso {n(db['usd_mxn_h10'], 1, True)}%, dólar amplio {n(db['usd_broad'], 1, True)}%.")
    lines.append(f"→ Importar USD 100,000 cuesta ${abs(ic['diff']):,.0f} pesos {'más' if ic['diff'] >= 0 else 'menos'} que hace una semana.")
    mine = f"Mi lectura: {tl['note']['text'][0].lower() + tl['note']['text'][1:]}\n\n" if tl.get("note") else ""
    how = ["Cómo lo calculo:",
           f"• Importación: USD 100,000 × FIX de hoy ({n(f['value'], 2)}) menos USD 100,000 × FIX de hace 7 días ({n(f['value_1w_ago'], 2)}).",
           f"• Ranking: {rk['n_weeks']} cambios semanales del FIX desde {mshort(rk['start'], 'es')} (cierre del viernes).",
           "• Termómetro: inflación, subyacente y expectativas son estables a ±0.5 pp de la meta de 3% y entran en tensión fuera de 2%–4%; "
           "la tasa real, frente al rango neutral de Banxico (1.8%–3.6%); tipo de cambio y actividad, por desviaciones estándar frente a su historia (tensión desde 2).",
           "• Tasa real de pares: tasa de política menos inflación anual" + (f" de {mshort(pr['cpi_month'], 'es')}" if pr else "") + "."]
    src = "Fuentes: Banxico, INEGI, BIS y Reserva Federal (H.10)."
    nm = _next_monday(run)
    return (f"MX Macro Monitor Nº {num} · {' '.join(cc['lines']).capitalize()}.\n\n{cc['short']} "
            + (f"Solo {rk['n_larger']} de {rk['n_weeks']} semanas desde {rk['start'][:4]} fueron peores." if lead == "fx" and rk["chg"] > 0 else "")
            + "\n\n" + "\n".join(lines) + "\n\n" + mine + "\n".join(how) + f"\n{src}\n\n"
            f"Cada lunes, un número nuevo. Sígueme para recibir el Nº {num + 1} el lunes {nm.day} de {MES_L[nm.month - 1]}.\n"
            f"Contacto: {EMAIL}\n\n#EconomíaMexicana #Banxico #TipoDeCambio")


def comment_en(s: dict, v: dict, t: dict, num: int) -> str:
    lead = t["en"]["order"][0]
    cc = cover_copy(s, v, lead, "en")
    sc, ic = v["thermo_score"], v["import_cost"]
    note = t["en"].get("note")
    mine = f"\n\nMy take: {note['text']}" if note else ""
    return (f"English version · MX Macro Monitor No. {num}: {' '.join(cc['lines']).capitalize()}. {cc['dek']} "
            f"MX Macro thermometer: {sc['tension']} signals in the red, {sc['vigilancia']} on watch, {sc['estable']} stable. "
            f"A USD 100,000 import costs MXN {abs(ic['diff']):,.0f} {'more' if ic['diff'] >= 0 else 'less'} than a week ago."
            f"{mine}\n\nOfficial data from Banxico, INEGI, BIS and the Federal Reserve.")


def alt_text(s: dict, v: dict, t: dict, num: int) -> str:
    cc = cover_copy(s, v, t["es"]["order"][0], "es")
    sc, ic = v["thermo_score"], v["import_cost"]
    return (f"Documento de {TOTAL} páginas, MX Macro Monitor Nº {num}, una idea por página. Portada: {' '.join(cc['lines']).lower()}; "
            f"{cc['short']} Después: el lugar de la semana en la historia; termómetro con {sc['tension']} señales en tensión; "
            "tasa real de México frente a cinco pares; comparación del peso, el real y el dólar; "
            f"{abs(ic['diff']):,.0f} pesos {'más' if ic['diff'] >= 0 else 'menos'} por cada 100 mil dólares importados; agenda; "
            "nota del autor; contraportada con contacto.")

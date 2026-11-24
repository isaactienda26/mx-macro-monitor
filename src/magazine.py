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
from config import AUTHOR, REPO_URL

EMAIL = "isaac.tienda01@gmail.com"
W, H, M = 1080, 1350, 72
CW = W - 2 * M
CTX = "#8C8578"     # context marks (3.2:1 on paper)
PAPER_2 = "#EAE3D6"  # panel tint
ON_INK = "#CFC7B8"   # secondary text on ink (10.6:1)
STATE_COLOR = {"estable": GREEN, "vigilancia": OCHRE, "tension": RED}
TOTAL = 6

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
EPISODES = {"2020-03": {"es": "COVID-19", "en": "COVID-19"}, "2024-06": {"es": "Elección 2024", "en": "2024 election"}}


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


def footer(pg: Page, page: int, lang: str, dark: bool = False, swipe: bool = True):
    fg, sub = (PAPER, ON_INK) if dark else (INK, MUTED)
    y = H - 66
    pg.hline(y - 18, color=ON_INK if dark else RULE, lw=0.8)
    pg.text(M, y, AUTHOR, 19, fg, SANS, "semibold")
    pg.text(M + pg.width(AUTHOR, 19, SANS, "semibold") + 14, y, f"·  {EMAIL}", 19, sub, SANS)
    right = f"{page} / {TOTAL}"
    if swipe and page < TOTAL:
        right = ("Desliza  →   " if lang == "es" else "Swipe  →   ") + right
    pg.text(W - M, y, right, 19, fg, SANS, "semibold", ha="right")


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
    return {"kicker": kick, "lines": lines, "dek": dek, "strip": strip}


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


def chart_fx_weeks(pg: Page, s: dict, v: dict, lang: str, x, y, w, h):
    wk = v["fx_rank"]["weeks"]
    dts = pd.to_datetime(wk["dates"])
    vals = np.array(wk["values"])
    es = lang == "es"
    pg.text(x, y, ("Variación semanal del peso frente al dólar, % (FIX)" if es else "Weekly change of the peso vs the dollar, % (FIX)"),
            22, INK, SANS, "semibold")
    pg.text(x, y + 32, ("Barras hacia arriba = depreciación del peso · dic-2018 a nov-2026" if es
                        else "Bars up = peso depreciation · Dec 2018 to Nov 2026"), 19, MUTED, SANS)
    ax = pg.axes(x + 44, y + 74, w - 44, h - 74)
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
    annotate(pg, ax, (dts[-1], cur), (-150, -110), (f"Esta semana\n{n(cur, 1, True)}%" if es else f"This week\n{n(cur, 1, True)}%"),
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


# --- pages -------------------------------------------------------------------------------------
def page_cover(s, v, t, lang, num, run) -> Page:
    es = lang == "es"
    pg = Page()
    lead = t["order"][0]
    cc = cover_copy(s, v, lead, lang)
    # masthead band
    pg.rect(0, 0, W, 250, BLUE)
    draw_logo(pg.ax, M, 52, 104, PAPER, PAPER, BLUE, accent=PAPER)
    nw = pg.width(str(num), 170, DISPLAY, "extra bold")
    pg.text(W - M, 34, str(num), 170, PAPER, DISPLAY, "extra bold", ha="right", va="top")
    pg.text(W - M - nw - 10, 44, "Nº", 34, PAPER, DISPLAY, "extra bold", ha="right", va="top")
    meta = (f"{dlong(run, 'es').upper()}  ·  BOLETÍN SEMANAL DE ECONOMÍA MEXICANA  ·  POR {AUTHOR.upper()}" if es
            else f"{dlong(run, 'en').upper()}  ·  WEEKLY BULLETIN ON MEXICO'S ECONOMY  ·  BY {AUTHOR.upper()}")
    pg.text(M, 204, meta, 17, PAPER, SANS, "semibold")
    y = kicker(pg, 284, cc["kicker"])
    y = headline(pg, y, cc["lines"], cap=138)
    y = pg.justify(M, y + 4, cc["dek"], 33, CW, 1.26, INK, SERIF_D, "medium", "italic") + 30
    strip_y = H - 262
    if lead == "fx":
        chart_fx_weeks(pg, s, v, lang, M, y, CW, strip_y - y - 52)
    elif lead == "inflation":
        chart_line(pg, s["inflation"]["chart"], "Inflación anual, %" if es else "Annual inflation, %",
                   "Franja: intervalo de variabilidad de Banxico (2%–4%)" if es else "Band: Banxico's variability interval (2%–4%)",
                   M, y, CW, strip_y - y - 34, band=(2, 4))
    elif lead == "activity":
        chart_line(pg, s["activity"]["yoy_chart"], "IGAE, variación anual, %" if es else "IGAE, annual change, %",
                   "Serie desestacionalizada" if es else "Seasonally adjusted", M, y, CW, strip_y - y - 34)
    else:
        chart_line(pg, s["policy"]["real_chart"], "Tasa real ex ante, %" if es else "Ex-ante real rate, %",
                   "Franja: rango neutral estimado por Banxico (1.8%–3.6%)" if es else "Band: Banxico's neutral range (1.8%–3.6%)",
                   M, y, CW, strip_y - y - 34, band=tuple(s["policy"]["neutral_range"]))
    # Dato · Lectura · Fuente
    pg.hline(strip_y, color=INK, lw=1.4)
    labels = ["Dato", "Lectura", "Fuente"] if es else ["Data", "Reading", "Source"]
    keys = ["dato", "lectura", "fuente"]
    colw = [300, 360, CW - 300 - 360 - 2 * 36]
    xx = M
    for k, (lab, key, cw) in enumerate(zip(labels, keys, colw)):
        if k:
            pg.vline(xx - 18, strip_y + 18, strip_y + 160)
        pg.text(xx, strip_y + 18, track(lab.upper()), 18, BLUE, SANS, "extra bold")
        pg.justify(xx, strip_y + 52, cc["strip"][key], 21, cw, 1.32, BODY, SANS)
        xx += cw + 36
    footer(pg, 1, lang)
    return pg


def page_thermo(s, v, t, lang, num, run) -> Page:
    es = lang == "es"
    pg = Page()
    header(pg, num, run, lang, 2)
    sc = v["thermo_score"]
    rows = v["thermometer"]
    y = kicker(pg, 148, "Termómetro MX Macro" if es else "MX Macro thermometer")
    hl = ([f"{NUM['es'][sc['tension']]} EN ROJO"] if es else [f"{NUM['en'][sc['tension']]} IN THE RED"]) if sc["tension"] else (
        ["TODO EN CALMA"] if es else ["ALL CALM"])
    y = headline(pg, y, hl, cap=128)
    names = {"es": {"inflation": "Inflación general", "core": "Inflación subyacente", "expectations": "Expectativas a 12 meses",
                    "real_rate": "Tasa real ex ante", "fx": "Tipo de cambio, semana", "activity": "Actividad (IGAE), mes"},
             "en": {"inflation": "Headline inflation", "core": "Core inflation", "expectations": "12-month expectations",
                    "real_rate": "Ex-ante real rate", "fx": "Exchange rate, week", "activity": "Activity (IGAE), month"}}[lang]
    tens = [names[r["key"]].split(",")[0].lower() for r in rows if r["state"] == "tension"]
    if es:
        dek = (f"Seis señales, una regla pública. Esta semana {sc['tension']} están en tensión"
               + (f" ({' y '.join(tens)})" if tens else "") + f", {sc['vigilancia']} en vigilancia y {sc['estable']} estable"
               + ("s" if sc["estable"] != 1 else "") + f". Índice MX Macro: {sc['index']} de 100, donde 0 es todo estable y 100 todo en tensión.")
    else:
        dek = (f"Six signals, one public rule. This week {sc['tension']} are in tension"
               + (f" ({' and '.join(tens)})" if tens else "") + f", {sc['vigilancia']} on watch and {sc['estable']} stable."
               + f" MX Macro index: {sc['index']} out of 100, where 0 means all stable and 100 all in tension.")
    y = pg.justify(M, y + 4, dek, 27, CW, 1.34, INK, SERIF_D, "medium", "italic") + 18
    # index scale
    pg.text(M, y, str(sc["index"]), 96, INK, DISPLAY, "extra bold")
    iw = pg.width(str(sc["index"]), 96, DISPLAY, "extra bold")
    pg.text(M + iw + 8, y + 50, "/100", 30, MUTED, SANS, "semibold")
    sx, sw, sy = M + 260, CW - 260, y + 44
    for k, (lab, col) in enumerate(zip(["estable", "vigilancia", "tension"], [GREEN, OCHRE, RED])):
        pg.rect(sx + k * sw / 3 + 2, sy, sw / 3 - 4, 12, col)
        word = {"es": ["Estable", "Vigilancia", "Tensión"], "en": ["Stable", "Watch", "Tension"]}[lang][k]
        pg.text(sx + k * sw / 3 + 2, sy + 24, word, 19, col, SANS, "semibold")
    mx = sx + sw * sc["index"] / 100
    pg.ax.plot([mx], [sy - 10], marker="v", ms=16, color=INK)
    y += 112
    pg.hline(y, color=INK, lw=1.4)
    state_w = {"es": {"estable": "Estable", "vigilancia": "Vigilancia", "tension": "Tensión", "na": "s. d."},
               "en": {"estable": "Stable", "vigilancia": "Watch", "tension": "Tension", "na": "n.a."}}[lang]
    rule_txt = {"es": {"band": "Meta 3% ± 0.5 pp · intervalo 2%–4%", "neutral": "Rango neutral Banxico 1.8%–3.6%",
                       "z": "Cambio vs. su historia: {z} desv. estándar"},
                "en": {"band": "Target 3% ± 0.5 pp · interval 2%–4%", "neutral": "Banxico neutral range 1.8%–3.6%",
                       "z": "Change vs. its history: {z} std. dev."}}[lang]
    rh = 80
    for r in rows:
        y0 = y + 12
        pg.text(M, y0, names[r["key"]], 27, INK, SANS, "semibold")
        rt = rule_txt[r["rule"]].format(z=n(r.get("z") or 0, 1, True))
        pg.text(M, y0 + 35, rt, 18, MUTED, SANS)
        val = r["value"]
        vs = (n(val, 2, r["key"] in ("fx", "activity")) + "%") if val is not None else "s. d."
        pg.text(M + 600, y0 - 6, vs, 52, INK, DISPLAY, "extra bold", ha="right")
        # three-step state marker
        bx = M + 650
        for k, st in enumerate(["estable", "vigilancia", "tension"]):
            on = r["state"] == st
            pg.rect(bx + k * 34, y0 + 12, 26, 26, STATE_COLOR[st] if on else PAPER_2)
        pg.text(bx + 3 * 34 + 12, y0 + 14, state_w[r["state"]], 26, STATE_COLOR.get(r["state"], MUTED), SANS, "extra bold")
        y += rh
        pg.hline(y)
    y += 18
    rules = ("Reglas: inflación, subyacente y expectativas son estables a ±0.5 pp de la meta de 3%, en vigilancia dentro "
             "del intervalo de 2% a 4% y en tensión fuera de él. La tasa real es estable dentro del rango neutral de Banxico "
             "y entra en tensión a más de 0.5 pp de sus bordes. Tipo de cambio y actividad usan el z-score del último cambio "
             "contra su historia previa: vigilancia desde 1.5 desviaciones estándar y tensión desde 2.") if es else (
             "Rules: headline, core and expectations are stable within ±0.5 pp of the 3% target, on watch inside the 2%–4% "
             "interval and in tension outside it. The real rate is stable inside Banxico's neutral range and in tension more "
             "than 0.5 pp beyond its edges. Exchange rate and activity use the z-score of the latest change against its prior "
             "history: watch from 1.5 standard deviations, tension from 2.")
    y = pg.justify(M, y, rules, 19, CW, 1.36, BODY, SANS) + 10
    source(pg, y, "Fuente: Elaboración propia con datos de INEGI y Banxico (SIE); rango neutral: Banxico (2024), Recuadro 7." if es
           else "Source: Own elaboration with INEGI and Banxico (SIE) data; neutral range: Banxico (2024), Box 7.")
    footer(pg, 2, lang)
    return pg


def page_peers(s, v, t, lang, num, run) -> Page:
    from valueadd import PEER_NAMES
    es = lang == "es"
    pg = Page()
    header(pg, num, run, lang, 3)
    pr, db = v["peers"], v["dollar"]
    y = kicker(pg, 148, "México frente a sus pares" if es else "Mexico vs its peers")
    if pr:
        mx = next(r for r in pr["rows"] if r["c"] == "MX")
        y = headline(pg, y, [f"{ORD[lang][pr['mx_rank']]} DE {NUM['es'][pr['n']]}" if es else f"{ORD[lang][pr['mx_rank']]} OF {NUM['en'][pr['n']]}"], cap=128)
        above = [r for r in pr["rows"][: pr["mx_rank"] - 1]]
        below = [r for r in pr["rows"][pr["mx_rank"]:]]
        nm = PEER_NAMES[lang]
        ab = [f"{nm[r['c']]} ({n(r['real'])}%)" for r in above]
        if es:
            dek = (f"Con una tasa real ex post de {n(mx['real'])}%, México ocupa el lugar {pr['mx_rank']} de {pr['n']}: "
                   + (f"debajo de {' y '.join(ab)}" if above else "")
                   + (f", pero arriba de {', '.join(nm[r['c']] for r in below[:-1])} y {nm[below[-1]['c']]}" if len(below) > 1 else "")
                   + ". Más tasa real es más colchón frente a choques, pero también crédito más caro.")
        else:
            dek = (f"With an ex-post real rate of {n(mx['real'])}%, Mexico ranks {pr['mx_rank']} of {pr['n']}: "
                   + (f"below {' and '.join(ab)}" if above else "")
                   + (f", but above {', '.join(nm[r['c']] for r in below[:-1])} and {nm[below[-1]['c']]}" if len(below) > 1 else "")
                   + ". A higher real rate is a bigger cushion against shocks, but also costlier credit.")
        y = pg.justify(M, y + 4, dek, 27, CW, 1.34, INK, SERIF_D, "medium", "italic") + 20
        pg.text(M, y, "Tasa real ex post, %" if es else "Ex-post real rate, %", 22, INK, SANS, "semibold")
        pg.text(M, y + 32, (f"Tasa de política vigente menos inflación anual de {mshort(pr['cpi_month'], 'es')}" if es
                            else f"Current policy rate minus annual inflation, {mshort(pr['cpi_month'], 'en')}"), 19, MUTED, SANS)
        y += 78
        rows = pr["rows"]
        bh, gap = 34, 12
        lx, bx0 = M, M + 230
        vmax = max(r["real"] for r in rows)
        vmin = min(0, min(r["real"] for r in rows))
        scale = (CW - 230 - 210) / (vmax - vmin)
        zero = bx0 + (-vmin) * scale
        for k, r in enumerate(rows):
            yy = y + k * (bh + gap)
            mxr = r["c"] == "MX"
            pg.text(lx, yy + bh / 2, nm[r["c"]], 25, INK, SANS, "extra bold" if mxr else "regular", va="center")
            x0, x1 = sorted([zero, zero + r["real"] * scale])
            pg.rect(x0, yy, max(x1 - x0, 2), bh, BLUE if mxr else CTX, z=3)
            lab = f"{n(r['real'])}"
            pg.text((x1 if r["real"] >= 0 else zero) + 12, yy + bh / 2, lab, 25, INK, SANS, "extra bold" if mxr else "semibold",
                    va="center")
            pg.text(W - M, yy + bh / 2, f"{n(r['rate'], 2)} − {n(r['cpi'], 2)}", 19, MUTED, SANS, ha="right", va="center")
        pg.vline(zero, y - 8, y + len(rows) * (bh + gap) - gap + 8, INK, 1.2)
        pg.text(W - M, y - 30, "tasa − inflación" if es else "rate − inflation", 17, MUTED, SANS, ha="right")
        y += len(rows) * (bh + gap) + 8
    if db:
        y += 10
        pg.rect(M, y, CW, 300, PAPER_2)
        ix = M + 32
        iy = y + 28
        pg.text(ix, iy, track(("¿Fue el peso o el dólar?" if es else "Was it the peso or the dollar?").upper()), 22, BLUE, SANS, "extra bold")
        items = [("Real brasileño" if es else "Brazilian real", db["usd_brl"], CTX),
                 ("Peso mexicano" if es else "Mexican peso", db["usd_mxn_h10"], BLUE),
                 ("Dólar vs canasta amplia" if es else "Dollar vs broad basket", db["usd_broad"], INK)]
        vmax = max(abs(x) for _, x, _ in items)
        bx0, bw = ix + 300, CW - 64 - 300 - 100
        for k, (lab, val, col) in enumerate(items):
            yy = iy + 42 + k * 44
            pg.text(ix, yy + 17, lab, 23, INK, SANS, "semibold" if col == BLUE else "regular", va="center")
            pg.rect(bx0, yy, max(abs(val) / vmax * bw, 2), 30, col, z=3)
            pg.text(bx0 + abs(val) / vmax * bw + 10, yy + 17, f"{n(val, 1, True)}%", 23, INK, SANS, "extra bold", va="center")
        txt = (f"Del {dshort(db['start'], 'es')} al {dshort(db['end'], 'es')}, el real cayó {n(db['usd_brl'])}% y el peso "
               f"{n(db['usd_mxn_h10'])}%, mientras el dólar se fortaleció solo {n(db['usd_broad'])}% frente a una canasta amplia. "
               "No fue un dólar fuerte en general: el ajuste se concentró en monedas latinoamericanas como el peso y el real.") if es else (
               f"From {dshort(db['start'], 'en')} to {dshort(db['end'], 'en')}, the real fell {n(db['usd_brl'])}% and the peso "
               f"{n(db['usd_mxn_h10'])}%, while the dollar gained only {n(db['usd_broad'])}% against a broad basket. "
               "This was not broad dollar strength: the adjustment was concentrated in Latin American currencies such as the peso and the real.")
        pg.justify(ix, iy + 180, txt, 20, CW - 64, 1.32, BODY, SERIF)
        y += 300 + 14
    source(pg, y, ("Fuente: Elaboración propia con datos de BIS (tasas de política e inflación), Banxico (tasa de México) y "
                   "Reserva Federal, H.10 (tipos de cambio e índice amplio del dólar).") if es else
           ("Source: Own elaboration with BIS (policy rates and inflation), Banxico (Mexico's rate) and Federal Reserve "
            "H.10 (exchange rates and broad dollar index) data."))
    footer(pg, 3, lang)
    return pg


def page_business(s, v, t, lang, num, run) -> Page:
    es = lang == "es"
    pg = Page()
    header(pg, num, run, lang, 4)
    f, p, i = s["fx"], s["policy"], s["inflation"]
    ic, rk = v["import_cost"], v["fx_rank"]
    y = kicker(pg, 148, "Para tu empresa" if es else "For your business")
    big = f"{'+' if ic['diff'] >= 0 else '−'}${abs(ic['diff']):,.0f}"
    size = pg.fit([big], CW, cap=200)
    pg.text(M, y - 6, big, size, BLUE, DISPLAY, "extra bold")
    y += size * 1.06 + 8
    dek = (f"pesos {'más' if ic['diff'] >= 0 else 'menos'} cuesta hoy una importación de USD 100,000 que hace una semana."
           if es else f"pesos {'more' if ic['diff'] >= 0 else 'less'} for a USD 100,000 import than a week ago.")
    y = pg.justify(M, y, dek, 38, CW, 1.22, INK, SERIF_D, "medium", "italic") + 10
    calc = (f"USD 100,000 × {n(f['value'], 4)} = ${ic['mxn_now']:,.0f} el {dshort(f['date'], 'es')}, frente a "
            f"${ic['mxn_1w']:,.0f} con el FIX de {n(f['value_1w_ago'], 4)} una semana antes.") if es else (
            f"USD 100,000 × {n(f['value'], 4)} = MXN {ic['mxn_now']:,.0f} on {dshort(f['date'], 'en')}, versus "
            f"MXN {ic['mxn_1w']:,.0f} at the FIX of {n(f['value_1w_ago'], 4)} a week earlier.")
    y = pg.justify(M, y, calc, 21, CW, 1.36, MUTED, SANS) + 26
    pg.hline(y, color=INK, lw=1.4)
    y += 24
    up = f["chg_1w_pct"] >= 0
    blocks = ([
        ("Si importas", f"Cada dólar cuesta {n(abs(f['chg_1w_pct']))}% {'más' if up else 'menos'} que hace una semana. "
                        "Conviene revisar qué parte de tus compras en dólares está cubierta y por cuánto tiempo."),
        ("Si exportas", f"Tus ventas en dólares valen {'más' if up else 'menos'} en pesos. El margen solo mejora de forma "
                        "duradera si el tipo de cambio se sostiene y tus insumos no están dolarizados."),
        ("Si te financias", f"La tasa objetivo está en {n(p['rate'], 2)}%, {abs(p['chg_12m_bp']):.0f} pb "
                            f"{'menos' if p['chg_12m_bp'] < 0 else 'más'} que hace un año, y la tasa real ex ante "
                            f"({n(p['real_ex_ante'], 1)}%) está dentro del rango neutral: el crédito ya no es restrictivo."),
        ("Si fijas precios", f"Inflación de {n(i['yoy'], 2)}% y subyacente de {n(i['core'], 2)}%, dentro del intervalo de 2% a 4%. "
                             "Para México, la evidencia apunta a un traspaso del tipo de cambio a precios bajo y gradual."),
    ] if es else [
        ("If you import", f"Each dollar costs {n(abs(f['chg_1w_pct']))}% {'more' if up else 'less'} than a week ago. "
                          "Check how much of your dollar purchases is hedged, and for how long."),
        ("If you export", f"Your dollar sales are worth {'more' if up else 'less'} in pesos. Margins only improve durably "
                          "if the exchange rate holds and your inputs are not priced in dollars."),
        ("If you borrow", f"The policy rate is {n(p['rate'], 2)}%, {abs(p['chg_12m_bp']):.0f} bp "
                          f"{'lower' if p['chg_12m_bp'] < 0 else 'higher'} than a year ago, and the ex-ante real rate "
                          f"({n(p['real_ex_ante'], 1)}%) is inside the neutral range: credit is no longer restrictive."),
        ("If you set prices", f"Inflation at {n(i['yoy'], 2)}% and core at {n(i['core'], 2)}%, inside the 2%–4% interval. "
                              "For Mexico, evidence points to low and gradual exchange-rate pass-through to prices."),
    ])
    colw = (CW - 48) / 2
    heights = []
    for k, (h_, b_) in enumerate(blocks):
        cx = M + (k % 2) * (colw + 48)
        cy = y + (k // 2) * (max(heights) + 30 if k >= 2 and heights else 0)
        pg.text(cx, cy, h_, 30, INK, DISPLAY, "extra bold")
        end = pg.justify(cx, cy + 44, b_, 24, colw, 1.36, BODY, SERIF)
        if k < 2:
            heights.append(end - cy)
    y = y + max(heights) * 2 + 30 + 10
    # the calculation of the week
    bh = H - 110 - y
    pg.rect(M, y, CW, bh, INK)
    pg.text(M + 32, y + 28, track(("El cálculo de la semana" if es else "This week's calculation").upper()), 20, GREEN_LT, SANS, "extra bold")
    rkt = f"{rk['rank']}º" if es else f"#{rk['rank']}"
    pg.text(M + 32, y + 60, rkt, 130, BLUE_LT, DISPLAY, "extra bold")
    years = pd.Series(pd.to_datetime(rk["weeks"]["dates"][:-1]))
    vals = pd.Series(rk["weeks"]["values"][:-1])
    worse = years[(vals >= rk["chg"]) if rk["chg"] > 0 else (vals <= rk["chg"])]
    yrs = worse.dt.year.value_counts().sort_index()
    if es:
        where = " y ".join(f"{c} en {y_}" if c > 1 else f"una en {y_}" for y_, c in yrs.items())
        txt = (f"Esta semana es la {rk['rank']}ª mayor {'depreciación' if rk['chg'] > 0 else 'apreciación'} del peso en "
               f"{rk['n_weeks']} semanas desde {mshort(rk['start'], 'es')} (percentil {n(rk['pct_rank'])}). Las {rk['n_larger']} "
               f"más fuertes: {where}.")
    else:
        where = " and ".join(f"{c} in {y_}" if c > 1 else f"one in {y_}" for y_, c in yrs.items())
        txt = (f"This is the peso's #{rk['rank']} largest weekly {'depreciation' if rk['chg'] > 0 else 'appreciation'} in "
               f"{rk['n_weeks']} weeks since {mshort(rk['start'], 'en')} ({n(rk['pct_rank'])}th percentile). The {rk['n_larger']} "
               f"larger ones: {where}.")
    tx = M + 32 + pg.width(rkt, 130, DISPLAY, "extra bold") + 36
    pg.justify(tx, y + 70, txt, 25, W - M - 32 - tx, 1.36, PAPER, SERIF)
    source(pg, y + bh - 62, ("Fuente: Elaboración propia con datos de Banxico (FIX). Cambio semanal: cierre del viernes; "
                             "semana actual: 7 días naturales.") if es else
           "Source: Own elaboration with Banxico data (FIX). Weekly change: Friday close; current week: 7 calendar days.",
           dark=True, x=M + 32, maxw=CW - 64)
    footer(pg, 4, lang)
    return pg


def page_agenda(s, v, t, lang, num, run) -> Page:
    es = lang == "es"
    pg = Page()
    header(pg, num, run, lang, 5)
    y = kicker(pg, 148, "Lo que viene" if es else "What's next")
    y = headline(pg, y, ["EN LA MIRA"] if es else ["ON THE RADAR"], cap=128) + 6
    rows = t["agenda"][:6]
    pg.hline(y, color=INK, lw=1.4)
    for r in rows:
        dd = r["day"].split()
        pg.text(M, y + 18, dd[0].upper(), 20, BLUE, SANS, "extra bold")
        pg.text(M, y + 42, dd[1] if len(dd) > 1 else "", 40, INK, DISPLAY, "extra bold")
        pg.text(M + 190, y + 20, f"{r['src']}{'  ·  ' + r['time'] + ' h' if r['time'] else ''}", 19, MUTED, SANS, "semibold")
        yy = pg.justify(M + 190, y + 48, r["what"], 27, CW - 190, 1.25, INK, SERIF)
        if r.get("prev"):
            pg.text(M + 190, yy + 2, r["prev"], 19, MUTED, SANS, style="italic")
            yy += 26
        y = max(y + 100, yy + 16)
        pg.hline(y)
    note = t.get("note")
    y += 40
    if note:
        y = kicker(pg, y, "Nota del autor" if es else "Author's note") + 10
        txt = note["text"]
        y0 = y
        y = pg.justify(M + 34, y, txt, 33, CW - 34, 1.38, INK, SERIF_D, "medium", "italic") + 8
        pg.rect(M, y0 + 4, 7, y - y0 - 12, BLUE)
        pg.text(W - M, y + 6, f"— {AUTHOR}", 26, INK, SANS, "semibold", ha="right")
        y += 60
    recent = t.get("recent") or []
    if recent and y < H - 300:
        y = kicker(pg, y, "Ya se publicó" if es else "Already out", MUTED)
        for r in recent[: int((H - 130 - y) // 40)]:
            pg.text(M, y, r["day"], 21, INK, SANS, "semibold")
            pg.text(M + 190, y, f"{r['src']}  ·  {r['what']}", 21, BODY, SANS)
            y += 38
    footer(pg, 5, lang)
    return pg


def page_back(s, v, t, lang, num, run, refs: List[str]) -> Page:
    es = lang == "es"
    pg = Page(INK)
    draw_logo(pg.ax, M, 84, 120, PAPER, BLUE, WHITE,
              "Boletín semanal de economía mexicana" if es else "Weekly bulletin on Mexico's economy", ON_INK,
              accent=BLUE_LT)
    nxt = run + timedelta(days=(7 - run.weekday()) % 7 or 7)
    y = 330
    pg.hline(y, color=GREEN_LT, lw=3.2)
    y += 34
    pg.text(M, y, track(("Siguiente número" if es else "Next issue").upper()), 22, BLUE_LT, SANS, "extra bold")
    y += 40
    lines = [f"Nº {num + 1}", (f"LUNES {nxt.day} DE {MES_L[nxt.month - 1].upper()}" if es else f"MONDAY, {MON_L[nxt.month - 1].upper()} {nxt.day}")]
    y = headline(pg, y, lines, cap=104, color=PAPER)
    y = pg.justify(M, y + 6, ("Cada lunes, los datos que movieron a la economía mexicana, qué significan para tu empresa y "
                              "una lectura firmada. Sígueme para recibirlo." if es else
                              "Every Monday: the data that moved Mexico's economy, what it means for your business and a "
                              "signed reading. Follow me to get it."), 28, CW, 1.32, PAPER, SERIF_D, "medium", "italic") + 24
    pg.text(M, y, track(("Contacto" if es else "Contact").upper()), 20, BLUE_LT, SANS, "extra bold")
    pg.text(M, y + 36, EMAIL, 34, PAPER, SANS, "semibold")
    pg.text(M, y + 84, f"{AUTHOR}  ·  {REPO_URL}", 22, ON_INK, SANS)
    y += 130
    pg.hline(y, color=ON_INK, lw=0.8)
    y += 22
    pg.text(M, y, track(("Método y fuentes" if es else "Method and sources").upper()), 20, BLUE_LT, SANS, "extra bold")
    y += 40
    for r in refs:
        y = pg.justify(M, y, r, 17, CW, 1.3, ON_INK, SANS) + 6
    footer(pg, 6, lang, dark=True, swipe=False)
    return pg


def references(lang: str) -> List[str]:
    from narrative import REFERENCES as R
    es = lang == "es"
    data = ("Datos: Banxico, Sistema de Información Económica (FIX, tasa objetivo, Encuesta de Expectativas); INEGI, Banco "
            "de Información Económica (INPC, IGAE); BIS Data Portal (tasas de política e inflación de pares); Reserva Federal, "
            "H.10 y FRED (tipos de cambio, índice amplio del dólar, rango de fondos federales).") if es else (
            "Data: Banxico SIE (FIX, policy rate, Expectations Survey); INEGI BIE (CPI, IGAE); BIS Data Portal (peer policy "
            "rates and inflation); Federal Reserve H.10 and FRED (exchange rates, broad dollar index, fed funds range).")
    out = [data] + [R[k]["full"] for k in ("banxico_neutral", "angeles", "capistran", "heath")]
    out.append(("Código, metodología y reglas del termómetro: " if es else "Code, methodology and thermometer rules: ") + REPO_URL)
    return out


def render(s: dict, v: dict, t: dict, lang: str, out_dir: Path, num: int = 1) -> dict:
    tl = t[lang]
    run = date.fromisoformat(s["run_date"])
    pages = [page_cover(s, v, tl, lang, num, run), page_thermo(s, v, tl, lang, num, run),
             page_peers(s, v, tl, lang, num, run), page_business(s, v, tl, lang, num, run),
             page_agenda(s, v, tl, lang, num, run), page_back(s, v, tl, lang, num, run, references(lang))]
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
    tl = t["es"]
    lead = tl["order"][0]
    cc = cover_copy(s, v, lead, "es")
    run = date.fromisoformat(s["run_date"])
    f, sc, pr, db, ic = s["fx"], v["thermo_score"], v["peers"], v["dollar"], v["import_cost"]
    names = {"inflation": "inflación", "core": "subyacente", "expectations": "expectativas", "real_rate": "tasa real",
             "fx": "tipo de cambio", "activity": "actividad"}
    red = [names[r["key"]] for r in v["thermometer"] if r["state"] == "tension"]
    bullets = [f"→ Termómetro MX Macro: {sc['tension']} señales en rojo" + (f" ({' y '.join(red)})" if red else "")
               + f", {sc['vigilancia']} en vigilancia y {sc['estable']} estable" + ("s" if sc["estable"] != 1 else "") + "."]
    if pr:
        mx = next(r for r in pr["rows"] if r["c"] == "MX")
        bullets.append(f"→ México frente a sus pares: lugar {pr['mx_rank']} de {pr['n']} en tasa real ex post ({n(mx['real'])}%).")
    if db:
        bullets.append(f"→ ¿Peso o dólar? Del {dshort(db['start'], 'es')} al {dshort(db['end'], 'es')}, el real cayó "
                       f"{n(db['usd_brl'])}%, el peso {n(db['usd_mxn_h10'])}% y el dólar amplio solo subió {n(db['usd_broad'])}%.")
    bullets.append(f"→ Para tu empresa: una importación de USD 100,000 cuesta hoy ${abs(ic['diff']):,.0f} pesos "
                   f"{'más' if ic['diff'] >= 0 else 'menos'} que hace una semana.")
    lead_txt = cc["dek"]
    if lead == "fx" and v["fx_rank"]["n_larger"]:
        yrs = pd.Series(pd.to_datetime(v["fx_rank"]["weeks"]["dates"][:-1]))
        vals = pd.Series(v["fx_rank"]["weeks"]["values"][:-1])
        c = v["fx_rank"]["chg"]
        worse = yrs[(vals >= c) if c > 0 else (vals <= c)].dt.year.value_counts().sort_index()
        lead_txt += " " + ("Las más fuertes: " + " y ".join(f"{k} en {y}" if k > 1 else f"una en {y}" for y, k in worse.items()) + ".")
    mine = f"Mi lectura: {tl['note']['text'][0].lower() + tl['note']['text'][1:]}\n\n" if tl.get("note") else ""
    days: Dict[str, List[str]] = {}
    for r in tl["agenda"][:3]:
        days.setdefault(r["day"], []).append(r["what"])
    nxt = "; ".join(f"{d_}, {' y '.join(w_)}" for d_, w_ in list(days.items())[:2])
    nm = _next_monday(run)
    title = " ".join(cc["lines"]).capitalize()
    return (f"MX Macro Monitor Nº {num} · {title}.\n\n{lead_txt}\n\n"
            "En el documento:\n" + "\n".join(bullets) + "\n\n" + mine
            + (f"En la mira: {nxt}.\n\n" if nxt else "")
            + f"Cada lunes, un número nuevo. Sígueme para recibir el Nº {num + 1} el lunes {nm.day} de {MES_L[nm.month - 1]}.\n"
            f"Comentarios y colaboraciones: {EMAIL}\n\n"
            "#EconomíaMexicana #Banxico #TipoDeCambio #Macroeconomía")


def comment_en(s: dict, v: dict, t: dict, num: int) -> str:
    lead = t["en"]["order"][0]
    cc = cover_copy(s, v, lead, "en")
    sc, ic = v["thermo_score"], v["import_cost"]
    note = t["en"].get("note")
    mine = f"\n\nMy take: {note['text']}" if note else ""
    return (f"English version · MX Macro Monitor No. {num}: {' '.join(cc['lines']).capitalize()}. {cc['dek']} "
            f"MX Macro thermometer: {sc['tension']} signals in the red, {sc['vigilancia']} on watch, {sc['estable']} stable. "
            f"A USD 100,000 import costs MXN {abs(ic['diff']):,.0f} {'more' if ic['diff'] >= 0 else 'less'} than a week ago."
            f"{mine}\n\nOfficial data from Banxico, INEGI, BIS and the Federal Reserve. Method and open-source code: {REPO_URL}")


def alt_text(s: dict, v: dict, t: dict, num: int) -> str:
    cc = cover_copy(s, v, t["es"]["order"][0], "es")
    sc = v["thermo_score"]
    return (f"Documento de {TOTAL} páginas, MX Macro Monitor Nº {num}. Portada: {' '.join(cc['lines']).lower()}. {cc['dek']} "
            f"Página 2: termómetro con {sc['tension']} señales en tensión, {sc['vigilancia']} en vigilancia y {sc['estable']} "
            "estable. Página 3: tasa real de México frente a Brasil, Chile, Colombia, Perú y Estados Unidos, y comparación "
            "del peso, el real y el dólar. Página 4: efecto en pesos sobre una importación de 100 mil dólares. Página 5: "
            "agenda y nota del autor. Página 6: contacto y fuentes.")

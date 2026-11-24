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
import typeset
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
NUM_ISSUE = 1

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


    def text(self, x, y, s, size=30, color=BODY, family=SANS, weight="regular", style="normal", ha="left",
             va="top", linespacing=1.0, track=0.0, **kw):
        """Shaped text (HarfBuzz kerning; optional tracking in em). A leading \x01 marks tracked caps."""
        if s.startswith("\x01"):
            s, track = s[1:], 0.12
        return typeset.draw(self.ax, x, y, s, size, color, family, weight, style, ha, va, track, linespacing)

    def width(self, s, size, family=SANS, weight="regular", style="normal") -> float:
        track = 0.0
        if s.startswith("\x01"):
            s, track = s[1:], 0.12
        return typeset.width(s, size, family, weight, style, track)

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
    pg.text(M + 62, 71, "Boletín semanal de economía mexicana" if lang == "es" else "Weekly briefing on Mexico’s economy",
            17, sub, SERIF_D, "medium", "italic")
    pg.text(W - M, 47, f"{'Nº' if lang == 'es' else 'No.'} {num}", 19, fg, SANS, "extra bold", ha="right")
    pg.text(W - M, 72, dlong(run, lang), 17, sub, SANS, ha="right")
    pg.hline(110, color=BLUE, lw=3.2)


def footer(pg: Page, page: int, lang: str, dark: bool = False, swipe: bool = True, hook: Optional[str] = None,
           email: bool = True):
    """Author + email on the left; progress segments (one per page) on the right."""
    page = PAGE or page
    fg, sub = (PAPER, ON_INK) if dark else (INK, MUTED)
    y = H - 66
    pg.hline(y - 18, color=ON_INK if dark else RULE, lw=0.8)
    pg.text(M, y, AUTHOR, 19, fg, SANS, "semibold")
    pg.text(M + pg.width(AUTHOR, 19, SANS, "semibold") + 12, y, f"·  MX Macro Monitor {'Nº' if lang == 'es' else 'No.'} {NUM_ISSUE}", 19, sub, SANS)
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
    """Cover copy. Headline = the fact with its figure; dek = how big it is."""
    f, i, a, p = s["fx"], s["inflation"], s.get("activity") or {}, s["policy"]
    es = lang == "es"
    if lead == "fx":
        up = f["chg_1w_pct"] > 0
        x = n(abs(f["chg_1w_pct"]))
        line = (f"EL PESO {'CAE' if up else 'SUBE'} {x}%") if es else (f"PESO {'FALLS' if up else 'GAINS'} {x}%")
        rk = v["fx_rank"]
        yr = rk["start"][:4]
        if es:
            short = (f"Solo {rk['n_larger']} de {rk['n_weeks']} semanas desde {yr} fueron peores." if up
                     else f"Solo {rk['n_larger']} de {rk['n_weeks']} semanas desde {yr} fueron mejores.")
        else:
            short = (f"Only {rk['n_larger']} of {rk['n_weeks']} weeks since {yr} were worse for the peso." if up
                     else f"Only {rk['n_larger']} of {rk['n_weeks']} weeks since {yr} were better for the peso.")
        kick, src = ("Tipo de cambio", "Fuente: Elaboración propia con datos de Banxico (FIX).") if es else (
            "Exchange rate", "Source: Author’s calculations based on Banxico FIX data.")
    elif lead == "inflation":
        line = f"INFLACIÓN: {n(i['yoy'], 2)}%" if es else f"INFLATION AT {n(i['yoy'], 2)}%"
        short = (f"La subyacente está en {n(i['core'], 2)}%; la meta de Banxico es 3%." if es
                 else f"Core inflation stands at {n(i['core'], 2)}%; Banxico's target is 3%.")
        kick, src = ("Inflación", "Fuente: Elaboración propia con datos de INEGI.") if es else (
            "Inflation", "Source: Author’s calculations based on INEGI data.")
    elif lead == "activity":
        down = a.get("mom", 0) < 0
        x = n(abs(a["mom"]))
        line = (f"LA ECONOMÍA {'CAE' if down else 'CRECE'} {x}%") if es else (f"ECONOMY {'SHRINKS' if down else 'GROWS'} {x}%")
        short = (f"Variación mensual del IGAE; a tasa anual, {n(a['yoy'], 1, True)}%." if es
                 else f"Monthly change in IGAE; {n(a['yoy'], 1, True)}% year on year.")
        kick, src = ("Actividad económica", "Fuente: Elaboración propia con datos de INEGI.") if es else (
            "Economic activity", "Source: Author’s calculations based on INEGI data.")
    else:
        line = f"TASA EN {n(p['rate'], 2)}%" if es else f"POLICY RATE AT {n(p['rate'], 2)}%"
        short = (f"La tasa real ex ante está en {n(p['real_ex_ante'], 2)}%." if es
                 else f"The ex-ante real rate stands at {n(p['real_ex_ante'], 2)}%.")
        kick, src = ("Política monetaria", "Fuente: Elaboración propia con datos de Banxico.") if es else (
            "Monetary policy", "Source: Author’s calculations based on Banxico data.")
    return {"kicker": kick, "lines": [line], "short": short, "dek": short, "source": src}


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
    pg.text(x, y, ("Cambio semanal del FIX, % · arriba = peso más débil" if es
                   else "Weekly change in the peso vs. the dollar (FIX), % · up = weaker peso"), 22, MUTED, SANS)
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


# --- pages (v7: 6 páginas, títulos con el dato, firma de columnista) -----------------------------
HL = 124
Y_KICK = 168
Y_HEAD = 226
Y_SRC = H - 168
ROLE = {"es": "Economista Senior", "en": "Senior Economist"}


def head_lines(pg: Page, text: str, size: float = HL, maxw: float = CW) -> tuple:
    """One line if it fits; otherwise two balanced lines; shrink only if two lines still overflow."""
    if pg.width(text, size, DISPLAY, "extra bold") <= maxw:
        return [text], size
    words = text.split()
    best = None
    for k in range(1, len(words)):
        a, b = " ".join(words[:k]), " ".join(words[k:])
        wmax = max(pg.width(a, size, DISPLAY, "extra bold"), pg.width(b, size, DISPLAY, "extra bold"))
        if best is None or wmax < best[0]:
            best = (wmax, [a, b])
    wmax, lines = best
    return lines, (size if wmax <= maxw else size * maxw / wmax)


def inner(pg: Page, kick: str, title: str, dek: Optional[str], num, run, lang, page) -> float:
    header(pg, num, run, lang, page)
    kicker(pg, Y_KICK, kick)
    lines, size = head_lines(pg, title)
    y = Y_HEAD
    for k, l in enumerate(lines):
        pg.text(M, y + k * size * 1.0, l, size, INK, DISPLAY, "extra bold")
    y += len(lines) * size * 1.0 + 22
    if dek:
        y = pg.justify(M, y, dek, 36, CW, 1.25, INK, SERIF_D, "medium", "italic") + 10
    return y + 36


def short_event(what: str) -> str:
    """Agenda label for the back cover: drop the period; keep an acronym when the name has one (ENOE)."""
    w = what.split(" (")[0]
    if w.startswith("Quarterly Report"):
        return "Banxico " + w
    if ", " in w and w.split(", ")[-1].isupper():
        return w.split(", ")[-1]
    return w


def src_line(pg: Page, txt: str, dark=False):
    pg.text(M, Y_SRC, txt, 19, ON_INK if dark else MUTED, SANS)


def byline(pg: Page, x: float, y: float, lang: str, dark: bool = False):
    """Columnist byline: 'Por' + name in bold sans + role in italic serif."""
    fg, sub = (PAPER, ON_INK) if dark else (INK, MUTED)
    por = "Por " if lang == "es" else "By "
    pg.text(x, y, por, 26, sub, SERIF_D, "medium", "italic", va="baseline")
    x += pg.width(por, 26, SERIF_D, "medium", "italic") + 4
    pg.text(x, y, AUTHOR, 26, fg, SANS, "extra bold", va="baseline")
    x += pg.width(AUTHOR, 26, SANS, "extra bold")
    pg.text(x, y, f", {ROLE[lang]}", 26, sub, SERIF_D, "medium", "italic", va="baseline")


def page_cover(s, v, t, lang, num, run) -> Page:
    es = lang == "es"
    pg = Page()
    lead = t["order"][0]
    cc = cover_copy(s, v, lead, lang)
    pg.rect(0, 0, W, 250, BLUE)
    draw_logo(pg.ax, M, 52, 104, PAPER, PAPER, BLUE, accent=PAPER)
    nw = pg.width(str(num), 170, DISPLAY, "extra bold")
    pg.text(W - M, 40, str(num), 170, PAPER, DISPLAY, "extra bold", ha="right")
    pg.text(W - M - nw - 12, 40, "Nº" if es else "No.", 34, PAPER, DISPLAY, "extra bold", ha="right")
    pg.text(M, 204, track((dlong(run, "es") + "  ·  Boletín semanal de economía mexicana" if es
                           else dlong(run, "en") + "  ·  Weekly briefing on Mexico’s economy").upper()), 16, PAPER, SANS, "semibold")
    kicker(pg, 292, cc["kicker"])
    size = pg.fit(cc["lines"], CW, cap=170)
    pg.text(M, 334, cc["lines"][0], size, INK, DISPLAY, "extra bold")
    y = 334 + size * 1.0 + 26
    y = pg.justify(M, y, cc["short"], 38, CW, 1.22, INK, SERIF_D, "medium", "italic") + 22
    byline(pg, M, y + 26, lang)
    y += 26 + 44
    pg.hline(y, color=RULE)
    y += 34
    bottom = Y_SRC - 70
    if lead == "fx":
        chart_fx_weeks(pg, s, v, lang, M, y, CW, bottom - y)
    elif lead == "inflation":
        chart_line(pg, s["inflation"]["chart"], "Inflación anual, %" if es else "Annual inflation, %",
                   "Franja: intervalo de Banxico (2%–4%)" if es else "Band: Banxico's 2%–4% range", M, y, CW, bottom - y, band=(2, 4))
    elif lead == "activity":
        chart_line(pg, s["activity"]["yoy_chart"], "IGAE, variación anual, %" if es else "IGAE, year-on-year change, %",
                   "Serie desestacionalizada" if es else "Seasonally adjusted", M, y, CW, bottom - y)
    else:
        chart_line(pg, s["policy"]["real_chart"], "Tasa real ex ante, %" if es else "Ex-ante real rate, %",
                   "Franja: rango neutral de Banxico" if es else "Band: Banxico's neutral range", M, y, CW, bottom - y,
                   band=tuple(s["policy"]["neutral_range"]))
    src_line(pg, cc["source"])
    footer(pg, 1, lang)
    return pg


def page_thermo(s, v, t, lang, num, run) -> Page:
    es = lang == "es"
    pg = Page()
    sc, rows = v["thermo_score"], v["thermometer"]
    names = {"es": {"inflation": "Inflación general", "core": "Inflación subyacente", "expectations": "Expectativas de inflación",
                    "real_rate": "Tasa real (ex ante)", "fx": "Tipo de cambio (semanal)", "activity": "Actividad (mensual)"},
             "en": {"inflation": "Headline inflation", "core": "Core inflation", "expectations": "Inflation expectations",
                    "real_rate": "Real rate (ex ante)", "fx": "Exchange rate (w/w)", "activity": "Economic activity (m/m)"}}[lang]
    word = {"es": {"estable": "Estable", "vigilancia": "Vigilancia", "tension": "Tensión", "na": "s. d."},
            "en": {"estable": "Stable", "vigilancia": "Watch", "tension": "Alert", "na": "n/a"}}[lang]
    red = [names[r["key"]].lower() for r in rows if r["state"] == "tension"]
    if es:
        title = f"{sc['tension']} DE 6 SEÑALES EN ROJO" if sc["tension"] else "NINGUNA SEÑAL EN ROJO"
        dek = (f"En tensión: {' y '.join(red)}." if red else "Ninguna de las seis señales está en tensión.")
    else:
        title = f"{sc['tension']} OF 6 SIGNALS FLASH RED" if sc["tension"] else "NO RED FLAGS"
        red_en = [{"Exchange rate": "the exchange rate", "Economic activity": "economic activity"}.get(names[r["key"]], names[r["key"]].lower())
                  for r in rows if r["state"] == "tension"]
        dek = (f"On alert: {' and '.join(red_en)}." if red_en else "None of the six signals is on alert.")
    y = inner(pg, "Termómetro MX Macro" if es else "MX Macro thermometer", title, None, num, run, lang, 2)
    order = {"tension": 0, "vigilancia": 1, "estable": 2, "na": 3}
    rh = (Y_SRC - 40 - y) / 6
    pg.hline(y, color=INK, lw=1.4)
    for r in sorted(rows, key=lambda r: order[r["state"]]):
        cy = y + rh / 2
        pg.rect(M, cy - 14, 28, 28, STATE_COLOR.get(r["state"], MUTED))
        pg.text(M + 52, cy, names[r["key"]], 34, INK, SANS, "semibold", va="center")
        val = r["value"]
        vs = (n(val, 1, r["key"] in ("fx", "activity")) + "%") if val is not None else "–"
        pg.text(M + 680, cy, vs, 56, INK, DISPLAY, "extra bold", ha="right", va="center")
        pg.text(W - M, cy, word[r["state"]], 30, STATE_COLOR.get(r["state"], MUTED), SANS, "extra bold", ha="right", va="center")
        y += rh
        pg.hline(y)
    src_line(pg, "Fuente: Elaboración propia con datos de INEGI y Banxico. Reglas en el texto del post." if es
             else "Source: Author’s calculations based on INEGI and Banxico data. Methodology in the post.")
    footer(pg, 2, lang)
    return pg


def page_peers(s, v, t, lang, num, run) -> Page:
    from valueadd import PEER_NAMES
    es = lang == "es"
    pg = Page()
    pr = v["peers"]
    mx = next(r for r in pr["rows"] if r["c"] == "MX")
    nm = PEER_NAMES[lang]
    above = [nm[r["c"]] for r in pr["rows"][: pr["mx_rank"] - 1]]
    ordn = {"es": ["", "PRIMERO", "SEGUNDO", "TERCERO", "CUARTO", "QUINTO", "SEXTO"],
            "en": ["", "1ST", "2ND", "3RD", "4TH", "5TH", "6TH"]}
    if es:
        title = f"MÉXICO, {ordn['es'][pr['mx_rank']]} EN TASA REAL"
        dek = (f"Solo {' y '.join(above)} están más arriba." if above else "La más alta del grupo.")
    else:
        title = f"MEXICO RANKS {ordn['en'][pr['mx_rank']]} IN REAL RATES"
        dek = (f"Behind only {' and '.join(above)}." if above else "The highest in the group.")
    y = inner(pg, "México frente a sus pares" if es else "Mexico vs. its peers", title, dek, num, run, lang, 3)
    pg.text(M, y - 10, ("Tasa de política menos inflación observada (ex post), pp" if es
                        else "Policy rate minus headline inflation (ex post), pp"), 22, MUTED, SANS)
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
             else f"Source: Author’s calculations based on BIS and Banxico data; inflation as of {mshort(pr['cpi_month'], 'en')}.")
    footer(pg, 3, lang)
    return pg


def page_dollar(s, v, t, lang, num, run) -> Page:
    es = lang == "es"
    pg = Page()
    db = v["dollar"]
    peso_only = db["usd_broad"] < db["usd_mxn_h10"] / 2
    if es:
        title = "NO FUE EL DÓLAR" if peso_only else "FUE EL DÓLAR"
        dek = ("El real y el peso cayeron mucho más de lo que subió el dólar." if peso_only
               else "El dólar se fortaleció frente a casi todas las monedas.")
    else:
        title = "IT WASN’T THE DOLLAR" if peso_only else "IT WAS THE DOLLAR"
        dek = ("The real and the peso fell far more than the dollar rose." if peso_only
               else "The dollar strengthened against almost every currency.")
    y = inner(pg, "¿Peso o dólar?" if es else "Peso or dollar?", title, dek, num, run, lang, 4)
    st, en_ = pd.Timestamp(db["start"]), pd.Timestamp(db["end"])
    pg.text(M, y - 10, (f"Del {st.day} al {dshort(db['end'], 'es')}, % · datos de la Fed (otra semana que el FIX)" if es
                        else f"{MES['en'][st.month - 1]}. {st.day}–{en_.day}, % change · Fed data (differs from the FIX week)"), 22, MUTED, SANS)
    y += 40
    items = [("Real brasileño: se depreció" if es else "Brazilian real: weakened", db["usd_brl"], CTX, False),
             ("Peso mexicano: se depreció" if es else "Mexican peso: weakened", db["usd_mxn_h10"], BLUE, True),
             ("Índice amplio del dólar: se fortaleció" if es else "Broad dollar index: strengthened", db["usd_broad"], INK, False)]
    vmax = max(abs(x) for _, x, _, _ in items)
    bw, bh = CW - 150, 84
    step = (Y_SRC - 60 - y) / 3
    for k, (lab, val, col, bold) in enumerate(items):
        yy = y + k * step + (step - bh - 44) / 2
        pg.text(M, yy, lab, 30, INK, SANS, "extra bold" if bold else "regular")
        pg.rect(M, yy + 44, max(abs(val) / vmax * bw, 3), bh, col, z=3)
        pg.text(M + abs(val) / vmax * bw + 16, yy + 44 + bh / 2, f"{n(val, 1, True)}%", 40, INK, DISPLAY, "extra bold", va="center")
    src_line(pg, "Fuente: Elaboración propia con datos de la Reserva Federal (H.10); el FIX de Banxico usa otro corte de fechas." if es
             else "Source: Author’s calculations based on Federal Reserve H.10 data; Banxico’s FIX uses a different window.")
    footer(pg, 4, lang)
    return pg


def page_business(s, v, t, lang, num, run) -> Page:
    es = lang == "es"
    pg = Page()
    ic = v["import_cost"]
    up = ic["diff"] >= 0
    title = ("IMPORTAR CUESTA MÁS" if up else "IMPORTAR CUESTA MENOS") if es else ("IMPORTS GOT PRICIER" if up else "IMPORTS GOT CHEAPER")
    dek = "Por cada USD 100,000 importados pagas hoy:" if es else "For every US$100,000 in imports, you now pay:"
    y = inner(pg, "Para tu empresa" if es else "For your business", title, dek, num, run, lang, 5)
    big = f"{abs(ic['diff']):,.0f}"
    size = pg.fit([big], CW, cap=280)
    block = size * 1.0 + 70
    y += max(0, (Y_SRC - 60 - y - block) / 2) - 20
    pg.text(M - 4, y, big, size, BLUE, DISPLAY, "extra bold")
    y += size * 1.0 + 30
    pg.text(M, y, (f"pesos {'más' if up else 'menos'} que hace una semana." if es
                   else f"{'more' if up else 'fewer'} pesos than a week ago."), 40, INK, SERIF_D, "medium", "italic")
    src_line(pg, "Fuente: Cálculo propio con el FIX de Banxico. La cuenta completa, en el texto del post." if es
             else "Source: Author’s calculation based on Banxico’s FIX rate. Full math in the post.")
    footer(pg, 5, lang)
    return pg


def page_back(s, v, t, lang, num, run) -> Page:
    """Back cover: what's next, next issue, author block with the email (only place it appears)."""
    es = lang == "es"
    pg = Page(INK)
    draw_logo(pg.ax, M, 76, 96, PAPER, BLUE, WHITE, None, ON_INK, accent=BLUE_LT)
    y = 230
    pg.hline(y, color=BLUE_LT, lw=3.2)
    pg.text(M, y + 40, track("LO QUE VIENE" if es else "COMING UP"), 22, BLUE_LT, SANS, "extra bold")
    y += 92
    days: Dict[str, List[dict]] = {}
    for r in t["agenda"][:5]:
        days.setdefault(r["day"], []).append(r)
    for day, evs in list(days.items())[:3]:
        d0 = day.split()
        pg.text(M, y, day.upper(), 30, PAPER, DISPLAY, "extra bold")
        pg.text(M + 230, y, " · ".join(short_event(e["what"]) for e in evs[:2]), 28, PAPER, SERIF)
        y += 56
    y += 30
    pg.hline(y, color=ON_INK, lw=0.8)
    nxt = _next_monday(run)
    pg.text(M, y + 40, track("SIGUIENTE NÚMERO" if es else "NEXT ISSUE"), 22, BLUE_LT, SANS, "extra bold")
    nl = (f"Nº {num + 1}: LUNES {nxt.day} DE {MES_L[nxt.month - 1].upper()}" if es
          else f"NO. {num + 1}: MONDAY, {MON_L[nxt.month - 1].upper()} {nxt.day}")
    lines, size = head_lines(pg, nl, 96)
    yy = y + 86
    for k, l in enumerate(lines):
        pg.text(M, yy + k * size, l, size, PAPER, DISPLAY, "extra bold")
    yy += len(lines) * size + 24
    pg.text(M, yy, "Sígueme para recibirlo." if es else "Follow me so you don’t miss it.", 40, PAPER, SERIF_D, "medium", "italic")
    # author block
    ay = H - 400
    pg.hline(ay, color=ON_INK, lw=0.8)
    pg.text(M, ay + 46, AUTHOR, 56, PAPER, DISPLAY, "extra bold")
    pg.text(M, ay + 122, ROLE[lang], 30, ON_INK, SERIF_D, "medium", "italic")
    pg.text(M, ay + 172, EMAIL, 30, BLUE_LT, SANS, "semibold")
    footer(pg, TOTAL, lang, dark=True, swipe=False)
    return pg


def render(s: dict, v: dict, t: dict, lang: str, out_dir: Path, num: int = 1) -> dict:
    global TOTAL, PAGE
    tl = t[lang]
    run = date.fromisoformat(s["run_date"])
    builders = [page_cover, page_thermo, page_peers, page_dollar, page_business, page_back]
    if not v.get("peers"):
        builders.remove(page_peers)
    if not v.get("dollar"):
        builders.remove(page_dollar)
    TOTAL = len(builders)
    global NUM_ISSUE
    NUM_ISSUE = num
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
            "Subject": "Boletín semanal de economía mexicana" if lang == "es" else "Weekly briefing on Mexico’s economy"}
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
    return (f"MX Macro Monitor Nº {num} · {' '.join(cc['lines']).capitalize()}.\n\n{cc['short']}"
            + "\n\n" + "\n".join(lines) + "\n\n" + mine + "\n".join(how) + f"\n{src}\n\n"
            f"Cada lunes, un número nuevo. Sígueme para recibir el Nº {num + 1} el lunes {nm.day} de {MES_L[nm.month - 1]}.\n"
            f"Contacto: {EMAIL}\n\n#EconomíaMexicana #Banxico #TipoDeCambio")


def comment_en(s: dict, v: dict, t: dict, num: int) -> str:
    lead = t["en"]["order"][0]
    cc = cover_copy(s, v, lead, "en")
    sc, ic, pr, db = v["thermo_score"], v["import_cost"], v["peers"], v["dollar"]
    note = t["en"].get("note")
    parts = [f"English version · MX Macro Monitor No. {num}: {cc['lines'][0].capitalize()}. {cc['short']}",
             f"MX Macro thermometer: {sc['tension']} of 6 signals flashing red, {sc['vigilancia']} on watch, {sc['estable']} stable."]
    if pr:
        mx = next(r for r in pr["rows"] if r["c"] == "MX")
        parts.append(f"Mexico's ex-post real rate ({n(mx['real'])} pp) ranks #{pr['mx_rank']} of {pr['n']} among its peers.")
    if db:
        parts.append(f"It wasn't the dollar: the real fell {n(db['usd_brl'])}% and the peso {n(db['usd_mxn_h10'])}%, "
                     f"while the broad dollar index rose just {n(db['usd_broad'])}%." if db["usd_broad"] < db["usd_mxn_h10"] / 2 else
                     f"The broad dollar index rose {n(db['usd_broad'])}%.")
    parts.append(f"A USD 100,000 import now costs MXN {abs(ic['diff']):,.0f} {'more' if ic['diff'] >= 0 else 'less'} than a week ago.")
    mine = f"\n\nMy take: {note['text']}" if note else ""
    return " ".join(parts) + mine + "\n\nOfficial data from Banxico, INEGI, the BIS and the Federal Reserve."


def alt_text(s: dict, v: dict, t: dict, num: int) -> str:
    cc = cover_copy(s, v, t["es"]["order"][0], "es")
    sc, ic = v["thermo_score"], v["import_cost"]
    return (f"Documento de {TOTAL} páginas, MX Macro Monitor Nº {num}, por Isaac Tienda. Portada: {cc['lines'][0].lower()}; "
            f"{cc['short']} Página 2: {sc['tension']} de 6 señales del termómetro en rojo. Página 3: tasa real de México frente a "
            "Brasil, Colombia, Chile, Estados Unidos y Perú. Página 4: el real y el peso cayeron más de lo que subió el dólar. "
            f"Página 5: importar USD 100,000 cuesta {abs(ic['diff']):,.0f} pesos {'más' if ic['diff'] >= 0 else 'menos'} que hace una semana. "
            "Página 6: agenda, siguiente número y contacto.")

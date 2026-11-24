"""
LinkedIn carousel renderer, v4 — institutional bulletin style.

Five 1080x1350 (4:5) pages exported as one PDF (LinkedIn "document" post):

    1 Gráfica de la semana  masthead · headline · plain-language dek · Gráfica 1 · notes
    2 Indicadores clave     Banxico-style key-indicator table with trend lines and footnotes
    3 Gráfica 2             second topic, same template as page 1 without the masthead band
    4 Lectura del autor     signed note (config/nota_autor.yml) + what to watch this week
    5 Notas y referencias   methodology, glossary, references, how to follow

Conventions follow central-bank and multilateral chart practice: descriptive chart
title + units subtitle, notes then source under the chart, last observation stated,
direct labels instead of legends, no gridlines (author's rule), abbreviations
explained. Coordinates are px of the 1080x1350 page (1 px = 0.72 pt). On a phone the
page is shown ~390 px wide (×0.36): body text ≥ 34 px, notes ≥ 24 px.
Tokens: docs/DESIGN_SYSTEM.md.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import List, Optional

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker as mticker  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

from config import AUTHOR, AUTHOR_ROLE_EN, AUTHOR_ROLE_ES, FONT_DIR, REPO_URL
from narrative import REFERENCES, SOURCE_LINE, day, day_year, month, signed

W, H = 1080, 1350
M = 84

# --- tokens (docs/DESIGN_SYSTEM.md) ----------------------------------------------------
INK = "#0B1F33"       # masthead band, headlines, figures
TEXT = "#1F2933"      # body (14.8:1)
MUTED = "#52606D"     # subtitles, notes, sources (6.5:1)
AXIS = "#66717F"      # tick labels (5.0:1)
RULE = "#D9DEE5"      # hairlines, x baseline
BG = "#FFFFFF"
TINT = "#F4F6F9"      # table header / zebra
BLUE = "#1F5FAD"      # series 1, latest bar (6.4:1)
BLUE_CTX = "#6F95C9"  # context bars (3.1:1, meets 1.4.11)
ORANGE = "#D9692B"    # series 2, comparison only (3.5:1, never text)
BAND = "#E9EEF5"      # reference bands

for f in FONT_DIR.glob("*.ttf"):
    font_manager.fontManager.addfont(str(f))
plt.rcParams.update({"font.family": "Source Sans 3", "pdf.fonttype": 42, "axes.unicode_minus": True})
SERIF, SERIF_D, SANS = "Source Serif 4", "Source Serif 4 Display", "Source Sans 3"
MES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MES_L = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre"]


def pt(px: float) -> float:
    return px * 0.72


def long_date(d: str, lang: str) -> str:
    x = date.fromisoformat(d)
    return f"{x.day} de {MES_L[x.month - 1]} de {x.year}" if lang == "es" else x.strftime("%B %-d, %Y")


# --- canvas ---------------------------------------------------------------------------------
class Page:
    def __init__(self):
        self.fig = plt.figure(figsize=(10.8, 13.5), dpi=100)
        self.fig.patch.set_facecolor(BG)
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, W)
        self.ax.set_ylim(H, 0)
        self.ax.axis("off")
        self.r = self.fig.canvas.get_renderer()

    def text(self, x, y, s, size=34, color=TEXT, weight="regular", family=SANS, ha="left", va="top", style="normal"):
        return self.ax.text(x, y, s, fontsize=pt(size), color=color, fontweight=weight, family=family, ha=ha, va=va,
                            fontstyle=style)

    def width(self, s, size, weight="regular", family=SANS, style="normal") -> float:
        t = self.text(0, 0, s, size=size, weight=weight, family=family, style=style)
        w = t.get_window_extent(self.r).width / self.fig.dpi * 100
        t.remove()
        return w

    def wrap(self, s, size, maxw, weight="regular", family=SANS, style="normal") -> List[str]:
        lines, cur = [], ""
        for word in s.split():
            trial = f"{cur} {word}".strip()
            if not cur or self.width(trial, size, weight, family, style) <= maxw:
                cur = trial
            else:
                lines.append(cur)
                cur = word
        return lines + ([cur] if cur else [])

    def para(self, x, y, s, size=34, maxw=W - 2 * M, lh=1.3, color=TEXT, weight="regular", family=SANS,
             style="normal") -> float:
        for k, ln in enumerate(self.wrap(s, size, maxw, weight, family, style)):
            self.text(x, y + k * size * lh, ln, size=size, color=color, weight=weight, family=family, style=style)
        return y + len(self.wrap(s, size, maxw, weight, family, style)) * size * lh

    def height(self, s, size, maxw, lh=1.3, weight="regular", family=SANS, style="normal") -> float:
        return len(self.wrap(s, size, maxw, weight, family, style)) * size * lh

    def rect(self, x, y, w, h, color):
        self.ax.add_patch(Rectangle((x, y), w, h, fc=color, ec="none"))

    def hline(self, y, x0=M, x1=W - M, color=RULE, lw=1.2):
        self.ax.plot([x0, x1], [y, y], color=color, lw=lw, solid_capstyle="butt")

    def axes(self, x, y, w, h):
        return self.fig.add_axes([x / W, 1 - (y + h) / H, w / W, h / H])


# --- chrome -------------------------------------------------------------------------------------
def masthead(pg: Page, s: dict, lang: str, full: bool):
    """Full masthead on page 1; slim running head elsewhere."""
    wk = date.fromisoformat(s["run_date"]).isocalendar()[1]
    if full:
        pg.rect(0, 0, W, 14, INK)
        pg.text(M, 50, "MX Macro Monitor", size=40, color=INK, weight="semibold", family=SERIF_D)
        pg.text(W - M, 52, (f"Semana {wk} · {long_date(s['run_date'], lang)}" if lang == "es"
                            else f"Week {wk} · {long_date(s['run_date'], lang)}"), size=26, color=MUTED, ha="right")
        pg.text(M, 104, "Boletín semanal de coyuntura económica de México" if lang == "es"
                else "Weekly bulletin on Mexico's economy", size=26, color=MUTED)
        pg.hline(150, color=INK, lw=1.6)
        return 182
    pg.text(M, 52, "MX Macro Monitor", size=28, color=INK, weight="semibold", family=SERIF_D)
    pg.text(W - M, 54, (f"Semana {wk}" if lang == "es" else f"Week {wk}"), size=24, color=MUTED, ha="right")
    pg.hline(98, color=INK, lw=1.2)
    return 132


def footer(pg: Page, idx: int, total: int, lang: str):
    pg.hline(H - 92)
    pg.text(M, H - 72, f"{AUTHOR} · {AUTHOR_ROLE_ES if lang == 'es' else AUTHOR_ROLE_EN}", size=24, color=MUTED)
    pg.text(W - M, H - 72, f"{idx}/{total}", size=24, color=MUTED, ha="right")


def notes_block(pg: Page, y: float, lines: List[str], size=24) -> float:
    for ln in lines:
        y = pg.para(M, y, ln, size=size, color=MUTED, lh=1.3) + 4
    return y


# --- charts (no gridlines; direct labels with series names) -----------------------------------------
def ser(payload) -> pd.Series:
    return pd.Series(payload["values"], index=pd.to_datetime(payload["dates"]))


def clean(ax, pct=False, decimals=None, nticks=4):
    ax.set_facecolor("none")
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(RULE)
    ax.spines["bottom"].set_linewidth(1.2)
    ax.grid(False)
    ax.tick_params(axis="both", colors=AXIS, labelsize=pt(26), length=0, pad=10)
    ax.yaxis.set_major_locator(mticker.MaxNLocator(nticks, min_n_ticks=3))

    def fmt(v, _):
        d = decimals if decimals is not None else (0 if float(v).is_integer() else 1)
        return (f"{v:.{d}f}" + ("%" if pct else "")).replace("-", "−")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(fmt))


def month_ticks(ax, lang, every=6):
    names = MES if lang == "es" else MON
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=every))
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(
        lambda v, _: f"{names[mdates.num2date(v).month - 1]} {str(mdates.num2date(v).year)[2:]}"))


def lab(ax, x, y, s, dx=14, dy=0, size=28, color=INK, weight="semibold", ha="left", va="center"):
    ax.annotate(s, (x, y), xytext=(dx, dy), textcoords="offset points", fontsize=pt(size), color=color,
                fontweight=weight, ha=ha, va=va, annotation_clip=False, family=SANS)


def draw_fx(ax, s, lang):
    f = s["fx"]
    x = ser(f["chart"])
    ax.plot(x.index, x.values, color=BLUE, lw=3.2, solid_capstyle="round", solid_joinstyle="round")
    ax.scatter([x.index[-1]], [x.iloc[-1]], s=110, color=BLUE, zorder=5, edgecolor="white", linewidth=2.5)
    lab(ax, x.index[-1], x.iloc[-1], f"{x.iloc[-1]:.2f}")
    lo_d = pd.Timestamp(f["low_52w_date"])
    if lo_d != x.index[-1]:
        ax.scatter([lo_d], [f["low_52w"]], s=70, color=MUTED, zorder=5, edgecolor="white", linewidth=2)
        lab(ax, lo_d, f["low_52w"], ("mínimo " if lang == "es" else "low ") + f"{f['low_52w']:.2f}", dx=0, dy=-26,
            size=26, color=MUTED, weight="regular", ha="center", va="top")
    clean(ax, decimals=1)
    month_ticks(ax, lang, every=3)
    pad = (x.max() - x.min()) * 0.2
    ax.set_ylim(x.min() - pad * 1.6, x.max() + pad * 0.5)


def draw_activity(ax, s, lang):
    lvl = ser(s["activity"]["chart"])
    mom = (lvl.pct_change() * 100).dropna().tail(24)
    ax.bar(mom.index, mom.values, width=21, color=[BLUE_CTX] * (len(mom) - 1) + [BLUE], edgecolor="white", linewidth=2)
    ax.axhline(0, color=INK, lw=1.2)
    v = mom.iloc[-1]
    lab(ax, mom.index[-1], v, f"{v:+.1f}%".replace("-", "−"), dx=0, dy=-12 if v < 0 else 10, ha="center",
        va="top" if v < 0 else "bottom")
    clean(ax, pct=True)
    ax.spines["bottom"].set_visible(False)
    month_ticks(ax, lang, every=6)
    m = max(abs(mom.min()), abs(mom.max())) * 1.35
    ax.set_ylim(-m, m)


def draw_inflation(ax, s, lang):
    i = s["inflation"]
    g = ser(i["chart"])
    ax.axhspan(i["band"][0], i["band"][1], color=BAND, lw=0, zorder=0)
    ax.axhline(i["target"], color=AXIS, lw=1.4, ls=(0, (2, 3)), zorder=1)
    ax.plot(g.index, g.values, color=BLUE, lw=3.2, solid_capstyle="round", zorder=3)
    names = ("General", "Subyacente") if lang == "es" else ("Headline", "Core")
    if i.get("core_chart"):
        c = ser(i["core_chart"])
        ax.plot(c.index, c.values, color=ORANGE, lw=3.2, solid_capstyle="round", zorder=3)
        up = c.iloc[-1] >= g.iloc[-1]
        lab(ax, c.index[-1], c.iloc[-1], f"{names[1]} {c.iloc[-1]:.2f}%", dy=16 if up else -16)
        lab(ax, g.index[-1], g.iloc[-1], f"{names[0]} {g.iloc[-1]:.2f}%", dy=-16 if up else 16)
        lo, hi = min(g.min(), c.min(), i["band"][0]) - 0.3, max(g.max(), c.max(), i["band"][1]) + 0.3
    else:
        lab(ax, g.index[-1], g.iloc[-1], f"{names[0]} {g.iloc[-1]:.2f}%")
        lo, hi = min(g.min(), i["band"][0]) - 0.3, max(g.max(), i["band"][1]) + 0.3
    clean(ax, pct=True)
    month_ticks(ax, lang, every=6)
    ax.set_ylim(lo, hi)


def draw_policy(ax, s, lang):
    p = s["policy"]
    r = ser(p["real_chart"])
    lo, hi = p.get("neutral_range", [1.8, 3.6])
    ax.axhspan(lo, hi, color=BAND, lw=0, zorder=0)
    ax.text(r.index[0], hi - 0.1, ("  rango neutral" if lang == "es" else "  neutral range"), color=MUTED,
            fontsize=pt(26), va="top", ha="left", family=SANS)
    ax.plot(r.index, r.values, color=BLUE, lw=3.2, solid_capstyle="round", zorder=3)
    cur = p["real_ex_ante"]
    ax.scatter([r.index[-1]], [cur], s=110, color=BLUE, zorder=5, edgecolor="white", linewidth=2.5)
    lab(ax, r.index[-1], cur, f"{cur:.2f}%")
    clean(ax, pct=True)
    month_ticks(ax, lang, every=6)
    ax.set_ylim(min(r.min(), lo) - 0.6, max(r.max(), hi) + 0.6)


DRAW = {"fx": draw_fx, "activity": draw_activity, "inflation": draw_inflation, "policy": draw_policy}
RIGHT_ROOM = {"fx": 130, "activity": 40, "inflation": 260, "policy": 130}


def chart_page(s, t, key, lang, idx, total, chart_no: int, first: bool) -> Page:
    pg = Page()
    ed = t["ed"][key]
    y = masthead(pg, s, lang, full=first)
    y = pg.para(M, y, ed["head"], size=62 if first else 58, color=INK, weight="semibold", family=SERIF_D, lh=1.12)
    y = pg.para(M, y + 22, ed["dek"], size=34, color=TEXT, lh=1.36) + 34

    # chart block: number + title, units subtitle, chart, notes, source
    gl = "Gráfica" if lang == "es" else "Chart"
    pg.text(M, y, f"{gl} {chart_no}. {ed['chart_title']}", size=30, color=INK, weight="semibold")
    y = pg.para(M, y + 40, ed["chart_sub"], size=26, color=MUTED) + 12
    notes = [ed["note"], ed["source"]]
    notes_h = sum(pg.height(n, 24, W - 2 * M) + 4 for n in notes)
    bottom = H - 112
    ch = bottom - notes_h - 70 - y
    ax = pg.axes(M + 70, y + 6, W - 2 * M - 70 - RIGHT_ROOM[key], max(260, ch))
    DRAW[key](ax, s, lang)
    notes_block(pg, bottom - notes_h, notes)
    footer(pg, idx, total, lang)
    return pg


# --- page 2: key indicators (Banxico "Indicadores económicos clave" style) -------------------------
def trend(pg: Page, payload, x, y, w, h):
    if not payload:
        return
    v = ser(payload)
    ax = pg.axes(x, y, w, h)
    ax.axis("off")
    ax.plot(v.index, v.values, color=BLUE, lw=2.4, solid_capstyle="round")
    ax.scatter([v.index[-1]], [v.iloc[-1]], s=36, color=BLUE, zorder=5)
    rng = (v.max() - v.min()) or 1
    ax.set_ylim(v.min() - rng * 0.12, v.max() + rng * 0.12)


def indicators_page(s, t, lang, idx, total) -> Page:
    pg = Page()
    es = lang == "es"
    i, p, f, a = s["inflation"], s["policy"], s["fx"], s.get("activity")
    y = masthead(pg, s, lang, full=False)
    y = pg.para(M, y, "Indicadores clave" if es else "Key indicators", size=58, color=INK, weight="semibold",
                family=SERIF_D, lh=1.1)
    y = pg.para(M, y + 12, (f"Últimos datos disponibles al {long_date(s['run_date'], lang)}" if es
                            else f"Latest data available as of {long_date(s['run_date'], lang)}"), size=30, color=MUTED) + 30
    atyp_fx = "¹" if f["signal"] == "atypical" else ""
    unus_ig = "²" if a and a["signal"] in ("unusual", "atypical") else ""
    stance = {"neutral": ("rango neutral", "neutral range"), "restrictive": ("restrictiva", "restrictive"),
              "accommodative": ("acomodaticia", "accommodative")}[p.get("stance", "neutral")][0 if es else 1]
    rows = [
        ("Inflación general" if es else "Headline inflation", f"% anual, {month(i['period'], lang)}" if es else f"% y/y, {month(i['period'], lang)}",
         f"{i['yoy']:.2f}", f"{signed(i['delta_pp'])} pp", i["chart"]),
        ("Inflación subyacente" if es else "Core inflation", f"% anual, {month(i['period'], lang)}" if es else f"% y/y, {month(i['period'], lang)}",
         f"{i.get('core', 0):.2f}", f"{signed(i.get('core_delta_pp'))} pp", i.get("core_chart")),
        ("Tasa objetivo de Banxico" if es else "Banxico target rate", f"%, {day(p['date'], lang, False)}",
         f"{p['rate']:.2f}", f"{signed(p['chg_12m_bp'],0)} {'pb en 12 m' if es else 'bp, 12 m'}", p["chart"]),
        ("Tasa real ex ante" if es else "Ex-ante real rate", f"%, {stance}", f"{p['real_ex_ante']:.2f}",
         f"{signed((p.get('real_ex_ante') or 0) - (p.get('real_ex_ante_12m_ago') or 0))} pp {'en 12 m' if es else '12 m'}",
         p.get("real_chart")),
        ("Tipo de cambio FIX" if es else "USD/MXN FIX", f"{'pesos por dólar' if es else 'pesos per dollar'}, {day(f['date'], lang, False)}",
         f"{f['value']:.2f}{atyp_fx}", f"{signed(f['chg_1w_pct'],1)}% {'semanal' if es else 'w/w'}", f["chart"]),
    ]
    if a:
        rows.append(("IGAE" if es else "IGAE (activity)", f"{'% mensual, a.e.' if es else '% m/m, s.a.'}, {month(a['period'], lang)}",
                     f"{signed(a['mom'],1)}{unus_ig}", f"{signed(a['yoy'],1)}% {'anual' if es else 'y/y'}", a.get("chart")))

    cx = [M, 470, 660, W - M]  # indicator | trend (470-630) | latest (right edge 770) | change (right edge)
    pg.rect(M, y, W - 2 * M, 50, TINT)
    for x_, s_, ha in ((cx[0] + 16, "Indicador" if es else "Indicator", "left"),
                       (cx[1], "Tendencia" if es else "Trend", "left"),
                       (cx[2] + 110, "Último" if es else "Latest", "right"),
                       (cx[3] - 16, "Cambio" if es else "Change", "right")):
        pg.text(x_, y + 12, s_, size=24, color=MUTED, weight="semibold", ha=ha)
    y += 50
    foot = [
        *(["¹ Movimiento atípico: el cambio semanal supera dos desviaciones estándar de los últimos cinco años." if es else
           "¹ Atypical move: the weekly change exceeds two standard deviations of the past five years."] if atyp_fx else []),
        *(["² Variación inusual: supera 1.5 desviaciones estándar de los 60 meses previos." if es else
           "² Unusual change: exceeds 1.5 standard deviations of the previous 60 months."] if unus_ig else []),
        ("a.e.: cifras con ajuste estacional. pp: puntos porcentuales. pb: puntos base. Tendencia: últimos 36 meses "
         "(tipo de cambio: 52 semanas)." if es else
         "s.a.: seasonally adjusted. pp: percentage points. bp: basis points. Trend: last 36 months (FX: 52 weeks)."),
        SOURCE_LINE["dashboard"][lang],
    ]
    foot_h = sum(pg.height(n, 24, W - 2 * M) + 4 for n in foot)
    rh = (H - 112 - foot_h - 30 - y) / len(rows)
    for k, (name, sub, val, chg, payload) in enumerate(rows):
        top = y + k * rh
        pg.text(cx[0] + 16, top + rh / 2 - 22, name, size=32, color=INK, weight="semibold", va="center")
        pg.text(cx[0] + 16, top + rh / 2 + 20, sub, size=24, color=MUTED, va="center")
        trend(pg, payload, cx[1], top + rh * 0.24, 160, rh * 0.52)
        pg.text(cx[2] + 110, top + rh / 2, val, size=42, color=INK, weight="semibold", ha="right", va="center")
        pg.text(cx[3] - 16, top + rh / 2, chg, size=25, color=TEXT, ha="right", va="center")
        pg.hline(top + rh)
    notes_block(pg, H - 112 - foot_h, foot)
    footer(pg, idx, total, lang)
    return pg


# --- page 4: author's note + what to watch ---------------------------------------------------------------
def note_page(s, t, lang, idx, total) -> Page:
    pg = Page()
    es = lang == "es"
    y = masthead(pg, s, lang, full=False)
    note = t.get("note")
    if note:
        y = pg.para(M, y, "Lectura del autor" if es else "Author's view", size=58, color=INK, weight="semibold",
                    family=SERIF_D, lh=1.1) + 30
        y = pg.para(M, y, note["text"], size=38, color=TEXT, family=SERIF, lh=1.42) + 26
        pg.text(M, y, AUTHOR, size=30, color=INK, weight="semibold")
        y = pg.para(M, y + 40, ("Opinión personal del autor; no representa la postura de ninguna institución." if es else
                                "Personal view of the author; it does not represent any institution."), size=24,
                    color=MUTED, style="italic") + 50
        pg.hline(y, color=INK, lw=1.2)
        y += 40
    head = "Qué vigilar esta semana" if es else "What to watch this week"
    y = pg.para(M, y, head, size=44 if note else 58, color=INK, weight="semibold", family=SERIF_D, lh=1.1) + 24
    for r in t["agenda"][:4 if note else 6]:
        pg.text(M, y, r["day"], size=32, color=INK, weight="semibold")
        yy = pg.para(M + 220, y, r["what"] + (f" ({r['src']})" if r["src"] not in r["what"] else ""), size=32,
                     color=TEXT, maxw=W - 2 * M - 220, lh=1.25)
        if r["prev"]:
            yy = pg.para(M + 220, yy + 2, r["prev"].capitalize(), size=24, color=MUTED, maxw=W - 2 * M - 220)
        y = yy + 26
        if y > H - 200:
            break
    notes_block(pg, H - 150, ["Hora del centro de México según los calendarios oficiales de INEGI, Banxico y la Fed." if es
                              else "Mexico City time, per the official INEGI, Banxico and Fed calendars."])
    footer(pg, idx, total, lang)
    return pg


# --- page 5: methodology, glossary, references ----------------------------------------------------
def refs_page(s, t, lang, idx, total) -> Page:
    pg = Page()
    es = lang == "es"
    y = masthead(pg, s, lang, full=False)
    y = pg.para(M, y, "Notas y referencias" if es else "Notes and references", size=58, color=INK, weight="semibold",
                family=SERIF_D, lh=1.1) + 26
    pg.text(M, y, "Metodología" if es else "Methodology", size=30, color=INK, weight="semibold")
    y += 46
    meth = ([
        "Todas las cifras provienen de fuentes oficiales: Banxico (SIE), INEGI (BIE) y la Reserva Federal (FRED).",
        "La tasa real ex ante es la tasa objetivo menos la media de las expectativas de inflación a 12 meses de la encuesta de Banxico.",
        "Un movimiento se considera inusual si supera 1.5 desviaciones estándar de su historia reciente y atípico si supera 2.",
    ] if es else [
        "All figures come from official sources: Banxico (SIE), INEGI (BIE) and the Federal Reserve (FRED).",
        "The ex-ante real rate is the policy rate minus the mean 12-month inflation expectation from Banxico's survey.",
        "A move is unusual above 1.5 standard deviations of its recent history and atypical above 2.",
    ])
    for m_ in meth:
        y = pg.para(M, y, m_, size=27, color=TEXT, lh=1.34) + 10
    y += 26
    pg.text(M, y, "Referencias" if es else "References", size=30, color=INK, weight="semibold")
    y += 46
    used: List[str] = []
    for k in t["order"][:2] + ["policy"]:
        for r in {"fx": ["capistran", "angeles"], "activity": ["heath"], "inflation": [],
                  "policy": ["banxico_neutral", "fama"]}.get(k, []):
            if r not in used:
                used.append(r)
    for r in used[:5]:
        y = pg.para(M + 30, y, REFERENCES[r]["full"], size=25, color=TEXT, maxw=W - 2 * M - 30, lh=1.3) + 14
        # hanging indent marker
        pg.rect(M, y - 14 - pg.height(REFERENCES[r]["full"], 25, W - 2 * M - 30, lh=1.3) + 14, 8, 2, MUTED)
    y = max(y + 20, H - 260)
    pg.hline(y, color=INK, lw=1.2)
    pg.para(M, y + 26, ("MX Macro Monitor se publica cada lunes. Datos, código y metodología: " if es else
                        "MX Macro Monitor is published every Monday. Data, code and methodology: ") + REPO_URL,
            size=28, color=INK, lh=1.3)
    footer(pg, idx, total, lang)
    return pg


# --- render -------------------------------------------------------------------------------------------------
def render(s: dict, t: dict, lang: str, out_dir: Path) -> dict:
    tl = t[lang]
    order = [k for k in tl["order"] if k in tl["ed"]]
    total = 5
    pages = [chart_page(s, tl, order[0], lang, 1, total, 1, first=True),
             indicators_page(s, tl, lang, 2, total),
             chart_page(s, tl, order[1], lang, 3, total, 2, first=False),
             note_page(s, tl, lang, 4, total),
             refs_page(s, tl, lang, 5, total)]
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = out_dir / f"carousel_{lang}.pdf"
    png_dir = out_dir / f"slides_{lang}"
    png_dir.mkdir(exist_ok=True)
    for old in png_dir.glob("*.png"):
        old.unlink()
    meta = {"Title": f"MX Macro Monitor · {tl['headline']}", "Author": AUTHOR,
            "Subject": ("Boletín semanal de coyuntura económica de México" if lang == "es" else "Weekly bulletin on Mexico's economy")}
    with PdfPages(pdf_path, metadata=meta) as pdf:
        for k, pg in enumerate(pages, 1):
            pdf.savefig(pg.fig, facecolor=BG)
            pg.fig.savefig(png_dir / f"{k:02d}.png", dpi=100, facecolor=BG)
            plt.close(pg.fig)
    return {"pdf": pdf_path, "png_dir": png_dir, "n": len(pages)}

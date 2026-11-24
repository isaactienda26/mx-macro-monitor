"""
LinkedIn carousel renderer, v3 (design system "MX Macro Monitor").

5 slides at 1080x1350 (4:5), one idea per slide, exported as a multi-page PDF
(LinkedIn "document" post) plus PNG previews:

    1 Cover        one hero number + headline + sparkline
    2 Lead topic   chart + one reading + why it matters + short reference
    3 Dashboard    six indicators with sparklines
    4 Second topic (same template as 2)
    5 Close        agenda + references + call to follow

Layout works in a 1080x1350 "px" space (origin top-left). Font sizes are px of
that space (1 px = 0.72 pt). LinkedIn shows documents ~390 px wide on phones
(scale ~0.36), so no text is smaller than 21 px. Tokens live in
DESIGN_SYSTEM.md; keep both in sync.
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
from matplotlib.patches import FancyBboxPatch, Rectangle  # noqa: E402

from config import AUTHOR, AUTHOR_ROLE_EN, AUTHOR_ROLE_ES, FONT_DIR, REPO_URL
from narrative import REFERENCES, SIGNAL_LABEL, SOURCE_LINE, day_year, month, signed

W, H = 1080, 1350
M = 80  # outer margin

# --- design tokens (DESIGN_SYSTEM.md) -----------------------------------------
NAVY = "#0B1F33"        # brand: cover background, titles
TEXT = "#1B2533"        # body text
MUTED = "#566070"       # secondary text (≈6:1 on white)
FAINT = "#6B7585"       # axis labels (≈4.8:1 on white)
RULE = "#DCE1E8"        # hairlines
PANEL = "#F3F6FA"       # callout background
BG = "#FFFFFF"
BLUE = "#2A78D6"        # series 1 / brand accent
BLUE_DK = "#1C5CAB"     # highlighted mark (latest point/bar)
BLUE_LT = "#A9CBF3"     # context marks (earlier bars)
ORANGE = "#EB6834"      # series 2 (comparison only)
BAND = "#E6EDF6"        # reference bands (target interval, neutral range)
GOLD = "#F2B84B"        # hero number on the cover (never in charts)
ON_NAVY = "#C9D4E3"     # secondary text on navy
STATUS = {"atypical": ("#B42318", "▲"), "unusual": ("#B54708", "●")}

for f in FONT_DIR.glob("*.ttf"):
    font_manager.fontManager.addfont(str(f))
plt.rcParams.update({"font.family": "Inter", "pdf.fonttype": 42, "axes.unicode_minus": True})
DISPLAY = "Inter Display"
MES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def pt(px: float) -> float:
    return px * 0.72


# --- canvas ----------------------------------------------------------------------
class Slide:
    def __init__(self, bg: str = BG):
        self.fig = plt.figure(figsize=(10.8, 13.5), dpi=100)
        self.fig.patch.set_facecolor(bg)
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, W)
        self.ax.set_ylim(H, 0)
        self.ax.axis("off")
        self.r = self.fig.canvas.get_renderer()

    def text(self, x, y, s, size=30, color=TEXT, weight="regular", family=None, ha="left", va="top", **kw):
        return self.ax.text(x, y, s, fontsize=pt(size), color=color, fontweight=weight, ha=ha, va=va,
                            family=family or "Inter", **kw)

    def width(self, s, size, weight="regular", family=None) -> float:
        t = self.text(0, 0, s, size=size, weight=weight, family=family)
        w = t.get_window_extent(self.r).width / self.fig.dpi * 100
        t.remove()
        return w

    def wrap(self, s, size, maxw, weight="regular", family=None) -> List[str]:
        lines, cur = [], ""
        for word in s.split():
            trial = f"{cur} {word}".strip()
            if not cur or self.width(trial, size, weight, family) <= maxw:
                cur = trial
            else:
                lines.append(cur)
                cur = word
        return lines + ([cur] if cur else [])

    def para(self, x, y, s, size=30, maxw=W - 2 * M, lh=1.32, color=TEXT, weight="regular", family=None,
             max_lines: Optional[int] = None) -> float:
        lines = self.wrap(s, size, maxw, weight, family)
        if max_lines and len(lines) > max_lines:
            lines = lines[:max_lines]
            lines[-1] = lines[-1].rstrip(".,;:") + "…"
        for k, ln in enumerate(lines):
            self.text(x, y + k * size * lh, ln, size=size, color=color, weight=weight, family=family)
        return y + len(lines) * size * lh

    def height(self, s, size, maxw, lh=1.32, weight="regular", family=None) -> float:
        return len(self.wrap(s, size, maxw, weight, family)) * size * lh

    def rect(self, x, y, w, h, color, radius=0):
        p = (FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={radius}", fc=color, ec="none")
             if radius else Rectangle((x, y), w, h, fc=color, ec="none"))
        self.ax.add_patch(p)

    def hline(self, y, x0=M, x1=W - M, color=RULE, lw=1.2):
        self.ax.plot([x0, x1], [y, y], color=color, lw=lw, solid_capstyle="butt")

    def axes(self, x, y, w, h):
        return self.fig.add_axes([x / W, 1 - (y + h) / H, w / W, h / H])


# --- chart helpers (no gridlines, minimal ink) -------------------------------------
def ser(payload) -> pd.Series:
    return pd.Series(payload["values"], index=pd.to_datetime(payload["dates"]))


def clean_axes(ax, pct=False, decimals=None, nticks=3):
    ax.set_facecolor("none")
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(RULE)
    ax.spines["bottom"].set_linewidth(1.2)
    ax.grid(False)
    ax.tick_params(axis="both", colors=FAINT, labelsize=pt(22), length=0, pad=10)
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


def label_point(ax, x, y, s, color, dx=12, dy=0, size=24, weight="bold", ha="left", va="center"):
    ax.annotate(s, (x, y), xytext=(dx, dy), textcoords="offset points", fontsize=pt(size), color=color,
                fontweight=weight, ha=ha, va=va, annotation_clip=False)


# --- chrome ----------------------------------------------------------------------------
def header(sl: Slide, s: dict, idx: int, total: int, lang: str):
    wk = date.fromisoformat(s["run_date"]).isocalendar()[1]
    sl.text(M, 60, f"MX MACRO MONITOR · {'SEMANA' if lang == 'es' else 'WEEK'} {wk}", size=22, color=BLUE, weight="bold")
    sl.text(W - M, 60, f"{idx}/{total}", size=22, color=MUTED, ha="right")


def footer(sl: Slide, lang: str, source: str):
    sl.hline(H - 118)
    sl.para(M, H - 100, source, size=21, color=MUTED, maxw=W - 2 * M - 250, lh=1.3, max_lines=2)
    sl.text(W - M, H - 100, AUTHOR, size=22, color=NAVY, weight="bold", ha="right")
    sl.text(W - M, H - 70, AUTHOR_ROLE_ES if lang == "es" else AUTHOR_ROLE_EN, size=21, color=MUTED, ha="right")


def title_block(sl: Slide, section: str, title: str, kicker: str, y=118) -> float:
    sl.text(M, y, section.upper(), size=22, color=MUTED, weight="semibold")
    y = sl.para(M, y + 40, title, size=58, color=NAVY, weight="bold", family=DISPLAY, lh=1.1, max_lines=2)
    return sl.para(M, y + 12, kicker, size=28, color=MUTED, lh=1.3, max_lines=2)


# --- slide 1: cover ---------------------------------------------------------------------
def slide_cover(s, t, lang, total) -> Slide:
    sl = Slide(bg=NAVY)
    es = lang == "es"
    lead_key = t["order"][0]
    c = t["cards"][lead_key]
    wk = date.fromisoformat(s["run_date"]).isocalendar()[1]
    sl.text(M, 72, "MX MACRO MONITOR", size=26, color="#FFFFFF", weight="bold")
    sl.text(M, 110, (f"Semana {wk} · datos al {day_year(s['run_date'], lang)}" if es
                     else f"Week {wk} · data as of {day_year(s['run_date'], lang)}"), size=22, color=ON_NAVY)
    sl.text(M, 228, c["hero_label"], size=28, color=ON_NAVY, weight="medium")
    sl.text(M - 6, 268, c["hero"], size=210, color=GOLD, weight="bold", family=DISPLAY)
    y = sl.para(M, 530, c["cover_line"], size=60, color="#FFFFFF", weight="bold", family=DISPLAY, lh=1.1, max_lines=3)
    sl.para(M, y + 16, c["cover_sub"], size=30, color=ON_NAVY, lh=1.3, max_lines=2)

    # sparkline of the lead series (no axes): context, not data reading
    payload = {"fx": s["fx"]["chart"], "inflation": s["inflation"]["chart"], "policy": s["policy"].get("real_chart"),
               "activity": (s.get("activity") or {}).get("chart")}.get(lead_key)
    if payload:
        x = ser(payload)
        rng = (x.max() - x.min()) or 1
        ax = sl.axes(M, 900, W - 2 * M - 140, 190)
        ax.axis("off")
        ax.fill_between(x.index, x.values, x.min() - rng * 0.15, color="#FFFFFF", alpha=0.06, lw=0)
        ax.plot(x.index, x.values, color="#FFFFFF", lw=3, alpha=0.9, solid_capstyle="round")
        ax.scatter([x.index[-1]], [x.iloc[-1]], s=110, color=GOLD, zorder=5, edgecolor=NAVY, linewidth=2.5)
        ax.set_ylim(x.min() - rng * 0.15, x.max() + rng * 0.1)
        span = {"fx": ("Tipo de cambio FIX, últimas 52 semanas", "USD/MXN FIX, last 52 weeks"),
                "inflation": ("Inflación anual, últimos 36 meses", "Annual inflation, last 36 months"),
                "policy": ("Tasa real ex ante, últimos 36 meses", "Ex-ante real rate, last 36 months"),
                "activity": ("IGAE desestacionalizado, últimos 36 meses", "Seasonally adjusted IGAE, last 36 months")}[lead_key]
        sl.text(M, 1105, span[0 if es else 1], size=22, color=ON_NAVY)
    sl.text(M, H - 92, f"{AUTHOR} · {AUTHOR_ROLE_ES if es else AUTHOR_ROLE_EN}", size=24, color="#FFFFFF", weight="bold")
    sl.text(M, H - 58, "Fuentes: Banxico, INEGI, Reserva Federal" if es else "Sources: Banxico, INEGI, Federal Reserve",
            size=21, color=ON_NAVY)
    sl.text(W - M, H - 92, "Desliza →" if es else "Swipe →", size=28, color="#FFFFFF", weight="bold", ha="right")
    return sl


# --- topic charts -----------------------------------------------------------------------------
def draw_fx(ax, s, lang):
    f = s["fx"]
    x = ser(f["chart"])
    ax.plot(x.index, x.values, color=BLUE, lw=3, solid_capstyle="round")
    ax.scatter([x.index[-1]], [x.iloc[-1]], s=90, color=BLUE_DK, zorder=5, edgecolor="white", linewidth=2)
    label_point(ax, x.index[-1], x.iloc[-1], f"{x.iloc[-1]:.2f}", NAVY)
    lo_d = pd.Timestamp(f["low_52w_date"])
    if lo_d != x.index[-1]:
        ax.scatter([lo_d], [f["low_52w"]], s=60, color=MUTED, zorder=5)
        label_point(ax, lo_d, f["low_52w"], ("mín. " if lang == "es" else "low ") + f"{f['low_52w']:.2f}",
                    MUTED, dx=0, dy=-22, size=22, weight="medium", ha="center", va="top")
    clean_axes(ax, decimals=1)
    month_ticks(ax, lang, every=3)
    pad = (x.max() - x.min()) * 0.18
    ax.set_ylim(x.min() - pad, x.max() + pad * 0.6)


def draw_activity(ax, s, lang):
    a = s["activity"]
    lvl = ser(a["chart"])
    mom = (lvl.pct_change() * 100).dropna().tail(24)
    colors = [BLUE_LT] * (len(mom) - 1) + [BLUE_DK]
    ax.bar(mom.index, mom.values, width=20, color=colors, edgecolor="white", linewidth=2)
    ax.axhline(0, color=NAVY, lw=1.2)
    v = mom.iloc[-1]
    label_point(ax, mom.index[-1], v, f"{v:+.1f}%".replace("-", "−"), NAVY, dx=0,
                dy=-12 if v < 0 else 10, ha="center", va="top" if v < 0 else "bottom")
    clean_axes(ax, pct=True)
    ax.spines["bottom"].set_visible(False)
    month_ticks(ax, lang, every=6)
    m = max(abs(mom.min()), abs(mom.max())) * 1.3
    ax.set_ylim(-m, m)


def draw_inflation(ax, s, lang):
    i = s["inflation"]
    g = ser(i["chart"])
    ax.axhspan(i["band"][0], i["band"][1], color=BAND, lw=0, zorder=0)
    ax.axhline(i["target"], color=FAINT, lw=1.4, ls=(0, (5, 4)), zorder=1)
    ax.text(g.index[0], i["target"], ("  meta 3%" if lang == "es" else "  3% target"), color=MUTED,
            fontsize=pt(22), va="bottom", ha="left")
    ax.plot(g.index, g.values, color=BLUE, lw=3, solid_capstyle="round", zorder=3)
    if i.get("core_chart"):
        c = ser(i["core_chart"])
        ax.plot(c.index, c.values, color=ORANGE, lw=3, solid_capstyle="round", zorder=3)
        up = c.iloc[-1] >= g.iloc[-1]
        label_point(ax, c.index[-1], c.iloc[-1], f"{c.iloc[-1]:.2f}%", NAVY, dy=14 if up else -14)
        label_point(ax, g.index[-1], g.iloc[-1], f"{g.iloc[-1]:.2f}%", NAVY, dy=-14 if up else 14)
        lo = min(g.min(), c.min(), i["band"][0]) - 0.3
        hi = max(g.max(), c.max(), i["band"][1]) + 0.3
    else:
        label_point(ax, g.index[-1], g.iloc[-1], f"{g.iloc[-1]:.2f}%", NAVY)
        lo, hi = min(g.min(), i["band"][0]) - 0.3, max(g.max(), i["band"][1]) + 0.3
    clean_axes(ax, pct=True)
    month_ticks(ax, lang, every=6)
    ax.set_ylim(lo, hi)


def draw_policy(ax, s, lang):
    p = s["policy"]
    r = ser(p["real_chart"])
    lo, hi = p.get("neutral_range", [1.8, 3.6])
    ax.axhspan(lo, hi, color=BAND, lw=0, zorder=0)
    ax.text(r.index[0], hi, ("  rango neutral (Banxico)" if lang == "es" else "  neutral range (Banxico)"),
            color=MUTED, fontsize=pt(22), va="top", ha="left")
    ax.plot(r.index, r.values, color=BLUE, lw=3, solid_capstyle="round", zorder=3)
    cur = p["real_ex_ante"]
    ax.scatter([r.index[-1]], [cur], s=90, color=BLUE_DK, zorder=5, edgecolor="white", linewidth=2)
    label_point(ax, r.index[-1], cur, f"{cur:.2f}%", NAVY)
    clean_axes(ax, pct=True)
    month_ticks(ax, lang, every=6)
    ax.set_ylim(min(r.min(), lo) - 0.6, max(r.max(), hi) + 0.6)


DRAW = {"fx": draw_fx, "activity": draw_activity, "inflation": draw_inflation, "policy": draw_policy}
SECTION = {"fx": ("Tipo de cambio", "Exchange rate"), "activity": ("Actividad económica", "Economic activity"),
           "inflation": ("Inflación", "Inflation"), "policy": ("Política monetaria", "Monetary policy")}
LEGEND = {
    "inflation": [(("General", "Headline"), BLUE, "line"), (("Subyacente", "Core"), ORANGE, "line"),
                  (("Intervalo 2%–4%", "2%–4% band"), BAND, "band")],
    "policy": [(("Tasa objetivo − expectativa de inflación 12m (media)",
                 "Policy rate − 12m inflation expectation (mean)"), BLUE, "line")],
    "fx": [(("Pesos por dólar (alza = peso más débil)", "MXN per USD (up = weaker peso)"), BLUE, "line")],
    "activity": [(("Variación mensual, % (desestacionalizada)", "Monthly change, % (seasonally adjusted)"), BLUE_LT, "bar")],
}


def slide_topic(s, t, key, lang, idx, total) -> Slide:
    sl = Slide()
    es = lang == "es"
    c = t["cards"][key]
    header(sl, s, idx, total, lang)
    y = title_block(sl, SECTION[key][0 if es else 1], c["title"], c["kicker"])

    # legend row (≥2 series: always; 1 series: names the unit)
    y += 26
    x = M
    for (lab, col, kind) in LEGEND[key]:
        name = lab[0 if es else 1]
        if kind == "band":
            sl.rect(x, y + 6, 34, 20, col)
        elif kind == "bar":
            sl.rect(x + 8, y + 2, 18, 26, col)
        else:
            sl.ax.plot([x, x + 34], [y + 16, y + 16], color=col, lw=4, solid_capstyle="round")
        sl.text(x + 46, y, name, size=22, color=TEXT)
        x += 46 + sl.width(name, 22) + 36
    y += 44

    # bottom-up: measure text first so the chart takes the remaining height
    tw = W - 2 * M
    read_h = sl.height(c["read"], 32, tw, lh=1.3, weight="medium")
    why_h = sl.height(c["why"], 27, tw - 64, lh=1.32) + sl.height(c["ref_line"], 22, tw - 64, lh=1.3) + 64
    bottom = H - 140
    text_top = bottom - why_h - 28 - read_h
    ch = max(300, text_top - 60 - y)
    ax = sl.axes(M + 56, y + 10, W - 2 * M - 56 - 120, ch - 10)
    DRAW[key](ax, s, lang)

    yy = sl.para(M, text_top, c["read"], size=32, color=NAVY, weight="medium", lh=1.3)
    yy += 28
    sl.rect(M, yy, tw, why_h, PANEL, radius=12)
    sl.rect(M, yy, 6, why_h, BLUE)
    y2 = sl.para(M + 34, yy + 28, c["why"], size=27, color=TEXT, maxw=tw - 64, lh=1.32)
    sl.para(M + 34, y2 + 8, c["ref_line"], size=22, color=MUTED, maxw=tw - 64, lh=1.3)
    footer(sl, lang, c["source"])
    return sl


# --- slide 3: dashboard -----------------------------------------------------------------------
def spark(sl: Slide, payload, x, y, w, h, color=BLUE):
    if not payload:
        return
    v = ser(payload)
    ax = sl.axes(x, y, w, h)
    ax.axis("off")
    ax.plot(v.index, v.values, color=color, lw=2.6, solid_capstyle="round")
    ax.scatter([v.index[-1]], [v.iloc[-1]], s=40, color=BLUE_DK, zorder=5)
    rng = (v.max() - v.min()) or 1
    ax.set_ylim(v.min() - rng * 0.15, v.max() + rng * 0.15)


def slide_dashboard(s, t, lang, idx, total) -> Slide:
    sl = Slide()
    es = lang == "es"
    i, p, f, a = s["inflation"], s["policy"], s["fx"], s.get("activity")
    header(sl, s, idx, total, lang)
    y = title_block(sl, "Tablero" if es else "Dashboard", "Seis indicadores en una vista" if es else "Six indicators at a glance",
                    "Último dato, cambio y tendencia" if es else "Latest value, change and trend")
    prev_m = MES[(int(i["period"][5:7]) - 2) % 12]
    stance = ({"neutral": "postura neutral", "restrictive": "postura restrictiva", "accommodative": "postura acomodaticia"} if es
              else {"neutral": "neutral stance", "restrictive": "restrictive stance", "accommodative": "accommodative stance"})
    rows = [
        ("Inflación general" if es else "Headline inflation", month(i["period"], lang), f"{i['yoy']:.2f}%",
         f"{signed(i['delta_pp'])} pp" + (f" vs. {prev_m}" if es else " m/m"), i["chart"], i["signal"]),
        ("Inflación subyacente" if es else "Core inflation", month(i["period"], lang), f"{i.get('core', 0):.2f}%",
         f"{signed(i.get('core_delta_pp'))} pp" + (f" vs. {prev_m}" if es else " m/m"), i.get("core_chart"), "na"),
        ("Tasa objetivo Banxico" if es else "Banxico policy rate", day_year(p["date"], lang), f"{p['rate']:.2f}%",
         f"{signed(p['chg_12m_bp'],0)} {'pb' if es else 'bp'} en 12m" if es else f"{signed(p['chg_12m_bp'],0)} bp over 12m",
         p["chart"], "na"),
        ("Tasa real ex ante" if es else "Ex-ante real rate", ("rango neutral 1.8%–3.6%" if es else "neutral range 1.8%–3.6%"),
         f"{p['real_ex_ante']:.2f}%", stance[p.get("stance", "neutral")], p.get("real_chart"), "na"),
        ("Tipo de cambio FIX" if es else "USD/MXN FIX", day_year(f["date"], lang), f"{f['value']:.2f}",
         f"{signed(f['chg_1w_pct'],1)}% {'semanal' if es else 'w/w'}", f["chart"], f["signal"]),
    ]
    if a:
        rows.append(("IGAE, var. mensual" if es else "IGAE, m/m change", month(a["period"], lang) + (" · a.e." if es else " · s.a."),
                     f"{signed(a['mom'],1)}%", f"{signed(a['yoy'],1)}% {'anual' if es else 'y/y'}", a.get("chart"), a["signal"]))
    y += 30
    sl.hline(y, color=NAVY, lw=1.6)
    rh = (H - 150 - y) / len(rows)
    for name, sub, val, chg, payload, sig in rows:
        sl.text(M, y + 24, name, size=28, color=NAVY, weight="semibold")
        sl.text(M, y + 62, sub, size=22, color=MUTED)
        if sig in STATUS:
            col, icon = STATUS[sig]
            sl.text(M, y + 94, f"{icon} {SIGNAL_LABEL[lang][sig]}", size=22, color=col, weight="bold")
        spark(sl, payload, 500, y + 26, 190, rh - 52)
        sl.text(W - M, y + 22, val, size=44, color=NAVY, weight="bold", family=DISPLAY, ha="right")
        sl.text(W - M, y + 80, chg, size=22, color=MUTED, ha="right")
        y += rh
        sl.hline(y)
    footer(sl, lang, SOURCE_LINE["dashboard"][lang])
    return sl


# --- slide 5: close ------------------------------------------------------------------------------
def slide_close(s, t, lang, idx, total) -> Slide:
    sl = Slide()
    es = lang == "es"
    header(sl, s, idx, total, lang)
    sl.text(M, 118, "QUÉ SIGUE" if es else "WHAT'S NEXT", size=22, color=MUTED, weight="semibold")
    y = 162
    for r in t["agenda"][:3]:
        sl.text(M, y, r["day"], size=28, color=NAVY, weight="bold")
        yy = sl.para(M + 230, y, r["what"], size=28, color=TEXT, maxw=W - 2 * M - 230, lh=1.25)
        if r["prev"]:
            yy = sl.para(M + 230, yy + 2, r["prev"], size=22, color=MUTED, maxw=W - 2 * M - 230)
        y = yy + 22
        sl.hline(y - 10)
    y += 34
    sl.text(M, y, "CÓMO SE LEE" if es else "HOW TO READ IT", size=22, color=MUTED, weight="semibold")
    y = sl.para(M, y + 42, ("Señal estadística: puntaje z del último cambio frente a los 60 meses previos (tipo de cambio: "
                            "260 semanas), sin incluir el propio dato. Inusual ≥ 1.5σ; atípico ≥ 2σ. Tasa real ex ante: "
                            "tasa objetivo menos la media de las expectativas de inflación a 12 meses." if es else
                            "Statistical signal: z-score of the latest change vs. the prior 60 months (FX: 260 weeks), "
                            "excluding the latest point. Unusual ≥ 1.5σ; atypical ≥ 2σ. Ex-ante real rate: policy rate "
                            "minus the mean 12-month inflation expectation."), size=22, color=TEXT, lh=1.32)
    y += 30
    sl.text(M, y, "REFERENCIAS" if es else "REFERENCES", size=22, color=MUTED, weight="semibold")
    y += 44
    # only works cited on the slides shown (topics 1-2) + Banxico (2024) for the neutral range in the dashboard
    used: List[str] = []
    for k in [k for k in t["order"] if k in t["cards"]][:2] + ["policy"]:
        for r in t["cards"].get(k, {}).get("refs", []):
            if r not in used and r != "banxico_survey" and (k != "policy" or r == "banxico_neutral" or k in t["order"][:2]):
                used.append(r)
    for n_, r in enumerate(used[:6], 1):
        txt = REFERENCES[r]["full"]
        sl.text(M, y, f"{n_}.", size=21, color=MUTED)
        y = sl.para(M + 36, y, txt, size=21, color=TEXT, maxw=W - 2 * M - 36, lh=1.3) + 12
    head = ("Cada lunes, el pulso macro de México con datos oficiales." if es
            else "Every Monday: Mexico's macro pulse from official data.")
    follow = "Sígueme para la próxima edición." if es else "Follow for the next edition."
    iw = W - 2 * M - 72
    box_h = 30 + sl.height(head, 32, iw, lh=1.15, weight="bold", family=DISPLAY) + 16 + 2 * 22 * 1.35 + 28
    y = max(y + 18, H - 150 - box_h)
    sl.rect(M, y, W - 2 * M, box_h, NAVY, radius=14)
    yy = sl.para(M + 36, y + 30, head, size=32, color="#FFFFFF", weight="bold", family=DISPLAY, maxw=iw, lh=1.15)
    sl.text(M + 36, yy + 16, follow, size=22, color="#FFFFFF", weight="semibold")
    sl.text(M + 36, yy + 16 + 22 * 1.35, REPO_URL, size=22, color=ON_NAVY)
    footer(sl, lang, "Agenda: calendarios oficiales de INEGI, Banxico y la Fed; hora del centro de México." if es
           else "Agenda: official INEGI, Banxico and Fed calendars; Mexico City time.")
    return sl


# --- render -----------------------------------------------------------------------------------
def render(s: dict, t: dict, lang: str, out_dir: Path) -> dict:
    tl = t[lang]
    order = [k for k in tl["order"] if k in tl["cards"]]
    total = 5
    slides = [slide_cover(s, tl, lang, total),
              slide_topic(s, tl, order[0], lang, 2, total),
              slide_dashboard(s, tl, lang, 3, total),
              slide_topic(s, tl, order[1], lang, 4, total),
              slide_close(s, tl, lang, 5, total)]
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = out_dir / f"carousel_{lang}.pdf"
    png_dir = out_dir / f"slides_{lang}"
    png_dir.mkdir(exist_ok=True)
    for old in png_dir.glob("*.png"):
        old.unlink()
    with PdfPages(pdf_path, metadata={"Title": f"MX Macro Monitor {s['run_date']}", "Author": AUTHOR}) as pdf:
        for k, sl in enumerate(slides, 1):
            pdf.savefig(sl.fig, facecolor=sl.fig.get_facecolor())
            sl.fig.savefig(png_dir / f"{k:02d}.png", dpi=100, facecolor=sl.fig.get_facecolor())
            plt.close(sl.fig)
    return {"pdf": pdf_path, "png_dir": png_dir, "n": len(slides)}

"""
LinkedIn carousel renderer: 7 slides at 1080x1350 (4:5), exported as a multi-page
PDF (the format LinkedIn's "document" post expects) plus PNG previews.

Layout works in a 1080x1350 "px" coordinate space (origin top-left). Font sizes
are given in px of that space and converted to points (1 px = 0.72 pt).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import List, Optional

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle  # noqa: E402

from config import AUTHOR, AUTHOR_ROLE_EN, AUTHOR_ROLE_ES, FONT_DIR, REPO_URL
from narrative import SIGNAL_LABEL, day_year, month, n, signed

W, H = 1080, 1350
M = 72  # outer margin

# --- palette (validated with the dataviz skill's validator; see README) ------
INK = "#0F2537"        # navy: titles, cover background
TEXT = "#1E293B"
MUTED = "#5B6472"
RULE = "#D5DAE1"
TINT = "#F2F5F9"       # panels
BG = "#FFFFFF"
S1 = "#2A78D6"         # series 1 (blue)
S2 = "#EB6834"         # series 2 (orange)
BAND = "#E6ECF3"       # reference band
ACCENT_LIGHT = "#86B6EF"
STATUS = {"atypical": ("#B42318", "▲"), "unusual": ("#B54708", "●"), "normal": ("#5B6472", "–"), "na": ("#5B6472", "–")}

for f in FONT_DIR.glob("*.ttf"):
    font_manager.fontManager.addfont(str(f))
plt.rcParams.update({
    "font.family": "Inter", "pdf.fonttype": 42, "axes.unicode_minus": True,
    "svg.fonttype": "none",
})
DISPLAY = "Inter Display"


def pt(px: float) -> float:
    return px * 0.72


class Slide:
    def __init__(self, bg: str = BG):
        self.fig = plt.figure(figsize=(10.8, 13.5), dpi=100)
        self.fig.patch.set_facecolor(bg)
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, W)
        self.ax.set_ylim(H, 0)
        self.ax.axis("off")
        self.renderer = self.fig.canvas.get_renderer()

    # text helpers -------------------------------------------------------------
    def text(self, x, y, s, size=26, color=TEXT, weight="regular", family=None, ha="left", va="top", **kw):
        return self.ax.text(x, y, s, fontsize=pt(size), color=color, fontweight=weight, ha=ha, va=va,
                            family=family or "Inter", **kw)

    def width(self, s, size, weight="regular", family=None) -> float:
        t = self.text(0, 0, s, size=size, weight=weight, family=family)
        w = t.get_window_extent(self.renderer).width / self.fig.dpi * 100
        t.remove()
        return w

    def wrap(self, s: str, size: float, maxw: float, weight="regular", family=None) -> List[str]:
        lines, cur = [], ""
        for word in s.split():
            trial = f"{cur} {word}".strip()
            if self.width(trial, size, weight, family) <= maxw or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
        return lines

    def para(self, x, y, s, size=26, maxw=W - 2 * M, lh=1.38, color=TEXT, weight="regular", family=None,
             max_lines: Optional[int] = None) -> float:
        lines = self.wrap(s, size, maxw, weight, family)
        if max_lines and len(lines) > max_lines:
            lines = lines[:max_lines]
            lines[-1] = lines[-1].rstrip(".,;") + "…"
        for i, ln in enumerate(lines):
            self.text(x, y + i * size * lh, ln, size=size, color=color, weight=weight, family=family)
        return y + len(lines) * size * lh

    def rect(self, x, y, w, h, color, radius=0, **kw):
        if radius:
            p = FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={radius}",
                               facecolor=color, edgecolor="none", **kw)
        else:
            p = Rectangle((x, y), w, h, facecolor=color, edgecolor="none", **kw)
        self.ax.add_patch(p)

    def hline(self, y, x0=M, x1=W - M, color=RULE, lw=1.0):
        self.ax.plot([x0, x1], [y, y], color=color, lw=lw, solid_capstyle="butt")

    def chart_axes(self, x, y, w, h):
        """Axes placed in px (top-left origin)."""
        return self.fig.add_axes([x / W, 1 - (y + h) / H, w / W, h / H])


# --- shared chrome ---------------------------------------------------------------
def chrome(sl: Slide, idx: int, total: int, lang: str, source: str):
    sl.text(M, 56, "MX MACRO MONITOR", size=20, color=S1, weight="bold")
    sl.text(W - M, 56, f"{idx} / {total}", size=20, color=MUTED, ha="right")
    sl.hline(H - 104)
    sl.para(M, H - 86, source, size=17, color=MUTED, maxw=W - 2 * M - 300, lh=1.3)
    role = AUTHOR_ROLE_ES if lang == "es" else AUTHOR_ROLE_EN
    sl.text(W - M, H - 86, AUTHOR, size=20, color=INK, weight="bold", ha="right")
    sl.text(W - M, H - 58, role, size=17, color=MUTED, ha="right")


def title_block(sl: Slide, kicker: str, title: str, y: float = 112) -> float:
    sl.text(M, y, kicker.upper(), size=19, color=MUTED, weight="semibold")
    return sl.para(M, y + 38, title, size=50, color=INK, weight="bold", family=DISPLAY, lh=1.12, max_lines=3)


def bullets_height(sl: Slide, bullets: List[str], why: str, size: float = 25) -> float:
    h = sum(len(sl.wrap(b, size, W - 2 * M - 26)) * size * 1.36 + 14 for b in bullets) + 6
    return h + len(sl.wrap(why, 23, W - 2 * M - 56, "medium")) * 23 * 1.38 + 40


def bullets_block(sl: Slide, bullets: List[str], why: str, y: float, size: float = 25) -> float:
    for b in bullets:
        sl.rect(M, y + 11, 8, 8, S1, radius=1)
        y = sl.para(M + 26, y, b, size=size, maxw=W - 2 * M - 26, lh=1.36) + 14
    y += 6
    lines = sl.wrap(why, 23, W - 2 * M - 56, "medium")
    h = len(lines) * 23 * 1.38 + 40
    sl.rect(M, y, W - 2 * M, h, TINT, radius=10)
    sl.rect(M, y, 6, h, S1)
    for i, ln in enumerate(lines):
        sl.text(M + 32, y + 20 + i * 23 * 1.38, ln, size=23, color=INK, weight="medium")
    return y + h


def style_axes(ax, ypct=False):
    ax.set_facecolor(BG)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(RULE)
    ax.tick_params(axis="both", colors=MUTED, labelsize=pt(18), length=0, pad=8)
    ax.grid(axis="y", color=RULE, lw=0.8, alpha=0.7)
    ax.set_axisbelow(True)
    if ypct:
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: (f"{v:.0f}%" if v == int(v) else f"{v:.1f}%").replace("-", "−")))


def month_axis(ax, lang, every=6):
    mes = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"] if lang == "es" else \
          ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=every))
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(
        lambda v, _: f"{mes[mdates.num2date(v).month-1]}\n{mdates.num2date(v).year}"))


def end_label(ax, x, y, s, color, dy=0, size=20, weight="bold"):
    ax.annotate(s, (x, y), xytext=(10, dy), textcoords="offset points", fontsize=pt(size), color=color,
                fontweight=weight, va="center", ha="left", annotation_clip=False)


def ser(payload) -> pd.Series:
    return pd.Series(payload["values"], index=pd.to_datetime(payload["dates"]))


# --- slides -----------------------------------------------------------------------
def slide_cover(s, t, lang, total) -> Slide:
    sl = Slide(bg=INK)
    run = date.fromisoformat(s["run_date"])
    wk = run.isocalendar()[1]
    sl.text(M, 64, "MX MACRO MONITOR", size=24, color="#FFFFFF", weight="bold")
    sl.text(M, 100, (f"Semana {wk} · {run.year}" if lang == "es" else f"Week {wk} · {run.year}").upper(),
            size=20, color=ACCENT_LIGHT, weight="semibold")
    sl.rect(M, 150, 96, 6, S1)
    y = sl.para(M, 196, t["headline"], size=66, color="#FFFFFF", weight="bold", family=DISPLAY, lh=1.1, max_lines=4)
    sub = t["subhead"][0].lower() + t["subhead"][1:] if lang == "es" else t["subhead"]
    y = sl.para(M, y + 22, ("También: " if lang == "es" else "Also: ") + sub, size=28, color="#C9D4E3", lh=1.3, max_lines=2)

    i, p, f, a = s["inflation"], s["policy"], s["fx"], s.get("activity")
    tiles = {
        "fx": ("Tipo de cambio FIX" if lang == "es" else "USD/MXN FIX", n(f["value"], 2),
               f"{signed(f['chg_1w_pct'])}% " + ("semanal" if lang == "es" else "w/w")),
        "inflation": ("Inflación anual" if lang == "es" else "Inflation (y/y)", f"{n(i['yoy'])}%",
                      f"{signed(i['delta_pp'])} pp · {month(i['period'], lang)}"),
        "policy": ("Tasa Banxico" if lang == "es" else "Banxico rate", f"{n(p['rate'])}%",
                   (f"real ex ante {n(p.get('real_ex_ante'))}%" if lang == "es" else f"ex-ante real {n(p.get('real_ex_ante'))}%")),
    }
    if a:
        tiles["activity"] = ("IGAE (var. mensual)" if lang == "es" else "IGAE (m/m)", f"{signed(a['mom'],1)}%",
                             f"{signed(a['yoy'],1)}% " + ("anual" if lang == "es" else "y/y") + f" · {month(a['period'], lang)}")
    tiles = [tiles[k] for k in t["order"] if k in tiles]
    top = max(y + 48, 700)
    tw, th, gap = (W - 2 * M - 24) / 2, 190, 24
    for k, (lab, val, sub) in enumerate(tiles[:4]):
        x0 = M + (k % 2) * (tw + gap)
        y0 = top + (k // 2) * (th + gap)
        sl.rect(x0, y0, tw, th, "#17314A", radius=14)
        sl.text(x0 + 28, y0 + 26, lab, size=21, color="#C9D4E3", weight="medium")
        sl.text(x0 + 28, y0 + 62, val, size=62, color="#FFFFFF", weight="bold", family=DISPLAY)
        sl.text(x0 + 28, y0 + 146, sub, size=19, color=ACCENT_LIGHT)
    sl.text(M, H - 96, (f"Datos al {day_year(s['run_date'], lang)} · Banxico · INEGI · Fed" if lang == "es"
                        else f"Data as of {day_year(s['run_date'], lang)} · Banxico · INEGI · Fed"), size=19, color="#C9D4E3")
    sl.text(M, H - 64, f"{AUTHOR} · {AUTHOR_ROLE_ES if lang == 'es' else AUTHOR_ROLE_EN}", size=21, color="#FFFFFF", weight="bold")
    sl.text(W - M, H - 64, ("Desliza  →" if lang == "es" else "Swipe  →"), size=24, color="#FFFFFF", weight="bold", ha="right")
    return sl


def slide_dashboard(s, t, lang, idx, total) -> Slide:
    sl = Slide()
    i, e, p, f, a = s["inflation"], s.get("expectations") or {}, s["policy"], s["fx"], s.get("activity")
    es = lang == "es"
    prev_lbl = "m/m"
    if es:
        pm = (int(i["period"][5:7]) - 2) % 12
        prev_lbl = "vs. " + ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"][pm]
    y = title_block(sl, "Tablero" if es else "Dashboard",
                    "Los 8 indicadores de la semana" if es else "This week's 8 indicators")
    rows = [
        ("Inflación general" if es else "Headline inflation", "% anual" if es else "% y/y", f"{n(i['yoy'])}",
         f"{signed(i['delta_pp'])} pp " + prev_lbl, month(i["period"], lang), i["signal"]),
        ("Inflación subyacente" if es else "Core inflation", "% anual" if es else "% y/y", f"{n(i.get('core'))}",
         f"{signed(i.get('core_delta_pp'))} pp " + prev_lbl, month(i.get("core_period", i["period"]), lang), "na"),
        ("Expectativa de inflación 12m" if es else "12m inflation expectation", "mediana, encuesta Banxico" if es else "median, Banxico survey",
         f"{n(e.get('exp_12m'))}", f"{signed((e.get('exp_12m') or 0) - (e.get('exp_12m_prev') or 0))} pp " + prev_lbl,
         month(e["period"], lang) if e else "N/D", "na"),
        ("Tasa objetivo Banxico" if es else "Banxico policy rate", "%", f"{n(p['rate'])}",
         f"{signed(p.get('chg_12m_bp'),0)} pb " + ("en 12 meses" if es else "over 12m").replace("pb", "pb" if es else "bp"),
         day_year(p["date"], lang), "na"),
        ("Tasa real ex ante" if es else "Ex-ante real rate", "tasa − expectativa 12m" if es else "rate − 12m expectation",
         f"{n(p.get('real_ex_ante'))}",
         (f"{signed((p.get('real_ex_ante') or 0) - (p.get('real_ex_ante_12m_ago') or 0))} pp " + ("en 12 meses" if es else "over 12m"))
         if p.get("real_ex_ante_12m_ago") is not None else "", month(e["period"], lang) if e else "N/D", "na"),
        ("Diferencial Banxico–Fed" if es else "Banxico–Fed spread", "pb, límite superior" if es else "bp, upper bound",
         f"{n(p.get('spread_bp'),0)}",
         (f"{signed((p.get('spread_bp') or 0) - (p.get('spread_12m_ago_bp') or 0),0)} pb " + ("en 12 meses" if es else "over 12m")).replace(" pb", " pb" if es else " bp"),
         day_year(p["date"], lang), "na"),
        ("Tipo de cambio FIX" if es else "USD/MXN FIX", "pesos por dólar" if es else "MXN per USD", f"{n(f['value'],4)}",
         f"{signed(f['chg_1w_pct'])}% " + ("semanal" if es else "w/w"), day_year(f["date"], lang), f["signal"]),
    ]
    if a:
        rows.append(("Actividad económica (IGAE)" if es else "Economic activity (IGAE)", "% mensual, a.e." if es else "% m/m, s.a.",
                     f"{signed(a['mom'],1)}", f"{signed(a['yoy'],1)}% " + ("anual" if es else "y/y"), month(a["period"], lang), a["signal"]))
    y += 34
    cols = [M, 560, 742, W - M]
    sl.text(cols[0], y, "Indicador" if es else "Indicator", size=18, color=MUTED, weight="semibold")
    sl.text(cols[2] - 20, y, "Último" if es else "Latest", size=18, color=MUTED, weight="semibold", ha="right")
    sl.text(cols[2] + 10, y, "Cambio" if es else "Change", size=18, color=MUTED, weight="semibold")
    sl.text(cols[3], y, "Señal" if es else "Signal", size=18, color=MUTED, weight="semibold", ha="right")
    y += 36
    sl.hline(y, color=INK, lw=1.4)
    rh = min(104, (H - 230 - y) / len(rows))
    for name, unit, val, chg, per, sig in rows:
        sl.text(cols[0], y + 18, name, size=24, color=INK, weight="semibold")
        sl.text(cols[0], y + 52, f"{unit} · {per}", size=17, color=MUTED)
        sl.text(cols[2] - 20, y + 22, val, size=36, color=INK, weight="bold", family=DISPLAY, ha="right")
        sl.para(cols[2] + 10, y + 22, chg, size=19, color=TEXT, maxw=200, lh=1.25)
        col, icon = STATUS[sig]
        if sig in ("unusual", "atypical"):
            sl.text(cols[3], y + 26, f"{icon} {SIGNAL_LABEL[lang][sig]}", size=19, color=col, weight="bold", ha="right")
        else:
            sl.text(cols[3], y + 26, "—", size=19, color=MUTED, ha="right")
        y += rh
        sl.hline(y)
    note = ("Señal: puntaje z del último cambio frente a los 60 meses previos (tipo de cambio: 260 semanas). "
            "Inusual ≥ 1.5σ; atípico ≥ 2σ. a.e. = serie desestacionalizada." if es else
            "Signal: z-score of the latest change vs. the prior 60 months (FX: 260 weeks). "
            "Unusual ≥ 1.5σ; atypical ≥ 2σ. s.a. = seasonally adjusted.")
    sl.para(M, y + 18, note, size=17, color=MUTED, lh=1.35)
    chrome(sl, idx, total, lang, "Fuentes: Banxico (SIE), INEGI (BIE), Reserva Federal (FRED)." if es else
           "Sources: Banxico (SIE), INEGI (BIE), Federal Reserve (FRED).")
    return sl


def _chart_slide(s, block, kicker, lang, idx, total, source, draw, legend: Optional[List[tuple]] = None) -> Slide:
    sl = Slide()
    y = title_block(sl, kicker, block["title"])
    y += 18
    if legend:
        x = M
        for lab, col, style in legend:
            if style == "text":
                sl.text(x, y, lab, size=19, color=MUTED)
                x += sl.width(lab, 19) + 34
                continue
            if style == "band":
                sl.rect(x, y + 4, 30, 16, BAND)
            else:
                sl.ax.plot([x, x + 30], [y + 12, y + 12], color=col, lw=3 if style == "solid" else 2,
                           ls="-" if style == "solid" else (0, (4, 3)), solid_capstyle="round")
            sl.text(x + 40, y, lab, size=19, color=TEXT)
            x += 40 + sl.width(lab, 19) + 34
        y += 40
    size = 24
    need = bullets_height(sl, block["bullets"], block["why"], size)
    bottom = H - 130  # keep clear of the footer rule
    ch = bottom - need - 112 - (y + 8)
    if ch < 300:  # dense week: shrink body text before squeezing the chart further
        size = 22
        need = bullets_height(sl, block["bullets"], block["why"], size)
        ch = bottom - need - 112 - (y + 8)
    ch = max(260, min(430, ch))
    ax = sl.chart_axes(M + 40, y + 8, W - 2 * M - 150, ch)
    draw(ax)
    y += ch + 112
    bullets_block(sl, block["bullets"], block["why"], y, size=size)
    chrome(sl, idx, total, lang, source)
    return sl


def slide_inflation(s, t, lang, idx, total) -> Slide:
    i = s["inflation"]
    es = lang == "es"

    def draw(ax):
        g = ser(i["chart"])
        ax.axhspan(i["band"][0], i["band"][1], color=BAND, lw=0)
        ax.axhline(i["target"], color=MUTED, lw=1.2, ls=(0, (4, 3)))
        ax.plot(g.index, g.values, color=S1, lw=3, solid_capstyle="round")
        end_label(ax, g.index[-1], g.iloc[-1], f"{g.iloc[-1]:.2f}%", S1, dy=10)
        if i.get("core_chart"):
            c = ser(i["core_chart"])
            ax.plot(c.index, c.values, color=S2, lw=3, solid_capstyle="round")
            end_label(ax, c.index[-1], c.iloc[-1], f"{c.iloc[-1]:.2f}%", S2, dy=-10 if c.iloc[-1] < g.iloc[-1] else 22)
        style_axes(ax, ypct=True)
        month_axis(ax, lang)
        lo = min(g.min(), c.min() if i.get("core_chart") else g.min(), i["band"][0]) - 0.4
        hi = max(g.max(), c.max() if i.get("core_chart") else g.max(), i["band"][1]) + 0.4
        ax.set_ylim(lo, hi)

    legend = [("General" if es else "Headline", S1, "solid"), ("Subyacente" if es else "Core", S2, "solid"),
              ("Intervalo 2%–4%" if es else "2%–4% band", None, "band"), ("Meta 3%" if es else "3% target", MUTED, "dash")]
    src = ("Fuente: INEGI vía Banxico (SIE: SP30578, SP74662); encuesta de expectativas Banxico (SR14195). Inflación anual, %."
           if es else "Source: INEGI via Banxico (SIE: SP30578, SP74662); Banxico expectations survey (SR14195). Annual inflation, %.")
    return _chart_slide(s, t["blocks"]["inflation"], "Inflación" if es else "Inflation", lang, idx, total, src, draw, legend)


def slide_policy(s, t, lang, idx, total) -> Slide:
    p = s["policy"]
    es = lang == "es"

    def draw(ax):
        r = ser(p["chart"])
        ax.step(r.index, r.values, where="post", color=S1, lw=3)
        end_label(ax, r.index[-1], r.iloc[-1], f"{r.iloc[-1]:.2f}%", S1)
        if p.get("fed_chart"):
            fd = ser(p["fed_chart"]).reindex(r.index, method="ffill")
            ax.step(fd.index, fd.values, where="post", color=S2, lw=3)
            ax.fill_between(r.index, fd.values, r.values, step="post", color=S1, alpha=0.07, lw=0)
            end_label(ax, fd.index[-1], fd.iloc[-1], f"{fd.iloc[-1]:.2f}%", S2)
            mid = (r.iloc[-1] + fd.iloc[-1]) / 2
            ax.annotate(f"{p['spread_bp']:.0f} {'pb' if es else 'bp'}", (r.index[-1], mid), xytext=(10, 0),
                        textcoords="offset points", fontsize=pt(18), color=MUTED, va="center")
        style_axes(ax, ypct=True)
        month_axis(ax, lang)
        ax.set_ylim(0, max(r.max(), 1) + 1)

    legend = [("Tasa objetivo Banxico" if es else "Banxico target rate", S1, "solid"),
              ("Fed, límite superior" if es else "Fed, upper bound", S2, "solid")]
    src = ("Fuente: Banxico (SIE: SF61745, SR14195); Reserva Federal vía FRED (DFEDTARU). Fin de mes, %."
           if es else "Source: Banxico (SIE: SF61745, SR14195); Federal Reserve via FRED (DFEDTARU). Month-end, %.")
    return _chart_slide(s, t["blocks"]["policy"], "Política monetaria" if es else "Monetary policy", lang, idx, total, src, draw, legend)


def slide_fx(s, t, lang, idx, total) -> Slide:
    f = s["fx"]
    es = lang == "es"

    def draw(ax):
        x = ser(f["chart"])
        ax.plot(x.index, x.values, color=S1, lw=2.6, solid_capstyle="round")
        ax.scatter([x.index[-1]], [x.iloc[-1]], s=70, color=S1, edgecolor="white", linewidth=2, zorder=5)
        end_label(ax, x.index[-1], x.iloc[-1], f"{x.iloc[-1]:.2f}", S1)
        lo_d = pd.Timestamp(f["low_52w_date"])
        if lo_d != x.index[-1]:
            ax.scatter([lo_d], [f["low_52w"]], s=50, color=MUTED, zorder=5)
            ax.annotate(("mín. " if es else "low ") + f"{f['low_52w']:.2f}", (lo_d, f["low_52w"]), xytext=(0, -24),
                        textcoords="offset points", ha="center", fontsize=pt(17), color=MUTED)
        style_axes(ax)
        ax.yaxis.set_major_formatter(matplotlib.ticker.FormatStrFormatter("%.1f"))
        month_axis(ax, lang, every=2)
        pad = (x.max() - x.min()) * 0.15
        ax.set_ylim(x.min() - pad, x.max() + pad)

    src = ("Fuente: Banxico (SIE: SF43718), tipo de cambio FIX diario, pesos por dólar. Últimas 52 semanas."
           if es else "Source: Banxico (SIE: SF43718), daily FIX rate, MXN per USD. Last 52 weeks.")
    legend = [("Tipo de cambio FIX, pesos por dólar (alza = peso más débil)" if es else "FIX rate, MXN per USD (up = weaker peso)", None, "text")]
    return _chart_slide(s, t["blocks"]["fx"], "Tipo de cambio" if es else "Exchange rate", lang, idx, total, src, draw, legend)


def slide_activity(s, t, lang, idx, total) -> Optional[Slide]:
    a = s.get("activity")
    if not a:
        return None
    es = lang == "es"

    def draw(ax):
        lvl = ser(a["chart"])
        mom = (lvl.pct_change() * 100).dropna().tail(24)
        cols = ["#9EC5F4"] * (len(mom) - 1) + ["#1C5CAB"]
        ax.bar(mom.index, mom.values, width=22, color=cols, edgecolor="white", linewidth=1.5)
        ax.axhline(0, color=INK, lw=1)
        v = mom.iloc[-1]
        ax.annotate(f"{v:+.1f}%".replace("-", "−"), (mom.index[-1], v), xytext=(0, -14 if v < 0 else 8),
                    textcoords="offset points", ha="center", va="top" if v < 0 else "bottom",
                    fontsize=pt(20), color="#1C5CAB", fontweight="bold")
        style_axes(ax, ypct=True)
        month_axis(ax, lang, every=3)
        m = max(abs(mom.min()), abs(mom.max())) * 1.3
        ax.set_ylim(-m, m)

    legend = [("Variación mensual del IGAE desestacionalizado, %" if es else "Seasonally adjusted IGAE, monthly change, %", None, "text")]
    src = ("Fuente: INEGI (BIE, serie 737219: IGAE desestacionalizado, 2018=100). Últimos 24 meses."
           if es else "Source: INEGI (BIE, series 737219: seasonally adjusted IGAE, 2018=100). Last 24 months.")
    return _chart_slide(s, t["blocks"]["activity"], "Actividad económica" if es else "Economic activity", lang, idx, total, src, draw, legend)


def slide_agenda(s, t, lang, idx, total) -> Slide:
    sl = Slide()
    es = lang == "es"
    y = title_block(sl, "Qué sigue" if es else "What's next", "Agenda de los próximos días" if es else "The week ahead")
    y += 30
    for r in t["agenda"][:6]:
        sl.text(M, y, r["day"], size=26, color=INK, weight="bold")
        sl.text(M, y + 36, r["time"] + (" h" if r["time"] else ""), size=18, color=MUTED)
        x = M + 210
        sl.rect(x, y + 2, sl.width(r["src"], 16, "semibold") + 20, 28, TINT, radius=6)
        sl.text(x + 10, y + 7, r["src"], size=16, color=S1, weight="semibold")
        yy = sl.para(x, y + 40, r["what"], size=24, color=TEXT, maxw=W - M - x, lh=1.3, weight="medium")
        if r["prev"]:
            yy = sl.para(x, yy + 2, r["prev"], size=19, color=MUTED, maxw=W - M - x)
        y = max(yy, y + 80) + 18
        sl.hline(y - 8)
    if t.get("recent"):
        y += 22
        sl.text(M, y, "Publicado en los últimos 7 días" if es else "Released in the past 7 days", size=19, color=MUTED, weight="semibold")
        y += 40
        for r in t["recent"][:5]:
            sl.text(M, y, r["day"], size=21, color=INK, weight="semibold")
            yy = sl.para(M + 210, y, f"{r['what']} ({r['src']})", size=21, color=TEXT, maxw=W - 2 * M - 210, lh=1.3)
            y = yy + 8
    y += 30
    box_h = 230
    sl.rect(M, y, W - 2 * M, box_h, INK, radius=14)
    sl.para(M + 36, y + 32, "Cada lunes, el pulso macro de México en 2 minutos." if es else
            "Every Monday: Mexico's macro pulse in 2 minutes.", size=32, color="#FFFFFF", weight="bold",
            family=DISPLAY, maxw=W - 2 * M - 72, lh=1.15)
    sl.para(M + 36, y + 120, ("Sígueme para recibir la próxima edición. Metodología y código abierto: " if es else
                              "Follow for the next edition. Methodology and open-source code: ") + REPO_URL,
            size=21, color="#C9D4E3", maxw=W - 2 * M - 72, lh=1.35)
    chrome(sl, idx, total, lang, (f"Calendarios oficiales de INEGI, Banxico y la Fed. Hora del centro de México."
                                  if es else "Official INEGI, Banxico and Fed calendars. Mexico City time."))
    return sl


def render(s: dict, t: dict, lang: str, out_dir: Path) -> dict:
    tl = t[lang]
    order = [k for k in tl["order"] if not (k == "activity" and not s.get("activity"))]
    makers = {"inflation": slide_inflation, "policy": slide_policy, "fx": slide_fx, "activity": slide_activity}
    total = 3 + len(order)
    slides = [slide_cover(s, tl, lang, total), slide_dashboard(s, tl, lang, 2, total)]
    for k, key in enumerate(order):
        slides.append(makers[key](s, tl, lang, 3 + k, total))
    slides.append(slide_agenda(s, tl, lang, total, total))
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

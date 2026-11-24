"""
MX Macro Monitor brand: tokens, fonts and logo.

The logo is drawn with vector primitives so it is identical in the PDF, the PNG
previews and the exported files in assets/logo/ (`python src/brand.py`).

Mark: a cobalt-blue square holding an "M" drawn as a line chart — two strokes
that fall and rise and a final stroke that climbs past the letter's cap line to
a data point. It reads as M (Monitor, México) and as a time series.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.patches import Circle, Rectangle  # noqa: E402

from config import FONT_DIR, ROOT

# --- tokens (docs/DESIGN_SYSTEM.md) --------------------------------------------------------
PAPER = "#F4EFE6"   # warm paper
INK = "#111418"     # headlines, figures, primary series (16.1:1 on paper)
BODY = "#2B2B2B"    # body text (12.4:1)
MUTED = "#5E5A52"   # captions, notes (6.0:1)
AXIS = "#6E685D"    # axis labels (4.8:1)
RULE = "#D8D0C2"    # hairlines
BLUE = "#1546C7"    # brand cobalt: masthead, highlight, latest data point (6.7:1 on paper, 7.7:1 white on it)
GREEN = "#12804F"   # brand green: logo data point, 'estable' state (4.3:1; validated with BLUE, ΔE CVD 24.9)
BLUE_LT = "#8DADFF"  # brand blue for text/marks on ink (8.4:1)
GREEN_LT = "#4FD08F"  # brand green on ink (9.5:1)
# status-only colors (never brand): always paired with a word and a position
OCHRE = "#946410"   # 'vigilancia' (4.5:1)
RED = "#C62F25"     # 'tensión' (4.8:1)
WHITE = "#FFFFFF"

DISPLAY = "Archivo XCond"      # condensed extra bold: headlines
WIDE = "Archivo Exp"           # expanded extra bold: wordmark
SANS = "Archivo"               # labels, data, UI
SERIF = "Newsreader Text"      # justified body
SERIF_D = "Newsreader Display"  # decks, author note

for f in FONT_DIR.glob("*.ttf"):
    font_manager.fontManager.addfont(str(f))
plt.rcParams.update({"font.family": SANS, "pdf.fonttype": 42, "svg.fonttype": "path", "axes.unicode_minus": True})


def pt(px: float) -> float:
    return px * 0.72


def draw_mark(ax, x: float, y: float, size: float, bg: str = BLUE, fg: str = WHITE, dot: str = GREEN):
    """Square mark at (x, y) top-left in a y-down px coordinate system."""
    ax.add_patch(Rectangle((x, y), size, size, fc=bg, ec="none", zorder=10))
    s = size / 120.0
    pts = [(22, 96), (22, 34), (52, 70), (70, 52), (92, 76), (100, 24)]
    xs = [x + px * s for px, _ in pts]
    ys = [y + py * s for _, py in pts]
    lw = 11.5 * s * 0.72 * (ax.figure.dpi / 100) * (100 / ax.figure.dpi)  # stroke ~11.5 px of the mark
    ax.plot(xs, ys, color=fg, lw=lw, solid_capstyle="round", solid_joinstyle="round", zorder=11)
    # data point: green with a ring in the line color so it separates from the blue field
    ax.add_patch(Circle((xs[-1], ys[-1]), 15 * s, fc=fg, ec="none", zorder=12))
    ax.add_patch(Circle((xs[-1], ys[-1]), 10 * s, fc=dot, ec="none", zorder=13))


def draw_logo(ax, x: float, y: float, h: float, color: str = INK, mark_bg: str = BLUE, mark_fg: str = WHITE,
              tagline: str | None = None, tag_color: str = MUTED, accent: str = BLUE, dot: str = GREEN):
    """Horizontal lockup: mark + two-line wordmark. h = mark height in px. Returns right edge x."""
    draw_mark(ax, x, y, h, mark_bg, mark_fg, dot)
    tx = x + h * 1.22
    fs = h * 0.40
    ax.text(tx, y + h * 0.02, "MX MACRO", fontsize=pt(fs), color=color, family=WIDE, fontweight="extra bold",
            va="top", ha="left")
    ax.text(tx, y + h * 0.50, "MONITOR", fontsize=pt(fs), color=accent, family=WIDE, fontweight="extra bold",
            va="top", ha="left")
    if tagline:
        ax.text(tx, y + h * 1.08, tagline, fontsize=pt(h * 0.17), color=tag_color, family=SERIF_D,
                fontstyle="italic", va="top", ha="left")
    return tx + fs * 0.9 * 9


def export_logo_files(out_dir: Path | None = None) -> list[Path]:
    out_dir = out_dir or ROOT / "assets" / "logo"
    out_dir.mkdir(parents=True, exist_ok=True)
    files = []
    variants = {
        "mxmm-lockup-paper": (PAPER, INK, BLUE, WHITE, "Boletín semanal de economía mexicana", BLUE, GREEN),
        "mxmm-lockup-ink": (INK, PAPER, BLUE, WHITE, "Boletín semanal de economía mexicana", BLUE_LT, GREEN),
        "mxmm-lockup-blue": (BLUE, WHITE, WHITE, BLUE, "Boletín semanal de economía mexicana", WHITE, GREEN),
    }
    for name, (bg, fg, mbg, mfg, tag, acc, dot) in variants.items():
        fig = plt.figure(figsize=(9.6, 2.6), dpi=100)
        fig.patch.set_facecolor(bg)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(0, 960)
        ax.set_ylim(260, 0)
        ax.axis("off")
        draw_logo(ax, 60, 50, 140, fg, mbg, mfg, tag, MUTED if bg == PAPER else fg, acc, dot)
        for ext in ("svg", "png"):
            p = out_dir / f"{name}.{ext}"
            fig.savefig(p, dpi=300 if ext == "png" else 100, facecolor=bg, bbox_inches="tight", pad_inches=0.35)
            files.append(p)
        plt.close(fig)
    # square mark (avatar / favicon)
    fig = plt.figure(figsize=(4, 4), dpi=100)
    fig.patch.set_facecolor(BLUE)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 400)
    ax.set_ylim(400, 0)
    ax.axis("off")
    draw_mark(ax, 0, 0, 400)
    for ext in ("svg", "png"):
        p = out_dir / f"mxmm-mark.{ext}"
        fig.savefig(p, dpi=200 if ext == "png" else 100, facecolor=BLUE)
        files.append(p)
    plt.close(fig)
    return files


if __name__ == "__main__":
    for p in export_logo_files():
        print(p)

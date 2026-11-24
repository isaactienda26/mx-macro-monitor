"""
LinkedIn-ready PNG table exporter for Mexico Macro Monitor.
Generates high-resolution (300 DPI) institutional tables with zero overlap.

Author: Isaac Tienda
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle


# Institutional color palette
NAVY = "#0F2537"
SLATE_TEXT = "#1E293B"
MUTED_TEXT = "#475569"
ROW_ALT = "#F4F7FA"
WHITE = "#FFFFFF"
BORDER = "#CBD5E1"
GREEN_BG = "#E6F4EC"
GREEN_FG = "#166534"
RED_BG = "#FEE2E2"
RED_FG = "#991B1B"
ACCENT_LINE = "#1D4ED8"


def _format_change(val: float, change_type: str, lang: str) -> str:
    if val != val:  # NaN check
        return "N/D" if lang == "es" else "N/A"
    sign = "+" if val > 0 else ""
    if change_type == "bps":
        unit = "pb" if lang == "es" else "bps"
        return f"{sign}{val:.0f} {unit}"
    return f"{sign}{val:.2f}%"


def _format_alert(m, lang: str) -> tuple[str, bool]:
    flags: List[str] = []
    if m.mom_anomaly:
        label = "Mensual" if lang == "es" else "MoM"
        flags.append(f"{label} ({m.mom_zscore:+.2f}σ)")
    if m.yoy_anomaly:
        label = "Anual" if lang == "es" else "YoY"
        flags.append(f"{label} ({m.yoy_zscore:+.2f}σ)")
    if not flags:
        return ("En rango" if lang == "es" else "Within range"), False
    prefix = "Alerta: " if lang == "es" else "Alert: "
    if len(flags) == 2:
        return f"{prefix}{flags[0]}\n{flags[1]}", True
    return f"{prefix}{flags[0]}", True


def export_table_png(
    metrics: Dict[str, object],
    output_path: Path,
    lang: str = "es",
    run_date: str | None = None,
) -> Path:
    """
    Renders a LinkedIn-optimized PNG image (3600x1920 px at 300 DPI) of the comparative table.
    """
    if run_date is None:
        run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if lang == "es":
        title = "Monitor Macroeconómico Semanal: México"
        subtitle = f"Fecha de corte: {run_date}  |  Fuentes: Banxico (SIE) e INEGI (BIE)"
        headers = [
            "Indicador",
            "Último dato",
            "Fecha",
            "Var. Mensual",
            "Var. Anual",
            "Monitor (>1σ, 60m)",
        ]
        footer_left = (
            "Nota: IGAE desestacionalizado (2018=100, serie 737121). Tasa objetivo (SF61745) en pb. "
            "FIX (SF43718) al cierre hábil. INPC (SP1). Z-score sobre ventana móvil de 60 meses."
        )
        footer_right = "Isaac Tienda"
    else:
        title = "Weekly Macroeconomic Monitor: Mexico"
        subtitle = f"As of: {run_date}  |  Sources: Banxico (SIE) & INEGI (BIE)"
        headers = [
            "Indicator",
            "Latest Value",
            "Date",
            "MoM Change",
            "YoY Change",
            "Monitor (>1σ, 60m)",
        ]
        footer_left = (
            "Note: IGAE seasonally adjusted (2018=100, series 737121). Policy rate (SF61745) in bps. "
            "USD/MXN FIX (SF43718) business day close. CPI (SP1). Z-score on 60-month rolling window."
        )
        footer_right = "Isaac Tienda"

    fig, ax = plt.subplots(figsize=(12, 6.4), dpi=300)
    fig.patch.set_facecolor(WHITE)
    ax.set_facecolor(WHITE)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    # Top accent bar
    ax.add_patch(Rectangle((0, 98.2), 100, 1.8, facecolor=NAVY, edgecolor="none"))
    ax.add_patch(Rectangle((0, 97.4), 28, 0.8, facecolor=ACCENT_LINE, edgecolor="none"))

    # Title and subtitle
    ax.text(
        3.0,
        90.5,
        title,
        fontsize=20,
        fontweight="bold",
        color=NAVY,
        va="center",
        ha="left",
        family="DejaVu Sans",
    )
    ax.text(
        3.0,
        83.8,
        subtitle,
        fontsize=10.5,
        color=MUTED_TEXT,
        va="center",
        ha="left",
        family="DejaVu Sans",
    )

    # Table geometry (left=3, right=97 -> width=94)
    col_widths = [27.0, 13.5, 11.5, 12.0, 12.0, 18.0]
    col_x = [3.0]
    for w in col_widths[:-1]:
        col_x.append(col_x[-1] + w)
    col_align = ["left", "right", "center", "right", "right", "center"]

    header_y = 69.0
    header_h = 8.5
    row_h = 12.2

    # Header background
    ax.add_patch(
        Rectangle(
            (3.0, header_y),
            sum(col_widths),
            header_h,
            facecolor=NAVY,
            edgecolor="none",
        )
    )

    # Header labels
    for i, h_text in enumerate(headers):
        pad = 1.2 if col_align[i] == "left" else (-1.2 if col_align[i] == "right" else 0.0)
        x_pos = (
            col_x[i] + pad
            if col_align[i] == "left"
            else (
                col_x[i] + col_widths[i] + pad
                if col_align[i] == "right"
                else col_x[i] + col_widths[i] / 2.0
            )
        )
        ax.text(
            x_pos,
            header_y + header_h / 2.0,
            h_text,
            fontsize=9.6,
            fontweight="bold",
            color=WHITE,
            va="center",
            ha=col_align[i],
            family="DejaVu Sans",
        )

    # Data rows
    items = list(metrics.values())
    for row_idx, m in enumerate(items):
        y_bottom = header_y - (row_idx + 1) * row_h
        bg_color = WHITE if row_idx % 2 == 0 else ROW_ALT

        ax.add_patch(
            Rectangle(
                (3.0, y_bottom),
                sum(col_widths),
                row_h,
                facecolor=bg_color,
                edgecolor="none",
            )
        )
        ax.plot([3.0, 97.0], [y_bottom, y_bottom], color=BORDER, linewidth=0.7)

        name = m.name_es if lang == "es" else m.name_en
        unit = m.unit_es if lang == "es" else m.unit_en
        val_fmt = f"{m.latest_value:.4f}" if m.key == "FIX" else f"{m.latest_value:.2f}"
        date_str = m.latest_date.strftime("%Y-%m-%d")
        mom_str = _format_change(m.mom_change, m.change_type, lang)
        yoy_str = _format_change(m.yoy_change, m.change_type, lang)
        alert_text, is_alert = _format_alert(m, lang)

        y_mid = y_bottom + row_h / 2.0

        # Col 0: Indicator name + unit subtitle
        ax.text(
            col_x[0] + 1.2,
            y_mid + 1.8,
            name,
            fontsize=10.0,
            fontweight="bold",
            color=SLATE_TEXT,
            va="center",
            ha="left",
            family="DejaVu Sans",
        )
        ax.text(
            col_x[0] + 1.2,
            y_mid - 2.3,
            f"{m.source} ({m.series_id}) | {unit}",
            fontsize=7.6,
            color=MUTED_TEXT,
            va="center",
            ha="left",
            family="DejaVu Sans",
        )

        # Col 1: Latest Value
        ax.text(
            col_x[1] + col_widths[1] - 1.2,
            y_mid,
            val_fmt,
            fontsize=10.5,
            fontweight="bold",
            color=SLATE_TEXT,
            va="center",
            ha="right",
            family="DejaVu Sans",
        )

        # Col 2: Date
        ax.text(
            col_x[2] + col_widths[2] / 2.0,
            y_mid,
            date_str,
            fontsize=9.4,
            color=MUTED_TEXT,
            va="center",
            ha="center",
            family="DejaVu Sans",
        )

        # Col 3: MoM Change
        ax.text(
            col_x[3] + col_widths[3] - 1.2,
            y_mid,
            mom_str,
            fontsize=10.0,
            fontweight="bold" if m.mom_anomaly else "normal",
            color=RED_FG if m.mom_anomaly else SLATE_TEXT,
            va="center",
            ha="right",
            family="DejaVu Sans",
        )

        # Col 4: YoY Change
        ax.text(
            col_x[4] + col_widths[4] - 1.2,
            y_mid,
            yoy_str,
            fontsize=10.0,
            fontweight="bold" if m.yoy_anomaly else "normal",
            color=RED_FG if m.yoy_anomaly else SLATE_TEXT,
            va="center",
            ha="right",
            family="DejaVu Sans",
        )

        # Col 5: Status badge
        badge_w = col_widths[5] - 1.6
        badge_h = 7.4 if "\n" in alert_text else 6.0
        badge_x = col_x[5] + 0.8
        badge_y = y_mid - badge_h / 2.0
        pill_bg = RED_BG if is_alert else GREEN_BG
        pill_fg = RED_FG if is_alert else GREEN_FG

        ax.add_patch(
            FancyBboxPatch(
                (badge_x, badge_y),
                badge_w,
                badge_h,
                boxstyle="round,pad=0.3,rounding_size=1.2",
                facecolor=pill_bg,
                edgecolor="none",
            )
        )
        ax.text(
            col_x[5] + col_widths[5] / 2.0,
            y_mid,
            alert_text,
            fontsize=7.6 if is_alert else 8.6,
            fontweight="bold",
            color=pill_fg,
            va="center",
            ha="center",
            linespacing=1.25,
            family="DejaVu Sans",
        )

    # Footer separator
    ax.plot([3.0, 97.0], [14.5, 14.5], color=BORDER, linewidth=0.9)

    # Footer text
    ax.text(
        3.0,
        8.2,
        footer_left,
        fontsize=7.4,
        color=MUTED_TEXT,
        va="center",
        ha="left",
        family="DejaVu Sans",
    )
    ax.text(
        97.0,
        8.2,
        footer_right,
        fontsize=9.2,
        fontweight="bold",
        color=NAVY,
        va="center",
        ha="right",
        family="DejaVu Sans",
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    fig.savefig(output_path, dpi=300, facecolor=WHITE)
    plt.close(fig)
    return output_path

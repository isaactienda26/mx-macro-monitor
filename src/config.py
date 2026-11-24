"""
Central configuration for MX Macro Monitor: series catalog, paths, thresholds.

Every series ID below was verified against the source metadata (Banxico SIE
`/series/{id}` endpoint and INEGI's official feed list) on 2026-11-24.
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / os.getenv("OUTPUT_DIR", "bulletins")
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
AGENDA_FILE = ROOT / "config" / "agenda.yml"
FONT_DIR = ROOT / "assets" / "fonts"

AUTHOR = os.getenv("MONITOR_AUTHOR", "Isaac Tienda")
AUTHOR_ROLE_ES = os.getenv("MONITOR_ROLE_ES", "Economista")
AUTHOR_ROLE_EN = os.getenv("MONITOR_ROLE_EN", "Economist")
REPO_URL = os.getenv("MONITOR_REPO_URL", "github.com/isaactienda26/mx-macro-monitor")

# Years of history requested from the APIs (enough for 60-month windows + charts).
HISTORY_YEARS = int(os.getenv("HISTORY_YEARS", "8"))

# Anomaly monitor: z-score of the latest change against the PRIOR window
# (the latest observation is excluded from its own mean and standard deviation).
ZSCORE_WINDOW_MONTHS = int(os.getenv("STD_WINDOW_MONTHS", "60"))
ZSCORE_WINDOW_WEEKS = int(os.getenv("ZSCORE_WINDOW_WEEKS", "260"))
Z_UNUSUAL = 1.5   # |z| >= 1.5 -> "unusual"
Z_ATYPICAL = 2.0  # |z| >= 2.0 -> "atypical"

# Banxico inflation target and variability band (percent).
INFLATION_TARGET = 3.0
INFLATION_BAND = (2.0, 4.0)

# --- Series catalog ---------------------------------------------------------
# key -> (source, series id, human description)
SERIES = {
    # Banxico SIE
    "inpc_index": ("banxico", "SP1", "INPC, índice general (mensual)"),
    "inflation_yoy": ("banxico", "SP30578", "INPC, variación anual (%)"),
    "inflation_mom": ("banxico", "SP30577", "INPC, variación mensual (%)"),
    "core_yoy": ("banxico", "SP74662", "Inflación subyacente, anual (%)"),
    "core_mom": ("banxico", "SP74660", "Inflación subyacente, mensual (%)"),
    "policy_rate": ("banxico", "SF61745", "Tasa objetivo Banxico (%)"),
    "fix": ("banxico", "SF43718", "Tipo de cambio FIX (MXN por USD)"),
    "exp_12m": ("banxico", "SR14195", "Expectativa de inflación general 12 meses, mediana (%)"),
    "exp_core_12m": ("banxico", "SR14202", "Expectativa de inflación subyacente 12 meses, mediana (%)"),
    # INEGI BIE (737219 = desestacionalizada; 737121 = cifras originales)
    "igae_sa": ("inegi", "737219", "IGAE, serie desestacionalizada (2018=100)"),
    # Federal Reserve (via FRED public CSV, no key required)
    "fed_upper": ("fred", "DFEDTARU", "Fed funds target range, upper limit (%)"),
}

# Series without which the bulletin is not published (pipeline exits 1).
CRITICAL = {"inflation_yoy", "policy_rate", "fix"}

"""
Mexico Macro Monitor
Automated ETL pipeline querying Banxico SIE and INEGI BIE public APIs.
Calculates MoM/YoY variations, detects >1 standard deviation anomalies over a
60-month rolling window, generates bilingual one-page Markdown bulletins, and
exports LinkedIn-ready PNG comparative tables.

Author: Isaac Tienda
"""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from table_exporter import export_table_png

# ---------------------------------------------------------------------------
# Configuration and Logging
# ---------------------------------------------------------------------------
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

BANXICO_TOKEN = os.getenv("BANXICO_TOKEN")
INEGI_TOKEN = os.getenv("INEGI_TOKEN")
STD_WINDOW_MONTHS = int(os.getenv("STD_WINDOW_MONTHS", "60"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "bulletins"))

BANXICO_BASE_URL = "https://www.banxico.org.mx/SieAPIRest/service/v1/series"
INEGI_BASE_URL = (
    "https://www.inegi.org.mx/app/api/indicadores/desarrolladores/jsonxml/INDICATOR"
)

# Official series identifiers
SERIES_CATALOG = {
    "INPC": {
        "source": "Banxico",
        "id": "SP1",
        "frequency": "monthly",
        "change_type": "pct",
        "unit_es": "Índice",
        "unit_en": "Index",
        "name_es": "Inflación General (INPC)",
        "name_en": "Headline Inflation (CPI / INPC)",
    },
    "TARGET_RATE": {
        "source": "Banxico",
        "id": "SF61745",
        "frequency": "daily",
        "change_type": "bps",
        "unit_es": "% anual",
        "unit_en": "% annual",
        "name_es": "Tasa de Interés Objetivo",
        "name_en": "Banxico Policy Rate",
    },
    "FIX": {
        "source": "Banxico",
        "id": "SF43718",
        "frequency": "daily",
        "change_type": "pct",
        "unit_es": "MXN/USD",
        "unit_en": "MXN/USD",
        "name_es": "Tipo de Cambio FIX",
        "name_en": "USD/MXN FIX Exchange Rate",
    },
    "IGAE": {
        "source": "INEGI",
        "id": "737121",  # IGAE Seasonally Adjusted, Base 2018=100
        "frequency": "monthly",
        "change_type": "pct",
        "unit_es": "Índice 2018=100 (Desest.)",
        "unit_en": "Index 2018=100 (SA)",
        "name_es": "Actividad Económica (IGAE)",
        "name_en": "Economic Activity (IGAE SA)",
    },
}


@dataclass
class IndicatorMetrics:
    key: str
    name_es: str
    name_en: str
    source: str
    series_id: str
    latest_date: pd.Timestamp
    latest_value: float
    mom_change: float
    yoy_change: float
    change_type: str  # "pct" or "bps"
    mom_zscore: float
    yoy_zscore: float
    mom_anomaly: bool
    yoy_anomaly: bool
    unit_es: str
    unit_en: str


# ---------------------------------------------------------------------------
# HTTP Session with Retries
# ---------------------------------------------------------------------------
def build_http_session() -> requests.Session:
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


# ---------------------------------------------------------------------------
# API Clients
# ---------------------------------------------------------------------------
def fetch_banxico_series(
    session: requests.Session, series_id: str, token: str
) -> pd.Series:
    url = f"{BANXICO_BASE_URL}/{series_id}/datos"
    headers = {"Bmx-Token": token, "Accept": "application/json"}

    try:
        response = session.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise RuntimeError(f"Banxico API request failed for {series_id}: {exc}") from exc
    except ValueError as exc:
        raise RuntimeError(f"Invalid JSON from Banxico for {series_id}: {exc}") from exc

    try:
        records = payload["bmx"]["series"][0]["datos"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(
            f"Unexpected Banxico payload structure for {series_id}"
        ) from exc

    dates: List[pd.Timestamp] = []
    values: List[float] = []

    for row in records:
        raw_val = str(row.get("dato", "")).replace(",", "").strip()
        if raw_val in ("", "N/E", "null", "None"):
            continue
        try:
            dt = pd.to_datetime(row["fecha"], format="%d/%m/%Y")
            val = float(raw_val)
            dates.append(dt)
            values.append(val)
        except ValueError:
            continue

    if not values:
        raise RuntimeError(f"No valid observations returned by Banxico for {series_id}")

    series = pd.Series(values, index=pd.DatetimeIndex(dates), name=series_id)
    return series.sort_index()


def fetch_inegi_series(
    session: requests.Session, indicator_id: str, token: str
) -> pd.Series:
    # INEGI retired "BIE" as a source id; BIE series are now served under "BIE-BISE".
    url = f"{INEGI_BASE_URL}/{indicator_id}/es/00/false/BIE-BISE/2.0/{token}?type=json"

    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        # The token travels in the URL path; never let it reach the logs.
        safe_msg = str(exc).replace(token, "***")
        raise RuntimeError(
            f"INEGI API request failed for {indicator_id}: {safe_msg}"
        ) from None
    except ValueError as exc:
        raise RuntimeError(f"Invalid JSON from INEGI for {indicator_id}: {exc}") from exc

    try:
        observations = payload["Series"][0]["OBSERVATIONS"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(
            f"Unexpected INEGI payload structure for {indicator_id}"
        ) from exc

    dates: List[pd.Timestamp] = []
    values: List[float] = []

    for obs in observations:
        raw_val = obs.get("OBS_VALUE")
        period = str(obs.get("TIME_PERIOD", "")).strip()
        if raw_val is None or raw_val == "":
            continue
        try:
            dt = pd.to_datetime(period, format="%Y/%m")
            val = float(raw_val)
            dates.append(dt)
            values.append(val)
        except ValueError:
            continue

    if not values:
        raise RuntimeError(f"No valid observations returned by INEGI for {indicator_id}")

    series = pd.Series(values, index=pd.DatetimeIndex(dates), name=indicator_id)
    return series.sort_index()


# ---------------------------------------------------------------------------
# Analytics and Anomaly Detection
# ---------------------------------------------------------------------------
def compute_calendar_change(
    series: pd.Series, months_back: int, change_type: str
) -> pd.Series:
    """
    Computes exact calendar-offset variation (MoM or YoY) for both daily and
    monthly series using nearest prior observation (asof lookup).
    """
    results = []
    idx = series.index
    for dt in idx:
        target_dt = dt - pd.DateOffset(months=months_back)
        prior_val = series.asof(target_dt)
        if pd.isna(prior_val) or prior_val == 0:
            results.append(np.nan)
        elif change_type == "bps":
            results.append((series.loc[dt] - prior_val) * 100.0)
        else:
            results.append(((series.loc[dt] / prior_val) - 1.0) * 100.0)
    return pd.Series(results, index=idx)


def compute_zscore(change_series: pd.Series, window_months: int) -> Tuple[float, bool]:
    clean = change_series.dropna()
    if len(clean) < 2:
        return 0.0, False

    latest_dt = clean.index[-1]
    cutoff_dt = latest_dt - pd.DateOffset(months=window_months)
    window_data = clean.loc[clean.index >= cutoff_dt]

    if len(window_data) < 2:
        window_data = clean

    mean = float(window_data.mean())
    std = float(window_data.std(ddof=1))

    if std == 0 or np.isnan(std):
        return 0.0, False

    zscore = (float(clean.iloc[-1]) - mean) / std
    return zscore, abs(zscore) > 1.0


def evaluate_indicator(key: str, series: pd.Series) -> IndicatorMetrics:
    meta = SERIES_CATALOG[key]
    change_type = meta["change_type"]

    mom_series = compute_calendar_change(series, months_back=1, change_type=change_type)
    yoy_series = compute_calendar_change(series, months_back=12, change_type=change_type)

    mom_z, mom_anom = compute_zscore(mom_series, STD_WINDOW_MONTHS)
    yoy_z, yoy_anom = compute_zscore(yoy_series, STD_WINDOW_MONTHS)

    return IndicatorMetrics(
        key=key,
        name_es=meta["name_es"],
        name_en=meta["name_en"],
        source=meta["source"],
        series_id=meta["id"],
        latest_date=series.index[-1],
        latest_value=float(series.iloc[-1]),
        mom_change=float(mom_series.iloc[-1]),
        yoy_change=float(yoy_series.iloc[-1]),
        change_type=change_type,
        mom_zscore=mom_z,
        yoy_zscore=yoy_z,
        mom_anomaly=mom_anom,
        yoy_anomaly=yoy_anom,
        unit_es=meta["unit_es"],
        unit_en=meta["unit_en"],
    )


# ---------------------------------------------------------------------------
# Bulletin Generation (Spanish and English, max 1 page)
# ---------------------------------------------------------------------------
def format_change(val: float, change_type: str, lang: str) -> str:
    if pd.isna(val):
        return "N/D" if lang == "es" else "N/A"
    sign = "+" if val > 0 else ""
    if change_type == "bps":
        unit = "pb" if lang == "es" else "bps"
        return f"{sign}{val:.0f} {unit}"
    return f"{sign}{val:.2f}%"


def format_alert(m: IndicatorMetrics, lang: str) -> str:
    flags = []
    if m.mom_anomaly:
        label = "Mensual" if lang == "es" else "MoM"
        flags.append(f"{label} ({m.mom_zscore:+.2f}σ)")
    if m.yoy_anomaly:
        label = "Anual" if lang == "es" else "YoY"
        flags.append(f"{label} ({m.yoy_zscore:+.2f}σ)")
    if not flags:
        return "En rango" if lang == "es" else "Within range"
    return "Alerta: " + ", ".join(flags) if lang == "es" else "Alert: " + ", ".join(flags)


def build_takeaways_es(metrics: Dict[str, IndicatorMetrics]) -> List[str]:
    inpc = metrics["INPC"]
    rate = metrics["TARGET_RATE"]
    fx = metrics["FIX"]
    igae = metrics["IGAE"]

    real_rate = rate.latest_value - inpc.yoy_change
    anomalies = [m.name_es for m in metrics.values() if m.mom_anomaly or m.yoy_anomaly]
    anom_text = (
        f"Se detectan variaciones mayores a 1 desviación estándar en: {', '.join(anomalies)}."
        if anomalies
        else "Ningún indicador registra desviaciones superiores a 1 desviación estándar respecto a su ventana móvil de 60 meses."
    )

    return [
        (
            f"**Postura monetaria e inflación:** La inflación general anual se ubica en "
            f"{inpc.yoy_change:.2f}% ({inpc.latest_date.strftime('%Y-%m')}) frente a una tasa objetivo "
            f"de {rate.latest_value:.2f}% ({rate.latest_date.strftime('%Y-%m-%d')}), lo que implica "
            f"una tasa real ex post de {real_rate:.2f}%."
        ),
        (
            f"**Actividad económica y tipo de cambio:** El IGAE desestacionalizado registra una "
            f"variación mensual de {format_change(igae.mom_change, 'pct', 'es')} y anual de "
            f"{format_change(igae.yoy_change, 'pct', 'es')} ({igae.latest_date.strftime('%Y-%m')}). "
            f"El tipo de cambio FIX cierra en {fx.latest_value:.4f} MXN/USD "
            f"({format_change(fx.mom_change, 'pct', 'es')} mensual)."
        ),
        f"**Monitor de desviaciones (>1σ, 60 meses):** {anom_text}",
    ]


def build_takeaways_en(metrics: Dict[str, IndicatorMetrics]) -> List[str]:
    inpc = metrics["INPC"]
    rate = metrics["TARGET_RATE"]
    fx = metrics["FIX"]
    igae = metrics["IGAE"]

    real_rate = rate.latest_value - inpc.yoy_change
    anomalies = [m.name_en for m in metrics.values() if m.mom_anomaly or m.yoy_anomaly]
    anom_text = (
        f"Changes exceeding 1 standard deviation detected in: {', '.join(anomalies)}."
        if anomalies
        else "No indicator exceeds 1 standard deviation relative to its 60-month rolling window."
    )

    return [
        (
            f"**Monetary stance and inflation:** Annual headline inflation stands at "
            f"{inpc.yoy_change:.2f}% ({inpc.latest_date.strftime('%Y-%m')}) against a policy rate "
            f"of {rate.latest_value:.2f}% ({rate.latest_date.strftime('%Y-%m-%d')}), implying "
            f"an ex-post real rate of {real_rate:.2f}%."
        ),
        (
            f"**Economic activity and FX:** Seasonally adjusted IGAE posted "
            f"{format_change(igae.mom_change, 'pct', 'en')} MoM and "
            f"{format_change(igae.yoy_change, 'pct', 'en')} YoY ({igae.latest_date.strftime('%Y-%m')}). "
            f"USD/MXN FIX closed at {fx.latest_value:.4f} "
            f"({format_change(fx.mom_change, 'pct', 'en')} MoM)."
        ),
        f"**Anomaly monitor (>1σ, 60-month window):** {anom_text}",
    ]


def render_bulletin(metrics: Dict[str, IndicatorMetrics], lang: str, run_date: str) -> str:
    if lang == "es":
        lines = [
            "# Boletín Macroeconómico Semanal: México",
            f"**Fecha de corte:** {run_date} | **Autor:** Isaac Tienda | **Fuentes:** Banxico (SIE) e INEGI (BIE)",
            "",
            "## Tabla Comparativa de Indicadores",
            "",
            "| Indicador | Último dato | Fecha | Var. Mensual | Var. Anual | Monitor (>1σ, 60m) |",
            "| :--- | :---: | :---: | :---: | :---: | :--- |",
        ]
        for m in metrics.values():
            val_fmt = f"{m.latest_value:.4f}" if m.key == "FIX" else f"{m.latest_value:.2f}"
            lines.append(
                f"| {m.name_es} | {val_fmt} {m.unit_es} | {m.latest_date.strftime('%Y-%m-%d')} | "
                f"{format_change(m.mom_change, m.change_type, 'es')} | "
                f"{format_change(m.yoy_change, m.change_type, 'es')} | {format_alert(m, 'es')} |"
            )
        lines.extend(["", "## Lectura Ejecutiva", ""])
        for idx, bullet in enumerate(build_takeaways_es(metrics), start=1):
            lines.append(f"{idx}. {bullet}")
        lines.extend(
            [
                "",
                "---",
                "*Nota metodológica: IGAE en serie desestacionalizada (base 2018=100, serie INEGI 737121). "
                "Tasa objetivo (SF61745) en puntos base (pb). Tipo de cambio FIX (SF43718) al cierre del último día hábil. "
                "INPC (SP1). Alertas calculadas con puntaje Z sobre ventana móvil de 60 meses.*",
            ]
        )
    else:
        lines = [
            "# Weekly Macroeconomic Bulletin: Mexico",
            f"**As of:** {run_date} | **Author:** Isaac Tienda | **Sources:** Banxico (SIE) & INEGI (BIE)",
            "",
            "## Comparative Indicators Table",
            "",
            "| Indicator | Latest Value | Date | MoM Change | YoY Change | Monitor (>1σ, 60m) |",
            "| :--- | :---: | :---: | :---: | :---: | :--- |",
        ]
        for m in metrics.values():
            val_fmt = f"{m.latest_value:.4f}" if m.key == "FIX" else f"{m.latest_value:.2f}"
            lines.append(
                f"| {m.name_en} | {val_fmt} {m.unit_en} | {m.latest_date.strftime('%Y-%m-%d')} | "
                f"{format_change(m.mom_change, m.change_type, 'en')} | "
                f"{format_change(m.yoy_change, m.change_type, 'en')} | {format_alert(m, 'en')} |"
            )
        lines.extend(["", "## Executive Takeaways", ""])
        for idx, bullet in enumerate(build_takeaways_en(metrics), start=1):
            lines.append(f"{idx}. {bullet}")
        lines.extend(
            [
                "",
                "---",
                "*Methodological note: IGAE seasonally adjusted (base 2018=100, INEGI series 737121). "
                "Policy rate (SF61745) changes reported in basis points (bps). USD/MXN FIX (SF43718) at latest business day close. "
                "CPI/INPC (SP1). Alerts computed via Z-score over a 60-month rolling window.*",
            ]
        )

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------
def main() -> int:
    if not BANXICO_TOKEN or not INEGI_TOKEN:
        logger.error(
            "Missing API tokens. Set BANXICO_TOKEN and INEGI_TOKEN environment variables."
        )
        return 1

    session = build_http_session()
    metrics: Dict[str, IndicatorMetrics] = {}

    try:
        for key, meta in SERIES_CATALOG.items():
            logger.info("Fetching %s (%s: %s)...", key, meta["source"], meta["id"])
            if meta["source"] == "Banxico":
                series = fetch_banxico_series(session, meta["id"], BANXICO_TOKEN)
            else:
                series = fetch_inegi_series(session, meta["id"], INEGI_TOKEN)

            metrics[key] = evaluate_indicator(key, series)
            logger.info(
                "%s processed | Latest: %.4f (%s)",
                key,
                metrics[key].latest_value,
                metrics[key].latest_date.strftime("%Y-%m-%d"),
            )
    except RuntimeError as exc:
        logger.error("Pipeline aborted: %s", exc)
        return 1

    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    es_md = OUTPUT_DIR / "latest_es.md"
    en_md = OUTPUT_DIR / "latest_en.md"
    es_png = OUTPUT_DIR / "table_es.png"
    en_png = OUTPUT_DIR / "table_en.png"

    es_md.write_text(render_bulletin(metrics, "es", run_date), encoding="utf-8")
    en_md.write_text(render_bulletin(metrics, "en", run_date), encoding="utf-8")
    export_table_png(metrics, es_png, lang="es", run_date=run_date)
    export_table_png(metrics, en_png, lang="en", run_date=run_date)

    logger.info("Bulletins generated: %s, %s", es_md, en_md)
    logger.info("LinkedIn PNG tables generated: %s, %s", es_png, en_png)
    return 0


if __name__ == "__main__":
    sys.exit(main())

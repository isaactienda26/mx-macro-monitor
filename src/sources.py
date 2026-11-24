"""
API clients (Banxico SIE, INEGI BIE, FRED) plus a CSV cache in data/raw/.

The cache is committed with every weekly run, so any bulletin can be rebuilt
offline (`python src/macro_monitor.py --offline`) and audited later.
"""

from __future__ import annotations

import io
import logging
import os
from datetime import date, timedelta
from typing import Dict, Iterable, List, Optional

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import HISTORY_YEARS, RAW_DIR, SERIES

logger = logging.getLogger(__name__)

BANXICO_URL = "https://www.banxico.org.mx/SieAPIRest/service/v1/series"
INEGI_URL = "https://www.inegi.org.mx/app/api/indicadores/desarrolladores/jsonxml/INDICATOR"
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"


def build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=1.5, status_forcelist=[429, 500, 502, 503, 504],
                  allowed_methods=["GET"])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.headers["User-Agent"] = "mx-macro-monitor/2.0 (+https://github.com/isaactienda26/mx-macro-monitor)"
    return session


def _to_float(raw) -> Optional[float]:
    s = str(raw).replace(",", "").strip()
    if s in ("", "N/E", "null", "None", "."):
        return None
    try:
        return float(s)
    except ValueError:
        return None


# --- Banxico -----------------------------------------------------------------
def fetch_banxico(session: requests.Session, ids: List[str], token: str) -> Dict[str, pd.Series]:
    """Fetch several SIE series in one request (max 20 ids per call)."""
    start = (date.today() - timedelta(days=365 * HISTORY_YEARS)).isoformat()
    end = date.today().isoformat()
    out: Dict[str, pd.Series] = {}
    for i in range(0, len(ids), 20):
        chunk = ",".join(ids[i:i + 20])
        url = f"{BANXICO_URL}/{chunk}/datos/{start}/{end}"
        resp = session.get(url, headers={"Bmx-Token": token, "Accept": "application/json"}, timeout=60)
        resp.raise_for_status()
        for s in resp.json()["bmx"]["series"]:
            dates, vals = [], []
            for row in s.get("datos", []) or []:
                v = _to_float(row.get("dato"))
                if v is None:
                    continue
                dates.append(pd.to_datetime(row["fecha"], format="%d/%m/%Y"))
                vals.append(v)
            if vals:
                out[s["idSerie"]] = pd.Series(vals, index=pd.DatetimeIndex(dates)).sort_index()
    return out


# --- INEGI -------------------------------------------------------------------
def fetch_inegi(session: requests.Session, indicator_id: str, token: str) -> pd.Series:
    url = f"{INEGI_URL}/{indicator_id}/es/00/false/BIE-BISE/2.0/{token}?type=json"
    try:
        resp = session.get(url, timeout=60)
        resp.raise_for_status()
        payload = resp.json()
    except requests.RequestException as exc:
        # The token travels in the URL path; never let it reach the logs.
        raise RuntimeError(f"INEGI request failed for {indicator_id}: {str(exc).replace(token, '***')}") from None
    obs = payload["Series"][0]["OBSERVATIONS"]
    dates, vals = [], []
    for o in obs:
        v = _to_float(o.get("OBS_VALUE"))
        if v is None:
            continue
        dates.append(pd.to_datetime(str(o["TIME_PERIOD"]).strip(), format="%Y/%m"))
        vals.append(v)
    if not vals:
        raise RuntimeError(f"INEGI returned no observations for {indicator_id}")
    return pd.Series(vals, index=pd.DatetimeIndex(dates)).sort_index()


# --- FRED ----------------------------------------------------------------------
def fetch_fred(session: requests.Session, series_id: str) -> pd.Series:
    start = (date.today() - timedelta(days=365 * HISTORY_YEARS)).isoformat()
    resp = session.get(FRED_URL, params={"id": series_id, "cosd": start}, timeout=60)
    resp.raise_for_status()
    df = pd.read_csv(io.StringIO(resp.text))
    df.columns = ["date", "value"]
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna()
    return pd.Series(df["value"].values, index=pd.to_datetime(df["date"])).sort_index()


# --- Cache ---------------------------------------------------------------------
def save_cache(data: Dict[str, pd.Series]) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for key, s in data.items():
        s.rename("value").to_frame().rename_axis("date").to_csv(RAW_DIR / f"{key}.csv", float_format="%.6g")


def load_cache(keys: Iterable[str]) -> Dict[str, pd.Series]:
    out = {}
    for key in keys:
        path = RAW_DIR / f"{key}.csv"
        if path.exists():
            df = pd.read_csv(path, parse_dates=["date"])
            out[key] = pd.Series(df["value"].values, index=pd.DatetimeIndex(df["date"])).sort_index()
    return out


def fetch_all(offline: bool = False) -> tuple[Dict[str, pd.Series], List[str]]:
    """Return ({key: series}, [warnings]). Falls back to cached data per series on failure."""
    keys = list(SERIES)
    cached = load_cache(keys)
    if offline:
        missing = [k for k in keys if k not in cached]
        return cached, [f"Sin caché para: {', '.join(missing)}"] if missing else []

    warnings: List[str] = []
    data: Dict[str, pd.Series] = {}
    session = build_session()
    bx_token, ine_token = os.getenv("BANXICO_TOKEN"), os.getenv("INEGI_TOKEN")

    bx_keys = [k for k, (src, _, _) in SERIES.items() if src == "banxico"]
    if bx_token:
        try:
            got = fetch_banxico(session, [SERIES[k][1] for k in bx_keys], bx_token)
            for k in bx_keys:
                if SERIES[k][1] in got:
                    data[k] = got[SERIES[k][1]]
        except (requests.RequestException, KeyError, ValueError) as exc:
            warnings.append(f"Banxico SIE no respondió ({type(exc).__name__}); se usa caché.")
    else:
        warnings.append("BANXICO_TOKEN no definido; se usa caché.")

    for k, (src, sid, _) in SERIES.items():
        if k in data:
            continue
        try:
            if src == "inegi":
                if not ine_token:
                    raise RuntimeError("INEGI_TOKEN no definido")
                data[k] = fetch_inegi(session, sid, ine_token)
            elif src == "fred":
                data[k] = fetch_fred(session, sid)
        except (requests.RequestException, RuntimeError, KeyError, ValueError, IndexError) as exc:
            warnings.append(f"{k} ({sid}) falló: {exc}; se usa caché.")

    for k in keys:
        if k not in data and k in cached:
            data[k] = cached[k]
            if not any(k in w for w in warnings):
                warnings.append(f"{k}: dato de caché.")
    save_cache({k: v for k, v in data.items()})
    return data, warnings


# --- BIS (peers) ---------------------------------------------------------------------
BIS_URL = "https://stats.bis.org/api/v1/data"
PEERS = ["MX", "BR", "CL", "CO", "PE"]
PEER_CCY = {"MX": "MXN", "BR": "BRL", "CL": "CLP", "CO": "COP", "PE": "PEN"}


def _bis_csv(session: requests.Session, flow: str, key: str, start: str) -> pd.DataFrame:
    r = session.get(f"{BIS_URL}/{flow}/{key}/all", params={"startPeriod": start, "format": "csv"}, timeout=90)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text), usecols=lambda c: c in {"REF_AREA", "TIME_PERIOD", "OBS_VALUE", "CURRENCY"})
    df["OBS_VALUE"] = pd.to_numeric(df["OBS_VALUE"], errors="coerce")
    return df.dropna(subset=["OBS_VALUE"])


def fetch_peers(offline: bool = False) -> tuple[Dict[str, pd.DataFrame], List[str]]:
    """Policy rates (monthly), CPI y/y (monthly) and FX vs USD (daily) for Mexico and LatAm peers + US rate."""
    paths = {k: RAW_DIR / f"bis_{k}.csv" for k in ("policy", "cpi", "fx")}
    if offline:
        out = {k: pd.read_csv(p) for k, p in paths.items() if p.exists()}
        return out, ([] if len(out) == 3 else ["Sin caché BIS completa."])
    session, warnings, out = build_session(), [], {}
    y2 = (date.today() - timedelta(days=800)).isoformat()
    areas = "+".join(PEERS)
    jobs = {
        "policy": ("WS_CBPOL", f"M.{areas}+US", y2[:7]),
        "cpi": ("WS_LONG_CPI", f"M.{areas}+US.771", y2[:7]),
        "fx": ("WS_XRU", f"D.{areas}.{'+'.join(PEER_CCY.values())}.A", y2),
    }
    for k, (flow, key, start) in jobs.items():
        try:
            df = _bis_csv(session, flow, key, start)
            df.to_csv(paths[k], index=False)
            out[k] = df
        except (requests.RequestException, ValueError, KeyError) as exc:
            warnings.append(f"BIS {flow} falló ({type(exc).__name__}); se usa caché.")
            if paths[k].exists():
                out[k] = pd.read_csv(paths[k])
    return out, warnings

"""
Own value-added metrics for each edition. Every rule is public (docs/METODOLOGIA.md)
and every input comes from an institutional source already in the pipeline.

1. fx_rank        — the week's peso move ranked against every week since the series start.
2. import_cost    — what the week's move means for a USD 100,000 import.
3. thermometer    — six rule-based readings: Estable / Vigilancia / Tensión.
4. peers          — policy rate, inflation and ex-post real rate: Mexico vs Brazil, Chile,
                    Colombia, Peru and the US (BIS).
5. dollar_box     — was it the peso or the dollar? MXN vs BRL vs the Fed's broad dollar index
                    over the same window (Federal Reserve H.10).
"""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from config import INFLATION_BAND, INFLATION_TARGET

STATES = ("estable", "vigilancia", "tension")
PEER_NAMES = {
    "es": {"MX": "México", "BR": "Brasil", "CL": "Chile", "CO": "Colombia", "PE": "Perú", "US": "Estados Unidos"},
    "en": {"MX": "Mexico", "BR": "Brazil", "CL": "Chile", "CO": "Colombia", "PE": "Peru", "US": "United States"},
}


# --- 1. the week's move in history -----------------------------------------------------------
def fx_rank(fix: pd.Series) -> dict:
    """Weekly % change (Friday close; current week point-to-point vs 7 days earlier)."""
    t = fix.index[-1]
    wk = fix.resample("W-FRI").last().pct_change().dropna() * 100
    wk = wk[wk.index < t - pd.Timedelta(days=6)]  # completed weeks before the current one
    prev = fix[fix.index <= t - pd.Timedelta(days=7)].iloc[-1]
    cur = (fix.iloc[-1] / prev - 1) * 100
    allw = pd.concat([wk, pd.Series([cur], index=[t])])
    larger = int(((wk >= cur) if cur > 0 else (wk <= cur)).sum())
    return {
        "chg": round(float(cur), 2),
        "n_weeks": int(len(allw)),
        "n_larger": larger,                     # completed weeks with an equal or larger move, same sign
        "rank": larger + 1,
        "pct_rank": round(100 * (1 - larger / len(allw)), 1),
        "start": allw.index[0].strftime("%Y-%m-%d"),
        "weeks": {"dates": [d.strftime("%Y-%m-%d") for d in allw.index],
                  "values": [round(float(v), 3) for v in allw.values]},
    }


# --- 2. business translation -----------------------------------------------------------------
def import_cost(fx: dict, usd: float = 100_000) -> dict:
    v, w = fx["value"], fx["value_1w_ago"]
    return {"usd": usd, "mxn_now": round(usd * v), "mxn_1w": round(usd * w), "diff": round(usd * (v - w))}


# --- 3. thermometer --------------------------------------------------------------------------
def _band_state(x: float) -> str:
    lo, hi = INFLATION_BAND
    if abs(x - INFLATION_TARGET) <= 0.5:
        return "estable"
    return "vigilancia" if lo <= x <= hi else "tension"


def _signal_state(sig: str) -> str:
    return {"normal": "estable", "unusual": "vigilancia", "atypical": "tension"}.get(sig, "na")


def thermometer(s: dict) -> List[dict]:
    i, e, p, f, a = s["inflation"], s["expectations"] or {}, s["policy"], s["fx"], s["activity"] or {}
    lo, hi = p["neutral_range"]
    r = p["real_ex_ante"]
    rows = [
        {"key": "inflation", "value": i["yoy"], "unit": "%", "state": _band_state(i["yoy"]), "rule": "band"},
        {"key": "core", "value": i["core"], "unit": "%", "state": _band_state(i["core"]), "rule": "band"},
        {"key": "expectations", "value": e.get("exp_12m_mean"), "unit": "%",
         "state": _band_state(e["exp_12m_mean"]) if e.get("exp_12m_mean") is not None else "na", "rule": "band"},
        {"key": "real_rate", "value": r, "unit": "%",
         "state": "estable" if lo <= r <= hi else "vigilancia" if lo - 0.5 <= r <= hi + 0.5 else "tension",
         "rule": "neutral"},
        {"key": "fx", "value": f["chg_1w_pct"], "unit": "%", "state": _signal_state(f["signal"]), "rule": "z",
         "z": f["z_1w"]},
        {"key": "activity", "value": a.get("mom"), "unit": "%", "state": _signal_state(a.get("signal", "na")),
         "rule": "z", "z": a.get("z")},
    ]
    return rows


def thermometer_score(rows: List[dict]) -> dict:
    c = {k: sum(r["state"] == k for r in rows) for k in STATES}
    # 0 = all stable, 100 = all in tension
    pts = {"estable": 0, "vigilancia": 1, "tension": 2}
    valid = [pts[r["state"]] for r in rows if r["state"] in pts]
    return {**c, "index": round(100 * sum(valid) / (2 * len(valid))) if valid else None}


# --- 4. peers ------------------------------------------------------------------------------
def peers(bis: Dict[str, pd.DataFrame], mx_rate: Optional[float]) -> Optional[dict]:
    if not bis or "policy" not in bis or "cpi" not in bis:
        return None
    pol = bis["policy"].sort_values("TIME_PERIOD").groupby("REF_AREA").tail(1).set_index("REF_AREA")
    cpi = bis["cpi"].copy()
    common = cpi.groupby("REF_AREA")["TIME_PERIOD"].max().min()  # latest month available for every country
    cpi = cpi[cpi["TIME_PERIOD"] == common].set_index("REF_AREA")["OBS_VALUE"]
    rows = []
    for c in ["MX", "BR", "CL", "CO", "PE", "US"]:
        if c not in pol.index or c not in cpi.index:
            continue
        rate = mx_rate if (c == "MX" and mx_rate is not None) else float(pol.loc[c, "OBS_VALUE"])
        rows.append({"c": c, "rate": round(rate, 2), "cpi": round(float(cpi[c]), 2),
                     "real": round(rate - float(cpi[c]), 2), "rate_date": str(pol.loc[c, "TIME_PERIOD"])})
    rows.sort(key=lambda r: -r["real"])
    mx = next((r for r in rows if r["c"] == "MX"), None)
    return {"rows": rows, "cpi_month": common, "rate_date": max(r["rate_date"] for r in rows) if rows else None,
            "mx_rank": (rows.index(mx) + 1) if mx else None, "n": len(rows)}


# --- 5. peso or dollar? ------------------------------------------------------------------------
def dollar_box(d: Dict[str, pd.Series], days: int = 7) -> Optional[dict]:
    keys = ["usd_mxn_h10", "usd_brl", "usd_broad"]
    if any(k not in d or d[k] is None or d[k].empty for k in keys):
        return None
    end = min(d[k].index[-1] for k in keys)
    start = end - pd.Timedelta(days=days)
    out = {"end": end.strftime("%Y-%m-%d")}
    for k in keys:
        s = d[k]
        a = s[s.index <= start]
        if a.empty:
            return None
        out[k] = round(float((s[s.index <= end].iloc[-1] / a.iloc[-1] - 1) * 100), 2)
        out["start"] = a.index[-1].strftime("%Y-%m-%d")
    # share of the peso's move explained by broad dollar strength (simple ratio, not a regression)
    return out


def build(s: dict, d: Dict[str, pd.Series], bis: Dict[str, pd.DataFrame]) -> dict:
    rows = thermometer(s)
    return {
        "fx_rank": fx_rank(d["fix"]),
        "import_cost": import_cost(s["fx"]),
        "thermometer": rows,
        "thermo_score": thermometer_score(rows),
        "peers": peers(bis, s["policy"]["rate"]),
        "dollar": dollar_box(d),
    }

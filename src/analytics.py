"""
Metric engine: turns raw series into a Snapshot (plain dict, JSON-serialisable)
that the narrative, the magazine and the Markdown bulletin all read from.
"""

from __future__ import annotations

from datetime import date
from typing import Dict, Optional

import numpy as np
import pandas as pd

from config import (INFLATION_BAND, INFLATION_TARGET, NEUTRAL_REAL_RANGE, Z_ATYPICAL, Z_UNUSUAL,
                    ZSCORE_WINDOW_MONTHS, ZSCORE_WINDOW_WEEKS)


# --- helpers -----------------------------------------------------------------
def zscore_prior(changes: pd.Series, window: int) -> Optional[float]:
    """z of the latest change vs. the `window` observations BEFORE it (out-of-sample)."""
    clean = changes.dropna()
    if len(clean) < 12:
        return None
    prior = clean.iloc[:-1].tail(window)
    sd = float(prior.std(ddof=1))
    if not sd or np.isnan(sd):
        return None
    return (float(clean.iloc[-1]) - float(prior.mean())) / sd


def signal(z: Optional[float]) -> str:
    """'normal' | 'unusual' | 'atypical' | 'na'."""
    if z is None:
        return "na"
    a = abs(z)
    return "atypical" if a >= Z_ATYPICAL else "unusual" if a >= Z_UNUSUAL else "normal"


def asof_value(s: pd.Series, when: pd.Timestamp) -> Optional[float]:
    v = s.asof(when)
    return None if pd.isna(v) else float(v)


def pct(a: Optional[float], b: Optional[float]) -> Optional[float]:
    return None if a is None or b in (None, 0) else (a / b - 1.0) * 100.0


def _r(x: Optional[float], n: int = 2) -> Optional[float]:
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), n)


def monthly_last(s: pd.Series) -> pd.Series:
    return s.resample("MS").last().dropna()


def _series_payload(s: pd.Series, n: int) -> Dict[str, list]:
    s = s.tail(n)
    return {"dates": [d.strftime("%Y-%m-%d") for d in s.index], "values": [round(float(v), 4) for v in s.values]}


# --- blocks -------------------------------------------------------------------
def inflation_block(d: Dict[str, pd.Series]) -> dict:
    y, c = d["inflation_yoy"], d.get("core_yoy")
    last = y.index[-1]
    out = {
        "period": last.strftime("%Y-%m"),
        "yoy": _r(y.iloc[-1]), "yoy_prev": _r(y.iloc[-2]),
        "yoy_12m_ago": _r(asof_value(y, last - pd.DateOffset(months=12))),
        "mom": _r(d["inflation_mom"].iloc[-1]) if "inflation_mom" in d else None,
        "target": INFLATION_TARGET, "band": list(INFLATION_BAND),
        "chart": _series_payload(y, 37),
    }
    out["delta_pp"] = _r(out["yoy"] - out["yoy_prev"])
    # consecutive months moving in the same direction
    diffs = y.diff().dropna()
    streak, sign = 0, np.sign(diffs.iloc[-1])
    for v in reversed(diffs.values):
        if np.sign(v) == sign and sign != 0:
            streak += 1
        else:
            break
    out["streak"] = int(streak) * int(sign)
    if c is not None and len(c):
        out.update(core=_r(c.iloc[-1]), core_prev=_r(c.iloc[-2]), core_period=c.index[-1].strftime("%Y-%m"),
                   core_chart=_series_payload(c, 37))
        out["core_delta_pp"] = _r(out["core"] - out["core_prev"])
        out["core_mom"] = _r(d["core_mom"].iloc[-1]) if "core_mom" in d else None
    z = zscore_prior(y.diff(), ZSCORE_WINDOW_MONTHS)
    out.update(z=_r(z), signal=signal(z))
    return out


def expectations_block(d: Dict[str, pd.Series]) -> Optional[dict]:
    e = d.get("exp_12m")
    if e is None or not len(e):
        return None
    out = {"period": e.index[-1].strftime("%Y-%m"), "exp_12m": _r(e.iloc[-1]), "exp_12m_prev": _r(e.iloc[-2])}
    ec = d.get("exp_core_12m")
    if ec is not None and len(ec):
        out["exp_core_12m"] = _r(ec.iloc[-1])
    em = d.get("exp_12m_mean")
    if em is not None and len(em):
        out["exp_12m_mean"] = _r(em.iloc[-1])
    return out


def policy_block(d: Dict[str, pd.Series], exp: Optional[dict], infl: dict) -> dict:
    r = d["policy_rate"]
    today = r.index[-1]
    changes = r[r.diff().fillna(0) != 0]
    last_change_date = changes.index[-1] if len(changes) else None
    last_change_bp = _r((r.diff().loc[last_change_date]) * 100, 0) if last_change_date is not None else None
    r12 = asof_value(r, today - pd.DateOffset(months=12))
    out = {
        "date": today.strftime("%Y-%m-%d"), "rate": _r(r.iloc[-1]),
        "last_change_effective": last_change_date.strftime("%Y-%m-%d") if last_change_date is not None else None,
        "last_change_bp": last_change_bp,
        "chg_12m_bp": _r((r.iloc[-1] - r12) * 100, 0) if r12 is not None else None,
        "real_ex_post": _r(r.iloc[-1] - infl["yoy"]),
    }
    # Banxico's definition: policy rate minus the MEAN of 12-month expectations (median as fallback)
    e_key = "exp_12m_mean" if d.get("exp_12m_mean") is not None else "exp_12m"
    if exp:
        out["real_ex_ante"] = _r(r.iloc[-1] - (exp.get("exp_12m_mean") or exp["exp_12m"]))
        out["real_basis"] = "mean" if e_key == "exp_12m_mean" else "median"
        lo, hi = NEUTRAL_REAL_RANGE
        out["neutral_range"] = [lo, hi]
        ra = out["real_ex_ante"]
        out["stance"] = "restrictive" if ra > hi else "accommodative" if ra < lo else "neutral"
    fed = d.get("fed_upper")
    if fed is not None and len(fed):
        f_now = asof_value(fed, today)
        f12 = asof_value(fed, today - pd.DateOffset(months=12))
        out.update(fed_upper=_r(f_now), fed_lower=_r(f_now - 0.25),
                   spread_bp=_r((r.iloc[-1] - f_now) * 100, 0),
                   spread_12m_ago_bp=_r((r12 - f12) * 100, 0) if (r12 is not None and f12 is not None) else None)
        m_fed = monthly_last(fed).tail(37)
        out["fed_chart"] = _series_payload(m_fed, 37)
    out["chart"] = _series_payload(monthly_last(r), 37)
    # ex-ante real rate history (monthly): rate at month end minus survey expectation
    if d.get(e_key) is not None:
        e = d[e_key]
        rm = monthly_last(r).reindex(e.index, method="ffill")
        real = (rm - e).dropna()
        if out.get("real_ex_ante") is not None:  # current reading (today's rate, latest survey)
            real.loc[today] = out["real_ex_ante"]
        out["real_chart"] = _series_payload(real, 37)
        out["real_ex_ante_12m_ago"] = _r(asof_value(real, real.index[-1] - pd.DateOffset(months=12)))
    return out


def fx_block(d: Dict[str, pd.Series]) -> dict:
    s = d["fix"]
    t = s.index[-1]
    v = float(s.iloc[-1])
    w = asof_value(s, t - pd.Timedelta(days=7))
    m = asof_value(s, t - pd.DateOffset(months=1))
    y = asof_value(s, t - pd.DateOffset(months=12))
    last52 = s[s.index > t - pd.DateOffset(weeks=52)]
    weekly = s.resample("W-FRI").last().pct_change() * 100
    # latest weekly change computed point-to-point and appended for the z-score
    wk = weekly.dropna().iloc[:-1] if weekly.index[-1] >= t else weekly.dropna()
    wk = pd.concat([wk, pd.Series([pct(v, w)], index=[t])])
    z = zscore_prior(wk, ZSCORE_WINDOW_WEEKS)
    lo, hi = float(last52.min()), float(last52.max())
    # most recent prior week with a move at least as large in the same direction
    cur = pct(v, w) or 0.0
    prior = wk.iloc[:-1]
    same = prior[(np.sign(prior) == np.sign(cur)) & (prior.abs() >= abs(cur))] if cur else prior.iloc[0:0]
    largest_since = same.index[-1].strftime("%Y-%m-%d") if len(same) else None
    return {
        "date": t.strftime("%Y-%m-%d"), "value": round(v, 4), "value_1w_ago": round(w, 4) if w else None,
        "chg_1w_pct": _r(pct(v, w)), "chg_1m_pct": _r(pct(v, m)), "chg_12m_pct": _r(pct(v, y)),
        "low_52w": round(lo, 4), "high_52w": round(hi, 4),
        "low_52w_date": last52.idxmin().strftime("%Y-%m-%d"), "high_52w_date": last52.idxmax().strftime("%Y-%m-%d"),
        "pos_52w": _r((v - lo) / (hi - lo) * 100 if hi > lo else 50.0, 0),
        "z_1w": _r(z), "signal": signal(z),
        "largest_since": largest_since, "history_start": s.index[0].strftime("%Y-%m-%d"),
        "chart": _series_payload(last52, 400),
    }


def activity_block(d: Dict[str, pd.Series]) -> Optional[dict]:
    s = d.get("igae_sa")
    if s is None or len(s) < 15:
        return None
    mom = s.pct_change() * 100
    yoy = s.pct_change(12) * 100
    # 3-month average vs previous 3-month average (smooths single-month noise)
    a3 = s.rolling(3).mean()
    q_on_q = (a3 / a3.shift(3) - 1) * 100
    z = zscore_prior(mom, ZSCORE_WINDOW_MONTHS)
    return {
        "period": s.index[-1].strftime("%Y-%m"), "index": _r(s.iloc[-1], 1),
        "mom": _r(mom.iloc[-1]), "mom_prev": _r(mom.iloc[-2]), "yoy": _r(yoy.iloc[-1]), "yoy_prev": _r(yoy.iloc[-2]),
        "q3_vs_prev3": _r(q_on_q.iloc[-1]),
        "z": _r(z), "signal": signal(z),
        "chart": _series_payload(s, 37),
        "yoy_chart": _series_payload(yoy.dropna(), 37),
    }


def build_snapshot(d: Dict[str, pd.Series], run_date: date) -> dict:
    infl = inflation_block(d)
    exp = expectations_block(d)
    snap = {
        "run_date": run_date.isoformat(),
        "inflation": infl,
        "expectations": exp,
        "policy": policy_block(d, exp, infl),
        "fx": fx_block(d),
        "activity": activity_block(d),
    }
    return snap

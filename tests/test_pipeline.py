"""Regression tests for the issues found in the Nov-2026 audit."""
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import agenda  # noqa: E402
import analytics  # noqa: E402
import narrative  # noqa: E402
from config import SERIES  # noqa: E402


def test_igae_is_seasonally_adjusted_series():
    # 737121 = cifras originales; 737219 = desestacionalizada (INEGI feed list)
    assert SERIES["igae_sa"][1] == "737219"


def test_zscore_excludes_latest_point():
    rng = np.random.default_rng(0)
    s = pd.Series(np.r_[rng.normal(0, 1, 60), 6.0])
    z = analytics.zscore_prior(s, 60)
    in_sample = (6.0 - s.mean()) / s.std(ddof=1)
    assert z > in_sample  # including the shock in its own window shrinks z
    assert analytics.signal(z) == "atypical"


def test_signal_thresholds():
    assert analytics.signal(0.5) == "normal"
    assert analytics.signal(-1.6) == "unusual"
    assert analytics.signal(2.4) == "atypical"
    assert analytics.signal(None) == "na"


def test_fx_direction_wording():
    assert narrative.direction(1.2, "es", "se deprecia", "se aprecia", "estable", tol=0.25) == "se deprecia"
    assert narrative.direction(-1.2, "es", "se deprecia", "se aprecia", "estable", tol=0.25) == "se aprecia"
    assert narrative.direction(0.1, "es", "se deprecia", "se aprecia", "estable", tol=0.25) == "estable"


def test_agenda_is_valid():
    events, cov = agenda.load_events()
    assert events and cov >= events[-1]["date"]
    assert all(e["date"].weekday() < 5 for e in events)
    assert all(e["key"] for e in events)


def test_month_labels():
    assert narrative.month("2026-10", "es") == "oct-2026"
    assert narrative.month("2026-09", "en", long=True) == "September 2026"


def test_snapshot_from_cache_if_available():
    import sources
    data, _ = sources.fetch_all(offline=True)
    if "inflation_yoy" not in data:
        return
    snap = analytics.build_snapshot(data, date.today())
    assert snap["inflation"]["yoy"] is not None
    assert snap["fx"]["signal"] in {"normal", "unusual", "atypical", "na"}

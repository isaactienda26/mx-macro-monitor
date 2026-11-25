"""Publication calendar: one issue per week on Mondays, with dated exceptions (config/ediciones.yml)."""

from __future__ import annotations

from datetime import date, timedelta
from functools import lru_cache
from typing import Dict

import yaml

from config import ROOT

DIAS = {"es": ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"],
        "en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]}


@lru_cache(maxsize=1)
def _cfg() -> dict:
    path = ROOT / "config" / "ediciones.yml"
    d = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
    d = d or {}
    first = d.get("primer_lunes", date(2026, 11, 23))
    first = first if isinstance(first, date) else date.fromisoformat(str(first))
    exc: Dict[int, date] = {}
    for e in d.get("excepciones") or []:
        f = e["fecha"]
        exc[int(e["numero"])] = f if isinstance(f, date) else date.fromisoformat(str(f))
    return {"first": first, "exc": exc}


def issue_date(num: int) -> date:
    c = _cfg()
    return c["exc"].get(num, c["first"] + timedelta(days=7 * (num - 1)))


def edition_number(run: date) -> int:
    """Latest issue whose publication date is on or before the run date."""
    num = 1
    while issue_date(num + 1) <= run:
        num += 1
    return num


def is_publication_day(run: date) -> bool:
    return issue_date(edition_number(run)) == run


def weekday(d: date, lang: str) -> str:
    return DIAS[lang][d.weekday()]

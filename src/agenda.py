"""Release calendar: upcoming events and what was published in the past week."""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import List

import yaml

from config import AGENDA_FILE

logger = logging.getLogger(__name__)


def load_events() -> tuple[list, date]:
    raw = yaml.safe_load(AGENDA_FILE.read_text(encoding="utf-8"))
    events = []
    for e in raw.get("events", []):
        d = e["date"] if isinstance(e["date"], date) else date.fromisoformat(str(e["date"]))
        if d.weekday() >= 5:
            logger.warning("Evento en fin de semana, revisar: %s %s", d, e.get("es"))
        events.append({**e, "date": d})
    cov = raw.get("coverage_until")
    cov = cov if isinstance(cov, date) else date.fromisoformat(str(cov))
    return sorted(events, key=lambda x: (x["date"], x.get("time", ""))), cov


def window(run_date: date, run_time: str = "07:00", ahead_days: int = 14, back_days: int = 7) -> dict:
    events, cov = load_events()
    def published(e) -> bool:  # same-day releases before the 07:00 run count as published
        return e["date"] < run_date or (e["date"] == run_date and (e.get("time") or "99") <= run_time)

    future = [e for e in events if not published(e)]
    upcoming = [e for e in future if e["date"] <= run_date + timedelta(days=ahead_days)]
    if len(upcoming) < 3:  # quiet week: extend horizon so the slide is never empty
        upcoming = future[:5]
    recent = [e for e in events if published(e) and e["date"] >= run_date - timedelta(days=back_days)]
    if (cov - run_date).days < 30:
        logger.warning("La agenda cubre solo hasta %s: actualiza config/agenda.yml", cov)
    return {"upcoming": upcoming[:6], "recent": recent, "coverage_until": cov}

"""Query helpers that build Mongo filters for the frontend contract."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional


def _parse_csv(value: Optional[str]) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def _day_start(date_str: str) -> datetime:
    # Accept YYYY-MM-DD or full ISO
    if "T" in date_str:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    return datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)


def _day_end(date_str: str) -> datetime:
    if "T" in date_str:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    dt = datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
    return dt.replace(hour=23, minute=59, second=59, microsecond=999999)


def build_report_query(
    event_type: Optional[str] = None,
    state: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    q: Optional[str] = None,
) -> dict[str, Any]:
    clauses: list[dict[str, Any]] = []

    event_types = _parse_csv(event_type)
    if event_types:
        # Include common aliases used by collectors
        expanded = set(event_types)
        if "strong_wind" in expanded:
            expanded.add("strong_winds")
        if "flooding" in expanded:
            expanded.update({"flood", "floods"})
        clauses.append(
            {
                "$or": [
                    {"classification.event_type": {"$in": list(expanded)}},
                    {"event_type": {"$in": list(expanded)}},
                ]
            }
        )

    states = _parse_csv(state)
    if states:
        clauses.append(
            {
                "$or": [
                    {"location.state": {"$in": states}},
                    {"state": {"$in": states}},
                    # city fallback when state was never stored
                    {
                        "location.city": {
                            "$in": _cities_for_states(states),
                        }
                    },
                ]
            }
        )

    if status and status != "all":
        clauses.append(
            {
                "$or": [
                    {"verification.status": status},
                    {"verification_status": status},
                ]
            }
        )

    if date_from or date_to:
        ts_filter: dict[str, Any] = {}
        if date_from:
            ts_filter["$gte"] = _day_start(date_from).isoformat().replace("+00:00", "Z")
        if date_to:
            ts_filter["$lte"] = _day_end(date_to).isoformat().replace("+00:00", "Z")
        clauses.append({"timestamp": ts_filter})

    if q:
        regex = {"$regex": q, "$options": "i"}
        clauses.append(
            {
                "$or": [
                    {"text": regex},
                    {"cleaned_text": regex},
                    {"location.city": regex},
                    {"city": regex},
                    {"location.locality": regex},
                    {"location.state": regex},
                ]
            }
        )

    if not clauses:
        return {}
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def _cities_for_states(states: list[str]) -> list[str]:
    from api.mapper import CITY_TO_STATE

    wanted = {s.lower() for s in states}
    return [city for city, st in CITY_TO_STATE.items() if st.lower() in wanted]

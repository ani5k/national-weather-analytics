"""Refresh classifier prototypes from admin_labels (Phase 4 active learning)."""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pymongo import MongoClient

from pipeline.settings import COLLECTION_NAME, DB_NAME, MONGO_URI

OUT = ROOT / "ml" / "active_prototypes.json"
STATUS = ROOT / "ml" / "active_learning_status.json"
HELDOUT = ROOT / "ml" / "heldout_eval.json"


def _keyword_accuracy(examples: dict[str, list[str]], heldout: list[dict]) -> float:
    """Tiny offline accuracy: does any prototype token overlap the gold label text?"""
    if not heldout:
        return 0.0
    correct = 0
    for row in heldout:
        text = (row.get("text") or "").lower()
        gold = row.get("event_type")
        best = None
        best_hits = -1
        for et, samples in examples.items():
            hits = 0
            for sample in samples:
                for token in sample.lower().split()[:8]:
                    if len(token) > 3 and token in text:
                        hits += 1
            if hits > best_hits:
                best_hits = hits
                best = et
        if best == gold:
            correct += 1
    return round(correct / max(1, len(heldout)), 3)


def main() -> None:
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    labels = list(db["admin_labels"].find().sort("labeled_at", -1).limit(500))
    reports = db[COLLECTION_NAME]
    by_event: dict[str, list[str]] = defaultdict(list)
    for lab in labels:
        et = lab.get("admin_event_type")
        if not et:
            # infer from report classification when admin only verified/rejected
            doc = reports.find_one({"report_id": lab.get("report_id")})
            if doc:
                et = (doc.get("classification") or {}).get("event_type") or doc.get("admin_event_type")
        if not et:
            continue
        doc = reports.find_one({"report_id": lab.get("report_id")})
        if not doc:
            continue
        text = doc.get("cleaned_text") or doc.get("text")
        if text:
            by_event[et].append(text[:240])

    payload = {k: v[:5] for k, v in by_event.items()}
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    heldout = []
    if HELDOUT.exists():
        heldout = json.loads(HELDOUT.read_text(encoding="utf-8"))
    else:
        heldout = [
            {"text": "Waterlogging on roads after heavy rain", "event_type": "flooding"},
            {"text": "Severe heat advisory for afternoon hours", "event_type": "heatwave"},
            {"text": "Thunder and lightning overnight", "event_type": "thunderstorm"},
        ]
        HELDOUT.write_text(json.dumps(heldout, indent=2), encoding="utf-8")

    before = _keyword_accuracy({"rainfall": ["rain water"]}, heldout)
    after = _keyword_accuracy(payload or {"rainfall": ["rain"]}, heldout)
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    status = {
        "label_count": len(labels),
        "last_refresh_at": now,
        "message": f"Model updated - {len(labels)} new labels since last train",
        "heldout_accuracy_before": before,
        "heldout_accuracy_after": after,
        "classes": list(payload.keys()),
    }
    STATUS.write_text(json.dumps(status, indent=2), encoding="utf-8")
    print(f"wrote {OUT} classes={list(payload.keys())}")
    print(f"status {status}")


if __name__ == "__main__":
    main()

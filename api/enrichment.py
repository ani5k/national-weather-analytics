"""
Batch enrichment: clean → classify → embed → cluster → explainable trust → persist.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np

from credibility.scorer import score_and_label
from duplicate_detection.clustering import (
    DISTANCE_THRESHOLD_KM,
    SIMILARITY_THRESHOLD,
    TIME_THRESHOLD_MINUTES,
    are_duplicates,
    cluster_duplicate_reports,
    time_difference_minutes,
)
from duplicate_detection.location import distance_km
from duplicate_detection.similarity import text_similarity
from ml.event_classifier import classify_event
from pipeline.hashtags import extract_hashtags
from pipeline.languages import detect_languages
from preprocessing.cleaner import clean_text


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _coords(doc: dict) -> Optional[tuple[float, float]]:
    loc = doc.get("location") or {}
    lat = loc.get("latitude", loc.get("lat", doc.get("lat")))
    lng = loc.get("longitude", loc.get("lng", doc.get("lng")))
    try:
        if lat is None or lng is None:
            return None
        return float(lat), float(lng)
    except (TypeError, ValueError):
        return None


def _timestamp(doc: dict) -> Optional[str]:
    ts = doc.get("timestamp") or doc.get("created_at")
    if ts is None:
        return None
    if hasattr(ts, "isoformat"):
        value = ts.isoformat()
        return value if value.endswith("Z") else value + "Z"
    return str(ts)


def _parse_ts(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _is_official_source(doc: dict) -> bool:
    source = doc.get("source") or {}
    if isinstance(source, dict):
        platform = str(source.get("platform") or "").lower()
        stype = str(source.get("type") or "").lower()
    else:
        platform = str(source).lower()
        stype = ""
    return (
        doc.get("is_official_anchor")
        or platform in {"news_rss", "imd", "open-meteo", "openweathermap"}
        or stype in {"news", "api", "government"}
    )


def attach_official_anchor(doc: dict, pool: list[dict], hours: float = 24.0) -> Optional[str]:
    """Link citizen/social report to nearest official IMD/RSS bulletin."""
    if _is_official_source(doc):
        return None
    coords = _coords(doc)
    ts = _parse_ts(_timestamp(doc))
    if not coords or not ts:
        return None
    best_id = None
    best_dist = 999.0
    for other in pool:
        if not _is_official_source(other):
            continue
        ocoords = _coords(other)
        ots = _parse_ts(_timestamp(other))
        if not ocoords or not ots:
            continue
        if abs((ts - ots).total_seconds()) > hours * 3600:
            continue
        dist = distance_km(coords, ocoords)
        if dist <= 80 and dist < best_dist:
            best_dist = dist
            best_id = other.get("report_id")
    if best_id:
        doc["official_anchor_id"] = best_id
        doc["official_anchor_distance_km"] = round(best_dist, 2)
    return best_id


def find_official_nearby(doc: dict, pool: list[dict], hours: float = 24.0) -> bool:
    """Phase 4: nearby official/RSS anchor in time+space."""
    coords = _coords(doc)
    ts = _parse_ts(_timestamp(doc))
    if not coords or not ts:
        return False
    for other in pool:
        if other is doc or not _is_official_source(other):
            continue
        ocoords = _coords(other)
        ots = _parse_ts(_timestamp(other))
        if not ocoords or not ots:
            continue
        if abs((ts - ots).total_seconds()) > hours * 3600:
            continue
        if distance_km(coords, ocoords) <= 50:
            return True
    return False


def media_integrity_penalty(doc: dict) -> int:
    """Phase 3 media forensics lite."""
    from media.forensics import analyze_media

    analysis = analyze_media(doc)
    doc["media_forensics"] = analysis
    doc["media_forensics_detail"] = analysis.get("detail")
    return int(analysis.get("penalty") or 0)


def _build_duplicate_matrix(docs: list[dict], embeddings: list[Any]) -> np.ndarray:
    n = len(docs)
    matrix = np.ones((n, n), dtype=float)
    np.fill_diagonal(matrix, 0.0)

    for i in range(n):
        for j in range(i + 1, n):
            sim = text_similarity(embeddings[i], embeddings[j])
            coords_a, coords_b = _coords(docs[i]), _coords(docs[j])
            dist = (
                distance_km(coords_a, coords_b)
                if coords_a and coords_b
                else float("inf")
            )
            ts_a, ts_b = _timestamp(docs[i]), _timestamp(docs[j])
            if not ts_a or not ts_b:
                time_diff = float("inf")
            else:
                try:
                    time_diff = time_difference_minutes(ts_a, ts_b)
                except ValueError:
                    time_diff = float("inf")

            if are_duplicates(sim, dist, time_diff):
                matrix[i, j] = 0.0
                matrix[j, i] = 0.0
            else:
                soft = 1.0
                if (
                    sim >= SIMILARITY_THRESHOLD * 0.9
                    and dist <= DISTANCE_THRESHOLD_KM * 1.5
                    and time_diff <= TIME_THRESHOLD_MINUTES * 1.5
                ):
                    soft = 0.6
                matrix[i, j] = soft
                matrix[j, i] = soft
    return matrix


def ml_verification_status(score: int) -> str:
    if score >= 60:
        return "verified"
    if score < 30:
        return "rejected"
    return "pending"


def enrich_documents(docs: list[dict], apply_ml_status: bool = True) -> list[dict]:
    if not docs:
        return docs

    from duplicate_detection.embeddings import get_embedding

    embeddings = []
    for doc in docs:
        text = doc.get("text") or ""
        cleaned_text = clean_text(text)
        doc["cleaned_text"] = cleaned_text
        doc["languages"] = detect_languages(text)
        if not doc.get("hashtags"):
            doc["hashtags"] = extract_hashtags(text)

        # Re-classify free text when method isn't high-confidence API code
        method = (doc.get("classification") or {}).get("method")
        if method != "ingest_api_code":
            event, conf = classify_event(text)
            classification = doc.get("classification") or {}
            # Don't overwrite admin-forced labels
            if not doc.get("admin_event_type"):
                classification.update(
                    {
                        "event_type": event,
                        "event_types": [event],
                        "confidence": conf,
                        "method": "nlp_classifier",
                        "categorized_at": _now_iso(),
                    }
                )
                doc["classification"] = classification

        embeddings.append(get_embedding(cleaned_text) if cleaned_text else None)

    if len(docs) == 1:
        labels = np.array([0])
    else:
        matrix = _build_duplicate_matrix(docs, embeddings)
        labels = cluster_duplicate_reports(matrix)

    group_sizes: dict[int, int] = {}
    for label in labels:
        group_sizes[int(label)] = group_sizes.get(int(label), 0) + 1

    enriched_at = _now_iso()
    for idx, doc in enumerate(docs):
        label = int(labels[idx])
        size = group_sizes.get(label, 1)
        report_key = doc.get("report_id") or str(doc.get("_id") or idx)
        group_id = f"GRP-{label}" if size > 1 else f"GRP-SINGLE-{report_key}"
        corroboration = max(0, size - 1)

        doc["duplicate_detection"] = {
            "group_id": group_id,
            "group_size": size,
            "corroboration_count": corroboration,
            "is_duplicate": size > 1,
            "method": "embedding_geo_time_dbscan",
            "thresholds": {
                "similarity": SIMILARITY_THRESHOLD,
                "distance_km": DISTANCE_THRESHOLD_KM,
                "time_minutes": TIME_THRESHOLD_MINUTES,
            },
            "enriched_at": enriched_at,
        }
        doc["duplicate_group_id"] = group_id

        official_id = attach_official_anchor(doc, docs)
        official = bool(official_id) or find_official_nearby(doc, docs)
        penalty = media_integrity_penalty(doc)
        credibility = score_and_label(
            doc,
            corroboration_count=corroboration,
            official_nearby=official,
            media_penalty=penalty,
            official_anchor_id=doc.get("official_anchor_id"),
        )
        doc["credibility"] = {**credibility, "scored_at": enriched_at}
        doc["credibility_score"] = credibility["score"]
        doc["credibility_reasons"] = credibility.get("reasons") or []
        doc["credibility_factors"] = credibility.get("factors") or []

        # risk + impact overlay (Phase 4)
        from impact.population import estimate_people_at_risk

        event = (doc.get("classification") or {}).get("event_type") or "unknown"
        city = (doc.get("location") or {}).get("city") or doc.get("city") or "Unknown"
        severity = "low"
        if event in {"flooding", "thunderstorm"} and credibility["score"] >= 60:
            severity = "high"
        elif event in {"heatwave", "dust_storm", "strong_wind"} and credibility["score"] >= 50:
            severity = "moderate"
        impact = estimate_people_at_risk(city, event, severity, group_size=size)
        doc["risk"] = {
            "severity": severity,
            "score": credibility["score"],
            "event_type": event,
            "group_size": size,
            **impact,
        }

        if apply_ml_status:
            verification = doc.get("verification") or {}
            if verification.get("verified_by") == "admin" or doc.get("verified_by") == "admin":
                doc["updated_at"] = enriched_at
                continue
            status = ml_verification_status(credibility["score"])
            doc["verification"] = {
                "status": status,
                "verified_by": "ml",
                "verified_at": enriched_at,
            }
            doc["verification_status"] = status
            doc["verified_by"] = "ml"

        doc["updated_at"] = enriched_at

    return docs


def enrich_and_persist(collection, limit: int = 500, apply_ml_status: bool = True) -> dict:
    docs = list(collection.find().sort("timestamp", -1).limit(limit))
    if not docs:
        return {"processed": 0, "updated": 0, "groups": 0}

    enrich_documents(docs, apply_ml_status=apply_ml_status)

    updated = 0
    groups = set()
    for doc in docs:
        payload = {
            "cleaned_text": doc.get("cleaned_text"),
            "hashtags": doc.get("hashtags"),
            "classification": doc.get("classification"),
            "duplicate_detection": doc.get("duplicate_detection"),
            "duplicate_group_id": doc.get("duplicate_group_id"),
            "credibility": doc.get("credibility"),
            "credibility_score": doc.get("credibility_score"),
            "credibility_reasons": doc.get("credibility_reasons"),
            "credibility_factors": doc.get("credibility_factors"),
            "official_anchor_id": doc.get("official_anchor_id"),
            "official_anchor_distance_km": doc.get("official_anchor_distance_km"),
            "media_forensics": doc.get("media_forensics"),
            "media_forensics_detail": doc.get("media_forensics_detail"),
            "languages": doc.get("languages"),
            "risk": doc.get("risk"),
            "updated_at": doc.get("updated_at"),
        }
        if apply_ml_status and doc.get("verification"):
            payload["verification"] = doc["verification"]
            payload["verification_status"] = doc.get("verification_status")
            payload["verified_by"] = doc.get("verified_by")

        collection.update_one({"_id": doc["_id"]}, {"$set": payload})
        updated += 1
        gid = doc.get("duplicate_group_id")
        if gid:
            groups.add(gid)

    return {"processed": len(docs), "updated": updated, "groups": len(groups)}


def process_single_document(collection, doc: dict, apply_ml_status: bool = True) -> dict:
    """Worker path: enrich one new doc against a recent neighborhood window."""
    neighborhood = list(collection.find().sort("timestamp", -1).limit(200))
    # Ensure current doc is included
    ids = {d.get("report_id") for d in neighborhood}
    if doc.get("report_id") not in ids:
        neighborhood.insert(0, doc)
    enrich_documents(neighborhood, apply_ml_status=apply_ml_status)
    target = next(
        (d for d in neighborhood if d.get("report_id") == doc.get("report_id")),
        neighborhood[0],
    )
    payload = {
        "cleaned_text": target.get("cleaned_text"),
        "hashtags": target.get("hashtags"),
        "classification": target.get("classification"),
        "duplicate_detection": target.get("duplicate_detection"),
        "duplicate_group_id": target.get("duplicate_group_id"),
        "credibility": target.get("credibility"),
        "credibility_score": target.get("credibility_score"),
        "credibility_reasons": target.get("credibility_reasons"),
        "credibility_factors": target.get("credibility_factors"),
        "official_anchor_id": target.get("official_anchor_id"),
        "official_anchor_distance_km": target.get("official_anchor_distance_km"),
        "media_forensics": target.get("media_forensics"),
        "media_forensics_detail": target.get("media_forensics_detail"),
        "languages": target.get("languages"),
        "risk": target.get("risk"),
        "verification": target.get("verification"),
        "verification_status": target.get("verification_status"),
        "verified_by": target.get("verified_by"),
        "updated_at": target.get("updated_at"),
    }
    if target.get("_id"):
        collection.update_one({"_id": target["_id"]}, {"$set": payload})
    else:
        collection.update_one({"report_id": target.get("report_id")}, {"$set": payload})
    return target

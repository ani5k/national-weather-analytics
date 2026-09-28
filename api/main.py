"""
FastAPI application for the National Weather Analytics Platform.

Run:
    python -m uvicorn api.main:app --reload --port 8000
"""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pymongo import ReturnDocument

from api.config import (
    ACTIVE_ALERT_EVENT_TYPES,
    ACTIVE_ALERT_MIN_CREDIBILITY,
    CORS_ORIGINS,
)
from api.db import ensure_indexes, get_collection
from api.enrichment import enrich_and_persist, process_single_document
from api.mapper import doc_to_report
from api.queries import build_report_query
from api.schemas import (
    CitizenReportCreate,
    EventCluster,
    ModelStatus,
    Report,
    ReportStatusUpdate,
    StatsResponse,
)
from ml.event_classifier import classify_event
from pipeline.bus import publish_raw
from pipeline.hashtags import extract_hashtags
from pipeline.schema import build_report
from pipeline.settings import city_meta

MODEL_STATUS_PATH = Path(__file__).resolve().parents[1] / "ml" / "active_learning_status.json"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        ensure_indexes()
    except Exception as exc:  # noqa: BLE001
        print(f"Warning: could not ensure indexes: {exc}")
    yield


app = FastAPI(
    title="Weather Collector API",
    version="2.1.0",
    description="National weather big-data analytics backend",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "version": "2.1.0"}


@app.get("/reports", response_model=list[Report])
def list_reports(
    event_type: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    limit: int = Query(2000, ge=1, le=5000),
):
    collection = get_collection()
    mongo_query = build_report_query(
        event_type=event_type,
        state=state,
        status=status,
        date_from=date_from,
        date_to=date_to,
        q=q,
    )
    docs = list(collection.find(mongo_query).sort("timestamp", -1).limit(limit))
    return [doc_to_report(doc) for doc in docs]


@app.post("/reports", response_model=Report, status_code=201)
def create_citizen_report(body: CitizenReportCreate):
    collection = get_collection()
    now = datetime.now(timezone.utc)
    state, lat, lng = city_meta(body.city)
    lat = body.lat if body.lat is not None else lat
    lng = body.lng if body.lng is not None else lng
    state = body.state or state

    text = body.text
    hashtags = body.hashtags or extract_hashtags(text)
    if body.event_type:
        event, confidence = body.event_type, 0.9
        method = "citizen_provided"
    else:
        event, confidence = classify_event(text)
        method = "nlp_classifier"

    report_id = f"CIT_{now.strftime('%Y%m%d%H%M%S')}_{body.city[:3].upper()}"
    ts = now.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    doc = build_report(
        report_id=report_id,
        text=text,
        platform="citizen_report",
        source_type="citizen",
        city=body.city,
        state=state,
        event_type=event,
        timestamp=ts,
        timestamp_hour=now.replace(minute=0, second=0, microsecond=0).isoformat(),
        lat=lat,
        lng=lng,
        locality=body.locality,
        confidence=confidence,
        hashtags=hashtags,
        media_url=body.media_url,
        user_id=body.user_id,
    )
    doc["classification"]["method"] = method
    collection.insert_one(doc)
    publish_raw(doc)
    process_single_document(collection, doc, apply_ml_status=True)
    stored = collection.find_one({"report_id": report_id})
    return doc_to_report(stored or doc)


@app.get("/stats", response_model=StatsResponse)
def get_stats():
    collection = get_collection()
    docs = list(collection.find({}))
    if not docs:
        return StatsResponse(total=0, verifiedPct=0, activeAlerts=0, mostAffectedState="—")

    reports = [doc_to_report(doc) for doc in docs]
    total = len(reports)
    verified = sum(1 for r in reports if r["verification_status"] == "verified")
    active = sum(
        1
        for r in reports
        if r["event_type"] in ACTIVE_ALERT_EVENT_TYPES
        and r["credibility_score"] > ACTIVE_ALERT_MIN_CREDIBILITY
    )
    by_state: dict[str, int] = {}
    for r in reports:
        by_state[r["state"] or "Unknown"] = by_state.get(r["state"] or "Unknown", 0) + 1
    top_state = max(by_state.items(), key=lambda item: item[1])[0] if by_state else "—"
    return StatsResponse(
        total=total,
        verifiedPct=round((verified / total) * 100) if total else 0,
        activeAlerts=active,
        mostAffectedState=top_state,
    )


def _build_event_clusters(limit: int = 100) -> list[EventCluster]:
    collection = get_collection()
    docs = list(collection.find({}).sort("timestamp", -1).limit(3000))
    groups: dict[str, list[dict]] = {}
    for doc in docs:
        report = doc_to_report(doc)
        gid = report.get("duplicate_group_id") or f"SOLO-{report['id']}"
        groups.setdefault(gid, []).append(report)

    clusters: list[EventCluster] = []
    for gid, members in groups.items():
        if not members:
            continue
        lat = sum(m["lat"] for m in members) / len(members)
        lng = sum(m["lng"] for m in members) / len(members)
        avg_cred = round(sum(m["credibility_score"] for m in members) / len(members))
        trust_01 = round(avg_cred / 100.0, 2)
        sources = sorted({m["source"] for m in members})
        media_count = sum(1 for m in members if m.get("media_url"))
        breakdown = {"verified": 0, "pending": 0, "rejected": 0}
        for m in members:
            breakdown[m["verification_status"]] = breakdown.get(m["verification_status"], 0) + 1
        top_event = max(
            {m["event_type"] for m in members},
            key=lambda e: sum(1 for m in members if m["event_type"] == e),
        )
        severity = "low"
        if top_event in {"flooding", "thunderstorm"} and (len(members) >= 2 or avg_cred >= 60):
            severity = "high"
        elif avg_cred >= 50 or len(members) >= 2:
            severity = "moderate"
        tags: list[str] = []
        for m in members:
            for t in m.get("hashtags") or []:
                if t not in tags:
                    tags.append(t)
        langs: list[str] = []
        for m in members:
            for lang in m.get("languages") or []:
                if lang not in langs:
                    langs.append(lang)
        people = max((m.get("people_at_risk") or 0) for m in members)
        hospitals = max((m.get("hospitals_nearby") or 0) for m in members)
        roads = max((m.get("major_roads_nearby") or 0) for m in members)
        if people <= 0:
            from impact.population import estimate_people_at_risk

            impact = estimate_people_at_risk(
                members[0]["city"], top_event, severity, group_size=len(members)
            )
            people = impact["people_at_risk"]
            hospitals = impact["hospitals_nearby"]
            roads = impact["major_roads_nearby"]
        anchors = [m.get("official_anchor_id") for m in members if m.get("official_anchor_id")]
        official_anchor_id = anchors[0] if anchors else None
        latest = max(members, key=lambda m: m["timestamp"])
        clusters.append(
            EventCluster(
                id=gid,
                event_type=top_event,
                city=latest["city"],
                state=latest["state"],
                lat=lat,
                lng=lng,
                report_count=len(members),
                avg_credibility=avg_cred,
                trust_01=trust_01,
                sources=sources,
                source_count=len(sources),
                media_count=media_count,
                verification_breakdown=breakdown,
                risk_severity=severity,
                people_at_risk=people,
                hospitals_nearby=hospitals,
                major_roads_nearby=roads,
                latest_timestamp=latest["timestamp"],
                sample_text=latest["text"][:180],
                hashtags=tags[:12],
                member_ids=[m["id"] for m in members][:40],
                official_anchor_id=official_anchor_id,
                languages=langs,
            )
        )

    clusters.sort(key=lambda c: (c.report_count, c.avg_credibility), reverse=True)
    return clusters[:limit]


@app.get("/events", response_model=list[EventCluster])
def list_events(limit: int = Query(100, ge=1, le=500)):
    """Event-level corroboration clusters for the Events view."""
    return _build_event_clusters(limit=limit)


@app.get("/model-status", response_model=ModelStatus)
def model_status():
    collection = get_collection()
    label_count = collection.database["admin_labels"].count_documents({})
    if MODEL_STATUS_PATH.exists():
        try:
            data = json.loads(MODEL_STATUS_PATH.read_text(encoding="utf-8"))
            return ModelStatus(
                label_count=int(data.get("label_count", label_count)),
                last_refresh_at=data.get("last_refresh_at"),
                message=data.get("message")
                or f"Model updated — {label_count} admin labels available",
                heldout_accuracy_before=data.get("heldout_accuracy_before"),
                heldout_accuracy_after=data.get("heldout_accuracy_after"),
            )
        except Exception:  # noqa: BLE001
            pass
    return ModelStatus(
        label_count=label_count,
        last_refresh_at=None,
        message=f"{label_count} admin labels since last prototype refresh (run ml/refresh_prototypes.py)",
        heldout_accuracy_before=None,
        heldout_accuracy_after=None,
    )


@app.get("/stream/stats")
async def stream_stats():
    """SSE live counts for dashboard (report total + cluster count)."""

    async def event_generator():
        last_payload = None
        while True:
            try:
                collection = get_collection()
                total = collection.count_documents({})
                clusters = len(_build_event_clusters(limit=200))
                payload = {"total_reports": total, "event_clusters": clusters}
                if payload != last_payload:
                    yield f"data: {json.dumps(payload)}\n\n"
                    last_payload = payload
                else:
                    yield ": keepalive\n\n"
            except Exception as exc:  # noqa: BLE001
                yield f"data: {json.dumps({'error': str(exc)})}\n\n"
            await asyncio.sleep(5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.patch("/reports/{report_id}", response_model=Report)
def patch_report(report_id: str, body: ReportStatusUpdate):
    collection = get_collection()
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    update = {
        "verification.status": body.verification_status,
        "verification.verified_by": body.verified_by,
        "verification.verified_at": now,
        "verification_status": body.verification_status,
        "verified_by": body.verified_by,
        "updated_at": now,
    }
    if body.admin_event_type:
        update["admin_event_type"] = body.admin_event_type
        update["classification.event_type"] = body.admin_event_type
        update["classification.event_types"] = [body.admin_event_type]
        update["classification.method"] = "admin_label"

    result = collection.find_one_and_update(
        {"$or": [{"report_id": report_id}, {"id": report_id}]},
        {"$set": update},
        return_document=ReturnDocument.AFTER,
    )
    if result is None:
        try:
            result = collection.find_one_and_update(
                {"_id": ObjectId(report_id)},
                {"$set": update},
                return_document=ReturnDocument.AFTER,
            )
        except InvalidId:
            result = None
    if result is None:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")

    # Active-learning label store
    collection.database["admin_labels"].insert_one(
        {
            "report_id": report_id,
            "verification_status": body.verification_status,
            "admin_event_type": body.admin_event_type,
            "labeled_at": now,
        }
    )
    return doc_to_report(result)


@app.post("/enrich")
def enrich_reports(
    limit: int = Query(500, ge=1, le=3000),
    apply_ml_status: bool = Query(True),
):
    collection = get_collection()
    summary = enrich_and_persist(collection, limit=limit, apply_ml_status=apply_ml_status)
    return {"ok": True, **summary}

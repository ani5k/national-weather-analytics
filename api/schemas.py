"""Pydantic models for API responses and requests."""

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


VerificationStatus = Literal["verified", "pending", "rejected"]
VerifiedBy = Literal["ml", "admin"]


class Report(BaseModel):
    id: str
    text: str
    source: str
    event_type: str
    city: str
    state: str
    locality: Optional[str] = None
    lat: float
    lng: float
    timestamp: str
    credibility_score: int = Field(ge=0, le=100)
    verification_status: VerificationStatus
    verified_by: str
    media_url: Optional[str] = None
    duplicate_group_id: Optional[str] = None
    hashtags: list[str] = Field(default_factory=list)
    credibility_reasons: list[str] = Field(default_factory=list)
    credibility_factors: list[dict[str, Any]] = Field(default_factory=list)
    risk_severity: Optional[str] = None
    people_at_risk: Optional[int] = None
    hospitals_nearby: Optional[int] = None
    major_roads_nearby: Optional[int] = None
    official_anchor_id: Optional[str] = None
    media_forensics_detail: Optional[str] = None
    languages: list[str] = Field(default_factory=list)


class CitizenReportCreate(BaseModel):
    text: str = Field(min_length=5, max_length=2000)
    city: str
    state: Optional[str] = None
    locality: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    event_type: Optional[str] = None
    media_url: Optional[str] = None
    hashtags: Optional[list[str]] = None
    user_id: Optional[str] = None


class ReportStatusUpdate(BaseModel):
    verification_status: VerificationStatus
    verified_by: VerifiedBy = "admin"
    admin_event_type: Optional[str] = None


class StatsResponse(BaseModel):
    total: int
    verifiedPct: int
    activeAlerts: int
    mostAffectedState: str


class EventCluster(BaseModel):
    id: str
    event_type: str
    city: str
    state: str
    lat: float
    lng: float
    report_count: int
    avg_credibility: int
    trust_01: float
    sources: list[str]
    source_count: int
    media_count: int
    verification_breakdown: dict[str, int]
    risk_severity: str
    people_at_risk: int
    hospitals_nearby: int
    major_roads_nearby: int
    latest_timestamp: str
    sample_text: str
    hashtags: list[str]
    member_ids: list[str]
    official_anchor_id: Optional[str] = None
    languages: list[str] = Field(default_factory=list)


class ModelStatus(BaseModel):
    label_count: int
    last_refresh_at: Optional[str] = None
    message: str
    heldout_accuracy_before: Optional[float] = None
    heldout_accuracy_after: Optional[float] = None

from typing import Any

from pydantic import BaseModel, Field


class AnomalyResponse(BaseModel):
    anomaly_id: str
    anomaly_type: str
    severity: str
    title: str
    description: str
    records: dict[str, Any]
    expected: dict[str, Any]
    observed: dict[str, Any]
    recommendation: str
    detected_at: str


class AnomalyScanResponse(BaseModel):
    total_anomalies: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    anomalies: list[AnomalyResponse]


class AnomalySummaryResponse(BaseModel):
    total_anomalies: int
    by_severity: dict[str, int]
    by_type: dict[str, int]
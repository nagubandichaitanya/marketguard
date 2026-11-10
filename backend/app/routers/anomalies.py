from collections import Counter

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.services.anomaly_detector import scan_anomalies
from backend.app.schemas.anomaly import (
    AnomalyScanResponse,
    AnomalySummaryResponse,
)

router = APIRouter(
    prefix="/api/v1/anomalies",
    tags=["Anomaly Detection"],
)


@router.post("/scan", response_model=AnomalyScanResponse)
def run_anomaly_scan(db: Session = Depends(get_db)):
    """Run all five anomaly detection rules."""

    try:
        anomalies = scan_anomalies(db)

        severity_counts = Counter(
            anomaly["severity"] for anomaly in anomalies
        )

        return {
            "total_anomalies": len(anomalies),
            "critical_count": severity_counts.get("CRITICAL", 0),
            "high_count": severity_counts.get("HIGH", 0),
            "medium_count": severity_counts.get("MEDIUM", 0),
            "low_count": severity_counts.get("LOW", 0),
            "anomalies": anomalies,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Anomaly scan failed: {str(exc)}",
        )


@router.get("/summary", response_model=AnomalySummaryResponse)
def get_anomaly_summary(db: Session = Depends(get_db)):
    """Return anomaly counts grouped by severity and type."""

    try:
        anomalies = scan_anomalies(db)

        severity_counts = Counter(
            anomaly["severity"] for anomaly in anomalies
        )

        type_counts = Counter(
            anomaly["anomaly_type"] for anomaly in anomalies
        )

        return {
            "total_anomalies": len(anomalies),
            "by_severity": dict(severity_counts),
            "by_type": dict(type_counts),
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Anomaly summary failed: {str(exc)}",
        )
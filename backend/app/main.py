
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.app.config import settings
from backend.app.routers.anomalies import router as anomalies_router

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "MarketGuard - Marketplace seller operations, "
        "compliance, payout intelligence, and anomaly detection API."
    ),
)


@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "ok",
        "service": settings.app_name,
    }


app.include_router(anomalies_router)

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"

app.mount(
    "/",
    StaticFiles(directory=str(FRONTEND_DIR), html=True),
    name="frontend",
)

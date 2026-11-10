from fastapi import FastAPI

from backend.app.config import settings

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Marketplace seller operations, compliance, and payout intelligence API.",
)


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    """Basic process health check; database health will be added after DB setup."""
    return {"status": "ok", "service": settings.app_name}

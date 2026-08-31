from fastapi import APIRouter
from app.config import settings

router = APIRouter()


@router.get("/health")
def health():
    return {
        "status": "ok",
        "service": "Humana Ahead API",
        "openai_configured": bool(settings.openai_api_key),
        "model": settings.openai_model,
        "data_as_of": settings.data_as_of,
        "mock_ai": settings.use_mock_ai,
        "temperature": settings.openai_temperature,
        "prompt_version": settings.prompt_version,
        "scan_concurrency": settings.scan_concurrency,
        "max_scan_batch": settings.max_scan_batch,
    }

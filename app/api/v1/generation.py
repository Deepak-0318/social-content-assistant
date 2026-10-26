from fastapi import APIRouter, HTTPException

from app.ai.content_generation import (
    ContentGenerationService,
    MediaAnalysisNotFoundError,
    MediaNotFoundError,
)
from app.ai.providers.mock import MockAIProvider
from app.schemas.content_generation import (
    ContentGenerationRequest,
    ContentGenerationResponse,
)


router = APIRouter(prefix="/generation", tags=["Content Generation"])

service = ContentGenerationService(provider=MockAIProvider())


@router.post(
    "/generate",
    response_model=ContentGenerationResponse,
)
async def generate_content(
    request: ContentGenerationRequest,
) -> ContentGenerationResponse:
    try:
        return await service.generate(request)

    except MediaNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except MediaAnalysisNotFoundError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc
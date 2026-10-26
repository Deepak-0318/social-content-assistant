import json
from pathlib import Path
from uuid import UUID

from app.ai.providers.base import AIProvider, ProviderRequest
from app.schemas.content_generation import (
    ContentGenerationRequest,
    ContentGenerationResponse,
    GeneratedContent,
)


UPLOAD_DIR = Path("storage/uploads")
PROCESSED_DIR = Path("storage/processed")


class MediaNotFoundError(Exception):
    pass


class MediaAnalysisNotFoundError(Exception):
    pass


def _resolve_upload(upload_id: str) -> tuple[str, Path]:
    try:
        canonical_id = str(UUID(upload_id))
    except ValueError as exc:
        raise MediaNotFoundError("Invalid upload ID.") from exc

    root = UPLOAD_DIR.resolve()
    matches = [
        path
        for path in root.glob(f"{canonical_id}.*")
        if path.is_file() and not path.is_symlink()
    ]

    if len(matches) != 1:
        raise MediaNotFoundError("Uploaded media was not found.")

    source = matches[0].resolve()
    if source.parent != root:
        raise MediaNotFoundError("Uploaded media was not found.")

    return canonical_id, source


def _load_media_summary(upload_id: str, source: Path) -> tuple[str, str]:
    extension = source.suffix.lower()

    if extension in {".jpg", ".jpeg", ".png", ".webp"}:
        media_type = "image"
    elif extension in {".mp4", ".mov"}:
        media_type = "video"
    else:
        raise MediaNotFoundError("Unsupported media format.")

    analysis_file = PROCESSED_DIR / upload_id / "analysis.json"

    if not analysis_file.is_file() or analysis_file.is_symlink():
        raise MediaAnalysisNotFoundError(
            "Analyze this upload before generating content."
        )

    try:
        analysis = json.loads(analysis_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MediaAnalysisNotFoundError(
            "Media analysis could not be read."
        ) from exc

    # This summary uses metadata only; it does not infer what the media depicts.
    if media_type == "image":
        summary = (
            f"Image metadata: {analysis.get('width')}x"
            f"{analysis.get('height')}, "
            f"format {analysis.get('source_format', 'unknown')}."
        )
    else:
        summary = (
            f"Video metadata: duration "
            f"{analysis.get('duration_seconds', 'unknown')} seconds, "
            f"resolution {analysis.get('width')}x"
            f"{analysis.get('height')}, "
            f"audio available: {analysis.get('audio_available', False)}."
        )

    return media_type, summary


class ContentGenerationService:
    def __init__(self, provider: AIProvider):
        self.provider = provider

    async def generate(
        self,
        request: ContentGenerationRequest,
    ) -> ContentGenerationResponse:
        canonical_id, source = _resolve_upload(request.upload_id)
        media_type, media_summary = _load_media_summary(
            canonical_id,
            source,
        )

        provider_request = ProviderRequest(
            platform=request.platform,
            tone=request.tone,
            language=request.language,
            media_type=media_type,
            media_summary=media_summary,
            user_instructions=request.user_instructions,
        )

        generated = await self.provider.generate(provider_request)

        return ContentGenerationResponse(
            upload_id=canonical_id,
            platform=request.platform,
            tone=request.tone,
            language=request.language,
            provider="mock",
            content=GeneratedContent(
                caption=generated.caption,
                hashtags=generated.hashtags,
                description=generated.description,
            ),
        )
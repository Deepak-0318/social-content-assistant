import shutil
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.schemas.media_analysis import MediaAnalysisResponse
from app.storage.image_analysis import (
    MediaProcessingError,
    analyze_image,
)
from app.storage.video_processing import process_video


router = APIRouter(prefix="/media", tags=["Media Analysis"])

UPLOAD_DIR = Path("storage/uploads")
PROCESSED_DIR = Path("storage/processed")


def _find_upload(upload_id: str) -> Path:
    try:
        canonical_id = str(UUID(upload_id))
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid upload ID.",
        ) from exc

    root = UPLOAD_DIR.resolve()

    matches = [
        path for path in root.glob(f"{canonical_id}.*")
        if path.is_file() and not path.is_symlink()
    ]

    if len(matches) != 1:
        raise HTTPException(
            status_code=404,
            detail="Uploaded media was not found.",
        )

    source = matches[0].resolve()

    if source.parent != root:
        raise HTTPException(
            status_code=404,
            detail="Uploaded media was not found.",
        )

    return source


@router.post(
    "/{upload_id}/analyze",
    response_model=MediaAnalysisResponse,
)
def analyze_uploaded_media(upload_id: str) -> MediaAnalysisResponse:
    source = _find_upload(upload_id)
    extension = source.suffix.lower()

    if extension not in {
        ".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov"
    }:
        raise HTTPException(
            status_code=400,
            detail="Unsupported media format.",
        )

    try:
        canonical_id = str(UUID(upload_id))
        output_dir = PROCESSED_DIR / canonical_id

        if output_dir.is_symlink():
            raise MediaProcessingError(
                "Invalid processing output directory."
            )

        if output_dir.exists():
            shutil.rmtree(output_dir)

        output_dir.mkdir(parents=True, exist_ok=False, mode=0o700)

        if extension in {".jpg", ".jpeg", ".png", ".webp"}:
            analysis = analyze_image(source, output_dir)
            media_type = "image"
        else:
            analysis = process_video(source, output_dir)
            media_type = "video"

        return MediaAnalysisResponse(
            upload_id=canonical_id,
            media_type=media_type,
            analysis=analysis,
        )

    except MediaProcessingError as exc:
        if "output_dir" in locals():
            shutil.rmtree(output_dir, ignore_errors=True)

        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except OSError as exc:
        if "output_dir" in locals():
            shutil.rmtree(output_dir, ignore_errors=True)

        raise HTTPException(
            status_code=500,
            detail="Unable to process the uploaded media.",
        ) from exc

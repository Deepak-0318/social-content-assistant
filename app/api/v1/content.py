from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.schemas.media_upload import MediaUploadResponse
from app.storage.document_storage import store_upload
from app.storage.file_validation import FileValidationError


router = APIRouter(prefix="/content", tags=["Content"])

UPLOAD_DIR = Path("storage/uploads")


@router.post(
    "/upload",
    response_model=MediaUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_media(
    file: UploadFile = File(...),
) -> MediaUploadResponse:
    try:
        result = await store_upload(file, UPLOAD_DIR)

    except FileValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
            if "exceeds the" in str(exc)
            else status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to store the uploaded file.",
        ) from exc

    return MediaUploadResponse(**result)

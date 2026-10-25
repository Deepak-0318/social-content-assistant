import os
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.storage.file_validation import (
    ALLOWED_EXTENSIONS,
    IMAGE_LIMIT,
    VIDEO_LIMIT,
    FileValidationError,
    validate_media_file,
)


CHUNK_SIZE = 1024 * 1024


class UploadTooLargeError(FileValidationError):
    pass


async def store_upload(
    upload: UploadFile,
    storage_dir: Path,
) -> dict[str, str | int]:
    original_name = upload.filename or ""
    extension = Path(original_name).suffix.lower()
    media_type = ALLOWED_EXTENSIONS.get(extension)

    if media_type is None:
        raise FileValidationError(
            "Unsupported file extension. Use JPG, PNG, WebP, MP4, or MOV."
        )

    limit = IMAGE_LIMIT if media_type.startswith("image/") else VIDEO_LIMIT

    storage_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(storage_dir, 0o700)

    upload_id = str(uuid4())
    final_path = storage_dir / f"{upload_id}{extension}"
    temp_path = storage_dir / f".{upload_id}.part"
    size = 0

    try:
        # Exclusive creation prevents accidentally overwriting a file.
        with temp_path.open("xb") as output:
            os.chmod(temp_path, 0o600)

            while True:
                chunk = await upload.read(CHUNK_SIZE)
                if not chunk:
                    break

                size += len(chunk)
                if size > limit:
                    raise UploadTooLargeError(
                        f"File exceeds the {limit // (1024 * 1024)} MiB limit."
                    )

                output.write(chunk)

        validated = validate_media_file(
            path=temp_path,
            filename=original_name,
            size_bytes=size,
        )

        # Same-directory rename makes the final file appear atomically.
        os.replace(temp_path, final_path)

        return {
            "id": upload_id,
            "filename": final_path.name,
            "media_type": validated.media_type,
            "size_bytes": validated.size_bytes,
        }

    finally:
        # Never leave a partially uploaded file after an error.
        temp_path.unlink(missing_ok=True)
        await upload.close()

from dataclasses import dataclass
from pathlib import Path
import warnings

from PIL import Image, UnidentifiedImageError


IMAGE_LIMIT = 10 * 1024 * 1024
VIDEO_LIMIT = 100 * 1024 * 1024

ALLOWED_EXTENSIONS = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
}

# Recognized signatures for the supported formats.
IMAGE_SIGNATURES = {
    "image/jpeg": lambda b: b.startswith(b"\xff\xd8\xff"),
    "image/png": lambda b: b.startswith(b"\x89PNG\r\n\x1a\n"),
    "image/webp": lambda b: (
        len(b) >= 12 and b[:4] == b"RIFF" and b[8:12] == b"WEBP"
    ),
}


class FileValidationError(ValueError):
    """Raised when an uploaded file fails validation."""


@dataclass(frozen=True)
class ValidatedMedia:
    media_type: str
    extension: str
    size_bytes: int


def expected_media_type(filename: str) -> str:
    extension = Path(filename).suffix.lower()
    media_type = ALLOWED_EXTENSIONS.get(extension)

    if media_type is None:
        raise FileValidationError(
            "Unsupported file extension. Use JPG, PNG, WebP, MP4, or MOV."
        )

    return media_type


def validate_media_file(
    path: Path,
    filename: str,
    size_bytes: int,
) -> ValidatedMedia:
    media_type = expected_media_type(filename)
    extension = Path(filename).suffix.lower()

    if size_bytes <= 0:
        raise FileValidationError("The uploaded file is empty.")

    limit = IMAGE_LIMIT if media_type.startswith("image/") else VIDEO_LIMIT
    if size_bytes > limit:
        raise FileValidationError(
            f"File exceeds the {limit // (1024 * 1024)} MiB limit."
        )

    with path.open("rb") as file:
        header = file.read(32)

    if media_type in IMAGE_SIGNATURES:
        if not IMAGE_SIGNATURES[media_type](header):
            raise FileValidationError(
                "File contents do not match the declared image format."
            )

        try:
            # Verify image structure rather than trusting its extension.
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(path) as image:
                    if image.format != {
                        "image/jpeg": "JPEG",
                        "image/png": "PNG",
                        "image/webp": "WEBP",
                    }[media_type]:
                        raise FileValidationError(
                            "Image format does not match its extension."
                        )

                    image.verify()

        except FileValidationError:
            raise
        except (
            UnidentifiedImageError,
            OSError,
            ValueError,
            Image.DecompressionBombError,
            Image.DecompressionBombWarning,
        ) as exc:
            raise FileValidationError(
                "Image is malformed, corrupted, or unsafe to process."
            ) from exc

    else:
        # ISO Base Media File Format containers use an ftyp box.
        # Recognize MP4 and QuickTime/MOV brands.
        with path.open("rb") as file:
            box_header = file.read(8)
            if len(box_header) != 8:
                raise FileValidationError("Video container is incomplete.")

            box_size = int.from_bytes(box_header[:4], "big")
            if box_size > size_bytes:
                raise FileValidationError(
                    "Video container header exceeds the file size."
                )
            box_type = box_header[4:8]

            if box_type != b"ftyp" or box_size < 16:
                raise FileValidationError(
                    "File does not have a valid MP4/MOV container header."
                )

            file.seek(8)
            brands = file.read(min(box_size - 8, 256))

        compatible_brands = {
            brands[i:i + 4]
            for i in range(0, len(brands) - 3, 4)
        }

        if media_type == "video/mp4":
            valid_brand = any(
                brand in compatible_brands
                for brand in {b"isom", b"iso2", b"mp41", b"mp42", b"M4V "}
            )
        else:
            valid_brand = b"qt  " in compatible_brands

        if not valid_brand:
            raise FileValidationError(
                "Video container brand does not match MP4/MOV."
            )

    return ValidatedMedia(
        media_type=media_type,
        extension=extension,
        size_bytes=size_bytes,
    )

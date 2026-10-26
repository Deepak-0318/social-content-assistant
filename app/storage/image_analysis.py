from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError


MAX_IMAGE_DIMENSION = 1024


class MediaProcessingError(RuntimeError):
    """Raised when media cannot be safely processed."""


def analyze_image(source: Path, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

    try:
        with Image.open(source) as image:
            image_format = image.format
            original_width, original_height = image.size

            # Reject implausibly large pixel counts before full decoding.
            if original_width * original_height > 40_000_000:
                raise MediaProcessingError(
                    "Image dimensions exceed the processing limit."
                )

            image.verify()

        with Image.open(source) as image:
            image = ImageOps.exif_transpose(image)
            image.load()

            width, height = image.size
            image.thumbnail(
                (MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION)
            )

            # Use RGB JPEG for a consistent downstream model input.
            if image.mode in ("RGBA", "LA"):
                rgba = image.convert("RGBA")
                background = Image.new("RGBA", rgba.size, "white")
                image = Image.alpha_composite(background, rgba).convert("RGB")
            else:
                image = image.convert("RGB")

            preview_width, preview_height = image.size
            preview_path = output_dir / "image-preview.jpg"
            image.save(
                preview_path,
                format="JPEG",
                quality=88,
                optimize=True,
            )

    except MediaProcessingError:
        raise
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise MediaProcessingError(
            "The uploaded image could not be decoded."
        ) from exc

    return {
        "media_type": "image",
        "source_format": image_format,
        "width": width,
        "height": height,
        "preview_width": image.width,
        "preview_height": image.height,
        "preview_filename": preview_path.name,
    }

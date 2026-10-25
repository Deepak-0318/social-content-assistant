import struct

import pytest
from PIL import Image

from app.storage.file_validation import (
    FileValidationError,
    validate_media_file,
)


def create_png(path):
    Image.new("RGB", (10, 10), "red").save(path, format="PNG")


def test_valid_png_is_accepted(tmp_path):
    path = tmp_path / "image.png"
    create_png(path)

    result = validate_media_file(path, "image.png", path.stat().st_size)

    assert result.media_type == "image/png"
    assert result.extension == ".png"


def test_extension_spoofing_is_rejected(tmp_path):
    path = tmp_path / "fake.png"
    path.write_bytes(b"this is not a PNG")

    with pytest.raises(FileValidationError):
        validate_media_file(path, "fake.png", path.stat().st_size)


def test_malformed_image_is_rejected(tmp_path):
    path = tmp_path / "broken.png"
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"not a valid image")

    with pytest.raises(FileValidationError):
        validate_media_file(path, "broken.png", path.stat().st_size)


def test_unsupported_extension_is_rejected(tmp_path):
    path = tmp_path / "document.pdf"
    path.write_bytes(b"%PDF-test")

    with pytest.raises(FileValidationError):
        validate_media_file(path, "document.pdf", path.stat().st_size)


def test_valid_mp4_container_header_is_accepted(tmp_path):
    path = tmp_path / "sample.mp4"

    # Minimal ISO BMFF ftyp box with the "isom" brand.
    path.write_bytes(
        struct.pack(">I4s4sI4s", 20, b"ftyp", b"isom", 0, b"isom")
    )

    result = validate_media_file(path, "sample.mp4", path.stat().st_size)

    assert result.media_type == "video/mp4"


def test_mp4_with_wrong_container_is_rejected(tmp_path):
    path = tmp_path / "fake.mp4"
    path.write_bytes(b"this is not a video container")

    with pytest.raises(FileValidationError):
        validate_media_file(path, "fake.mp4", path.stat().st_size)

import shutil
import subprocess

import pytest
from uuid import uuid4

from fastapi.testclient import TestClient
from PIL import Image

from app.api.v1 import media
from app.main import app
from app.storage.image_analysis import analyze_image
from app.storage.video_processing import process_video


client = TestClient(app)


def test_image_analysis_creates_preview(tmp_path):
    source = tmp_path / "source.png"
    output = tmp_path / "processed"

    Image.new("RGB", (1600, 900), "blue").save(source)

    result = analyze_image(source, output)

    assert result["media_type"] == "image"
    assert result["width"] == 1600
    assert result["height"] == 900
    assert result["preview_width"] <= 1024
    assert result["preview_height"] <= 1024
    assert (output / "image-preview.jpg").is_file()


def test_corrupt_image_is_rejected(tmp_path):
    source = tmp_path / "broken.png"
    source.write_bytes(b"not a real image")

    try:
        analyze_image(source, tmp_path / "processed")
        assert False, "Expected MediaProcessingError"
    except media.MediaProcessingError:
        pass


def test_analyze_uploaded_image(tmp_path, monkeypatch):
    upload_dir = tmp_path / "uploads"
    processed_dir = tmp_path / "processed"
    upload_dir.mkdir()

    upload_id = str(uuid4())
    source = upload_dir / f"{upload_id}.png"
    Image.new("RGB", (100, 80), "red").save(source)

    monkeypatch.setattr(media, "UPLOAD_DIR", upload_dir)
    monkeypatch.setattr(media, "PROCESSED_DIR", processed_dir)

    response = client.post(f"/api/v1/media/{upload_id}/analyze")

    assert response.status_code == 200
    result = response.json()

    assert result["media_type"] == "image"
    assert result["processing_status"] == "completed"
    assert result["analysis"]["width"] == 100
    assert result["ai_description"] is None
    assert result["transcript"] is None


def test_invalid_upload_id_is_rejected():
    response = client.post("/api/v1/media/not-a-uuid/analyze")

    assert response.status_code == 400


def test_missing_upload_returns_404(tmp_path, monkeypatch):
    monkeypatch.setattr(media, "UPLOAD_DIR", tmp_path / "uploads")
    monkeypatch.setattr(media, "PROCESSED_DIR", tmp_path / "processed")

    response = client.post(
        f"/api/v1/media/{uuid4()}/analyze"
    )

    assert response.status_code == 404

@pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="FFmpeg and FFprobe are required for this test",
)
def test_video_frames_and_audio_are_extracted(tmp_path):
    source = tmp_path / "sample.mp4"
    output = tmp_path / "processed"

    subprocess.run(
        [
            shutil.which("ffmpeg"),
            "-nostdin",
            "-hide_banner",
            "-loglevel", "error",
            "-y",
            "-f", "lavfi",
            "-i", "testsrc=size=160x120:rate=10",
            "-f", "lavfi",
            "-i", "sine=frequency=1000:sample_rate=44100",
            "-t", "2",
            "-c:v", "mpeg4",
            "-c:a", "aac",
            "-pix_fmt", "yuv420p",
            "-shortest",
            str(source),
        ],
        check=True,
        capture_output=True,
        timeout=30,
    )

    result = process_video(source, output)

    assert result["media_type"] == "video"
    assert result["duration_seconds"] > 0
    assert 1 <= len(result["frames"]) <= 12
    assert result["audio_available"] is True
    assert result["audio_filename"] == "audio.wav"
    assert (output / "audio.wav").is_file()

    for frame in result["frames"]:
        assert (output / "frames" / frame["filename"]).is_file()
        assert frame["timestamp_seconds"] > 0

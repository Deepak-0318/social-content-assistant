from fastapi.testclient import TestClient
from PIL import Image

from app.api.v1 import content
from app.main import app

client = TestClient(app)


def test_upload_valid_png(tmp_path, monkeypatch):
    monkeypatch.setattr(content, "UPLOAD_DIR", tmp_path)

    image = Image.new("RGB", (10, 10), "blue")
    from io import BytesIO

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    payload = buffer.getvalue()

    response = client.post(
        "/api/v1/content/upload",
        files={"file": ("photo.png", payload, "image/png")},
    )

    assert response.status_code == 201

    data = response.json()
    assert data["media_type"] == "image/png"
    assert data["size_bytes"] == len(payload)
    assert data["status"] == "uploaded"

    saved_file = tmp_path / data["filename"]
    assert saved_file.exists()
    assert saved_file.read_bytes() == payload


def test_upload_rejects_unsupported_file(tmp_path, monkeypatch):
    monkeypatch.setattr(content, "UPLOAD_DIR", tmp_path)

    response = client.post(
        "/api/v1/content/upload",
        files={"file": ("document.pdf", b"%PDF-test", "application/pdf")},
    )

    assert response.status_code == 400
    assert not list(tmp_path.glob("*.pdf"))


def test_upload_rejects_spoofed_png(tmp_path, monkeypatch):
    monkeypatch.setattr(content, "UPLOAD_DIR", tmp_path)

    response = client.post(
        "/api/v1/content/upload",
        files={"file": ("fake.png", b"not an image", "image/png")},
    )

    assert response.status_code == 400
    assert not list(tmp_path.glob("*.png"))


def test_upload_rejects_empty_file(tmp_path, monkeypatch):
    monkeypatch.setattr(content, "UPLOAD_DIR", tmp_path)

    response = client.post(
        "/api/v1/content/upload",
        files={"file": ("empty.png", b"", "image/png")},
    )

    assert response.status_code == 400

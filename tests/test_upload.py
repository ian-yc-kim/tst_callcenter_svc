import io
import time
from datetime import datetime

import pytest
from fastapi import status
from fastapi.testclient import TestClient

# Import the app so that the new endpoint is available
from tst_callcenter_svc.app import app

client = TestClient(app)


# Helper to create a dummy wav file content

def create_dummy_wav_file(size: int = 1024, filename: str = "test.wav", content_type: str = "audio/wav"):
    content = b"RIFF\x00" + b"\x00" * (size - 4)
    return (filename, io.BytesIO(content), content_type)


# Monkeypatch trigger_n8n_workflow to simulate integration
@pytest.fixture(autouse=True)
def patch_trigger_n8n(monkeypatch):
    def fake_trigger(payload):
        return {"success": True, "message": "Workflow triggered successfully"}
    # Patch the trigger function in the upload module directly
    monkeypatch.setattr("tst_callcenter_svc.routers.upload.trigger_n8n_workflow", fake_trigger)


def test_upload_valid_file():
    file_tuple = create_dummy_wav_file(size=1024, filename="valid.wav", content_type="audio/wav")
    response = client.post("/api/v1/upload", files={"file": file_tuple})
    assert response.status_code == 200
    data = response.json()
    assert data.get("success") is True
    assert data.get("message") == "Workflow triggered successfully"


def test_upload_missing_file():
    response = client.post("/api/v1/upload")
    assert response.status_code == 422  # FastAPI validation error for missing file


def test_upload_invalid_extension():
    # Use a file with .txt extension
    file_tuple = ("invalid.txt", io.BytesIO(b"dummy content"), "audio/wav")
    response = client.post("/api/v1/upload", files={"file": file_tuple})
    assert response.status_code == 400
    data = response.json()
    assert "Invalid file extension" in data.get("detail")


def test_upload_invalid_mime_type():
    # Use a valid .wav file name but wrong MIME type
    file_tuple = ("test.wav", io.BytesIO(b"dummy content"), "application/octet-stream")
    response = client.post("/api/v1/upload", files={"file": file_tuple})
    assert response.status_code == 400
    data = response.json()
    assert "Invalid MIME type" in data.get("detail")


def test_upload_exceed_file_size(monkeypatch):
    # Create a file larger than 100MB
    large_size = 101 * 1024 * 1024  # Slightly over 100MB
    large_content = b"\x00" * large_size
    file_tuple = ("large.wav", io.BytesIO(large_content), "audio/wav")
    response = client.post("/api/v1/upload", files={"file": file_tuple})
    assert response.status_code == 400
    data = response.json()
    assert "File size exceeds" in data.get("detail")


def test_old_upload_endpoint_not_found():
    # The old endpoint /api/upload should no longer be available
    # Do not include file upload to avoid file processing errors
    response = client.post("/api/upload")
    # Expecting 404 since the route has been moved
    assert response.status_code == 404

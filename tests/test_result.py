import uuid
from datetime import datetime

import pytest
import requests

from tst_callcenter_svc.models.upload_metadata import UploadMetadata
from tst_callcenter_svc.models.base import get_db


# Helper function to insert a dummy record into the test database

def insert_dummy_record(db, upload_id: str, original_filename: str = "test.wav", file_size: int = 1024):
    record = UploadMetadata(
        id=upload_id,
        file_path="/dummy/path",
        original_filename=original_filename,
        file_size=file_size,
        upload_timestamp=datetime.utcnow()
    )
    db.add(record)
    db.commit()
    return record


# Use the client fixture provided by conftest.py

@pytest.fixture(autouse=True)
def override_get_db_for_test(db_session, client):
    # Override the get_db dependency to yield the same db_session instance used here
    def override_get_db():
        yield db_session
    client.app.dependency_overrides[get_db] = override_get_db
    yield
    client.app.dependency_overrides.pop(get_db, None)


def test_get_result_success(client):
    # Insert a dummy record into the test database
    valid_uuid = str(uuid.uuid4())
    # Get the shared db_session via dependency override
    db = next(client.app.dependency_overrides[get_db]())
    insert_dummy_record(db, valid_uuid)

    # Set Airtable environment variables
    import os
    os.environ["AIRTABLE_API_URL"] = "https://api.airtable.com/v0"
    os.environ["AIRTABLE_API_KEY"] = "test_api_key"
    os.environ["AIRTABLE_BASE_ID"] = "appTestBase"
    os.environ["AIRTABLE_TABLE_NAME"] = "TestTable"

    # Simulate a successful Airtable API response
    def fake_get(url, params, headers, timeout):
        class FakeResponse:
            status_code = 200
            def json(self):
                return {
                    "records": [
                        {
                            "fields": {
                                "processing_status": "completed",
                                "logs": "Log details",
                                "analysis_result": "Result details"
                            }
                        }
                    ]
                }
        return FakeResponse()

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(requests, "get", fake_get)

    response = client.get(f"/api/v1/result/{valid_uuid}")
    monkeypatch.undo()
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["upload_id"] == valid_uuid
    assert data["original_filename"] == "test.wav"
    assert data["processing_status"] == "completed"
    assert data["logs"] == "Log details"
    assert data["analysis_result"] == "Result details"


def test_get_result_invalid_uuid(client):
    invalid_uuid = "invalid-uuid"
    response = client.get(f"/api/v1/result/{invalid_uuid}")
    assert response.status_code == 400
    data = response.json()
    assert "Invalid UUID format" in data.get("detail")


def test_get_result_not_found(client):
    non_existent_uuid = str(uuid.uuid4())
    response = client.get(f"/api/v1/result/{non_existent_uuid}")
    assert response.status_code == 404
    data = response.json()
    assert "Upload record not found" in data.get("detail")


def test_get_result_airtable_failure(client):
    valid_uuid = str(uuid.uuid4())
    db = next(client.app.dependency_overrides[get_db]())
    insert_dummy_record(db, valid_uuid)

    import os
    os.environ["AIRTABLE_API_URL"] = "https://api.airtable.com/v0"
    os.environ["AIRTABLE_API_KEY"] = "test_api_key"
    os.environ["AIRTABLE_BASE_ID"] = "appTestBase"
    os.environ["AIRTABLE_TABLE_NAME"] = "TestTable"

    def fake_get(url, params, headers, timeout):
        class FakeResponse:
            status_code = 500
            def json(self):
                return {}
        return FakeResponse()

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(requests, "get", fake_get)

    response = client.get(f"/api/v1/result/{valid_uuid}")
    monkeypatch.undo()
    assert response.status_code == 500
    data = response.json()
    assert "Error retrieving analysis details" in data.get("detail")

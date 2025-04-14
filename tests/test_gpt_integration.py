import os
import time
import requests
import logging

from fastapi import HTTPException
from datetime import datetime

from tst_callcenter_svc.routers import gpt_integration


class FakeSuccessResponse:
    status_code = 200
    def json(self):
        return {"analysis": "Test analysis result"}


def fake_success_post(self, url, json, headers, timeout, verify):
    return FakeSuccessResponse()


def fake_retry_post_factory(call_count):
    def fake_retry_post(self, url, json, headers, timeout, verify):
        call_count["count"] += 1
        raise requests.exceptions.ConnectionError("Connection failed")
    return fake_retry_post


def test_successful_analysis(client, monkeypatch):
    # Set environment variables for GPT API
    monkeypatch.setenv("GPT_API_URL", "https://example.com/analyze")
    monkeypatch.setenv("GPT_API_KEY", "dummy_key")

    # Patch requests.Session.post to simulate a successful GPT API response
    monkeypatch.setattr(requests.Session, "post", fake_success_post)

    payload = {
        "conversation_id": "conv123",
        "preprocessed_audio_data": "audio_data",
        "timestamp": "2023-10-10T10:00:00"
    }
    response = client.post("/api/gpt/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data.get("success") is True
    assert data.get("analysis") == "Test analysis result"


def test_retry_mechanism(client, monkeypatch):
    call_count = {"count": 0}
    monkeypatch.setenv("GPT_API_URL", "https://example.com/analyze")
    monkeypatch.setenv("GPT_API_KEY", "dummy_key")

    monkeypatch.setattr(requests.Session, "post", fake_retry_post_factory(call_count))

    payload = {
        "conversation_id": "conv456",
        "preprocessed_audio_data": "audio_data",
        "timestamp": "2023-10-10T10:00:00"
    }
    response = client.post("/api/gpt/analyze", json=payload)
    # Should fail after 3 attempts
    assert response.status_code == 500
    assert call_count["count"] == 3


def test_validation_error(client):
    # Missing required fields
    payload = {
        "conversation_id": "conv789"
    }
    response = client.post("/api/gpt/analyze", json=payload)
    assert response.status_code == 422


# Additional tests for Airtable logging functionality

def test_log_to_airtable_success(monkeypatch):
    monkeypatch.setenv("AIRTABLE_API_URL", "https://example.com/airtable")
    monkeypatch.setenv("AIRTABLE_API_KEY", "dummy_airtable_key")
    monkeypatch.setenv("AIRTABLE_BASE_ID", "base123")
    monkeypatch.setenv("AIRTABLE_TABLE_NAME", "table_name")

    def fake_airtable_post(self, url, json, headers, timeout, verify):
        class FakeResponse:
            status_code = 200
            def json(inner_self):
                return {"id": "rec123"}
        return FakeResponse()

    monkeypatch.setattr(requests.Session, "post", fake_airtable_post)
    # Call the helper function directly
    gpt_integration.log_to_airtable("conv001", "analysis result", "2023-10-10T10:00:00")
    # If no exception and no retries needed, the test passes


def test_log_to_airtable_retry(monkeypatch):
    monkeypatch.setenv("AIRTABLE_API_URL", "https://example.com/airtable")
    monkeypatch.setenv("AIRTABLE_API_KEY", "dummy_airtable_key")
    monkeyatch_env = {
        "AIRTABLE_BASE_ID": "base123",
        "AIRTABLE_TABLE_NAME": "table_name"
    }
    for key, value in monkeyatch_env.items():
        monkeypatch.setenv(key, value)

    call_count = {"count": 0}
    def fake_airtable_post(self, url, json, headers, timeout, verify):
        call_count["count"] += 1
        # Simulate non-200 response
        FakeResponse = type('FakeResponse', (), {})
        response = FakeResponse()
        response.status_code = 500
        response.json = lambda: {}
        return response

    monkeypatch.setattr(requests.Session, "post", fake_airtable_post)
    gpt_integration.log_to_airtable("conv002", "analysis result", "2023-10-10T10:00:00")
    assert call_count["count"] == 3


def test_log_to_airtable_invalid_url(monkeypatch):
    # Set an invalid (insecure) Airtable URL
    monkeypatch.setenv("AIRTABLE_API_URL", "http://insecure.com/airtable")
    # Other environment variables (if any) can be set normally
    monkeypatch.setenv("AIRTABLE_API_KEY", "dummy_airtable_key")
    monkeypatch.setenv("AIRTABLE_BASE_ID", "base123")
    monkeypatch.setenv("AIRTABLE_TABLE_NAME", "table_name")

    call_count = {"count": 0}
    def fake_airtable_post(self, url, json, headers, timeout, verify):
        call_count["count"] += 1
        FakeResponse = type('FakeResponse', (), {})
        response = FakeResponse()
        response.status_code = 200
        response.json = lambda: {}
        return response

    monkeypatch.setattr(requests.Session, "post", fake_airtable_post)
    # Should detect insecure URL and not attempt any POST
    gpt_integration.log_to_airtable("conv003", "analysis result", "2023-10-10T10:00:00")
    assert call_count["count"] == 0

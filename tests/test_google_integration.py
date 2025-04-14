import os
import time
import uuid
import logging
import requests

import pytest
from fastapi import HTTPException
from datetime import datetime


def fake_success_post(self, url, json, headers, timeout, verify):
    """Fake post function to simulate a successful HTTPS POST response."""
    class FakeResponse:
        status_code = 200
        def json(inner_self):
            return {"success": True, "message": "Google processing triggered successfully"}
    return FakeResponse()


def fake_retry_post_factory(call_count):
    def fake_retry_post(self, url, json, headers, timeout, verify):
        call_count["count"] += 1
        raise requests.exceptions.ConnectionError("Connection failed")
    return fake_retry_post


def test_successful_trigger(client, monkeypatch):
    # Set environment variable for test
    monkeypatch.setenv("GOOGLE_API_URL", "https://example.com/google")
    # Patch the post method on the requests.Session class to simulate success
    monkeypatch.setattr(requests.Session, "post", fake_success_post)

    payload = {
        "task_id": "task123",
        "additional_data": {"key": "value"},
        "timestamp": "2023-10-10T10:00:00"
    }
    response = client.post("/api/google/trigger", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data.get("success") is True
    assert data.get("message") == "Google processing triggered successfully"


def test_retry_mechanism(client, monkeypatch):
    call_count = {"count": 0}
    monkeypatch.setenv("GOOGLE_API_URL", "https://example.com/google")
    monkeypatch.setattr(requests.Session, "post", fake_retry_post_factory(call_count))

    payload = {
        "task_id": "task456",
        "additional_data": {},
        "timestamp": "2023-10-10T10:00:00"
    }
    response = client.post("/api/google/trigger", json=payload)
    # Endpoint should fail after 3 retries
    assert response.status_code == 500
    assert call_count["count"] == 3


def test_validation_error(client):
    # Missing required field task_id
    payload = {
        "additional_data": {"key": "value"},
        "timestamp": "2023-10-10T10:00:00"
    }
    response = client.post("/api/google/trigger", json=payload)
    assert response.status_code == 422

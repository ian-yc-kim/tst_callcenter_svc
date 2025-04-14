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
    # Set environment variables for test
    monkeypatch.setenv("GPT_API_URL", "https://example.com/analyze")
    monkeypatch.setenv("GPT_API_KEY", "dummy_key")

    # Patch requests.Session.post to simulate a successful response
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

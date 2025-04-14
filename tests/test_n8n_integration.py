import requests


def fake_success_post(self, url, data=None, json=None, **kwargs):
    """Fake post function to simulate a successful HTTPS POST response."""
    class FakeResponse:
        status_code = 200
        def json(inner_self):
            return {"success": True, "message": "Workflow triggered successfully"}
    return FakeResponse()


def fake_retry_post_factory(call_count):
    def fake_retry_post(self, url, data=None, json=None, **kwargs):
        call_count["count"] += 1
        raise requests.exceptions.ConnectionError("Connection failed")
    return fake_retry_post


def test_successful_trigger(client, monkeypatch):
    # Set environment variable for test
    monkeypatch.setenv("N8N_WEBHOOK_URL", "https://example.com/webhook")
    # Patch the post method on the requests.Session class
    monkeypatch.setattr(requests.Session, "post", fake_success_post)
    payload = {
        "file_name": "test.txt",
        "file_size": 123,
        "upload_timestamp": "2023-10-10T10:00:00",
        "metadata": {"key": "value"}
    }
    response = client.post("/api/n8n/trigger", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data.get("success") is True


def test_retry_mechanism(client, monkeypatch):
    call_count = {"count": 0}
    monkeypatch.setenv("N8N_WEBHOOK_URL", "https://example.com/webhook")
    # Patch the Session.post method using a factory to capture call count
    monkeypatch.setattr(requests.Session, "post", fake_retry_post_factory(call_count))
    payload = {
        "file_name": "test.txt",
        "file_size": 456,
        "upload_timestamp": "2023-10-10T10:00:00",
        "metadata": {}
    }
    response = client.post("/api/n8n/trigger", json=payload)
    # Endpoint should fail after 3 retries
    assert response.status_code == 500
    assert call_count["count"] == 3


def test_validation_error(client):
    # Missing required fields: file_size, upload_timestamp and metadata
    payload = {
        "file_name": "test.txt"
    }
    response = client.post("/api/n8n/trigger", json=payload)
    assert response.status_code == 422

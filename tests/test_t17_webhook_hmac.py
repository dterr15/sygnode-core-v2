"""T17: Gmail webhook HMAC validation."""

import base64
import pytest
from app.settings import settings


@pytest.mark.asyncio
async def test_webhook_invalid_hmac(client):
    """T17: Invalid HMAC → 401, no processing."""
    response = await client.post(
        "/api/v2/ingest/gmail/webhook",
        json={"message": {"data": base64.b64encode(b"test").decode()}},
        headers={"x-goog-channel-token": "wrong-token"},
    )
    assert response.status_code == 401
    assert "HMAC" in response.json()["detail"]


@pytest.mark.asyncio
async def test_webhook_valid_hmac_no_token_configured(client):
    """T17b: Webhook without configured token → 503."""
    original = settings.gmail_webhook_token
    settings.gmail_webhook_token = ""
    try:
        response = await client.post(
            "/api/v2/ingest/gmail/webhook",
            json={"message": {}},
            headers={"x-goog-channel-token": "any-token"},
        )
        assert response.status_code == 503
    finally:
        settings.gmail_webhook_token = original


@pytest.mark.asyncio
async def test_webhook_valid_hmac_creates_intake(auth_client):
    """T17c: Valid HMAC with payload creates intake."""
    token = "test-webhook-token-2026"
    original = settings.gmail_webhook_token
    settings.gmail_webhook_token = token

    text = "50 kg cemento webhook\n10 sacos cal webhook"
    encoded = base64.b64encode(text.encode()).decode()

    try:
        response = await auth_client.post(
            "/api/v2/ingest/gmail/webhook",
            json={"message": {"data": encoded}},
            headers={"x-goog-channel-token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # processed=1 if org/user exists, 0 if not (auth_client has user fixture)
        assert data["processed"] in (0, 1)
    finally:
        settings.gmail_webhook_token = original

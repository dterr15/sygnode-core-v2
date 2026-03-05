"""Gmail service — Google Workspace API integration for email ingestion."""

import json
import time
from datetime import datetime, timezone

import httpx
from jose import jwt as jose_jwt

from app.settings import settings


class GmailClient:
    """Connects to Gmail via Google Workspace Service Account impersonation."""

    SCOPES = ["https://www.googleapis.com/auth/gmail.readonly", "https://www.googleapis.com/auth/gmail.modify"]
    TOKEN_URI = "https://oauth2.googleapis.com/token"
    GMAIL_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"

    def __init__(self):
        self._access_token: str | None = None
        self._token_expiry: float = 0

    async def _get_token(self) -> str:
        if self._access_token and time.time() < self._token_expiry - 60:
            return self._access_token

        now = int(time.time())
        payload = {
            "iss": settings.gws_client_email,
            "sub": settings.gws_impersonate_user,
            "scope": " ".join(self.SCOPES),
            "aud": self.TOKEN_URI,
            "iat": now,
            "exp": now + 3600,
        }

        assertion = jose_jwt.encode(
            payload,
            settings.gws_private_key.replace("\\n", "\n"),
            algorithm="RS256",
        )

        async with httpx.AsyncClient() as client:
            resp = await client.post(self.TOKEN_URI, data={
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": assertion,
            })
            resp.raise_for_status()
            data = resp.json()
            self._access_token = data["access_token"]
            self._token_expiry = now + data.get("expires_in", 3600)
            return self._access_token

    async def get_history(self, start_history_id: str) -> list[dict]:
        token = await self._get_token()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.GMAIL_BASE}/history",
                headers={"Authorization": f"Bearer {token}"},
                params={"startHistoryId": start_history_id, "historyTypes": "messageAdded"},
            )
            if resp.status_code == 404:
                return []
            resp.raise_for_status()
            return resp.json().get("history", [])

    async def get_message(self, message_id: str) -> dict:
        token = await self._get_token()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.GMAIL_BASE}/messages/{message_id}",
                headers={"Authorization": f"Bearer {token}"},
                params={"format": "full"},
            )
            resp.raise_for_status()
            return resp.json()


gmail_client = GmailClient()

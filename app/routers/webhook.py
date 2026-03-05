"""Webhook router — Gmail ingestion with HMAC validation (G6, T17)."""

import hmac
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.settings import settings

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("/gmail/webhook")
async def gmail_webhook(
    request: Request,
    x_goog_channel_token: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """
    T17: Validate HMAC before any processing.
    G6: LLM only called after valid HMAC.
    """
    # Validate HMAC (G6)
    if not hmac.compare_digest(
        x_goog_channel_token.encode(),
        settings.gmail_webhook_token.encode(),
    ):
        raise HTTPException(status_code=401, detail="HMAC inválido")

    # Parse Pub/Sub notification
    body = await request.json()
    # Process Gmail notification...
    # (Full implementation would decode base64, get history, create intake)

    return {"success": True, "processed": 0}

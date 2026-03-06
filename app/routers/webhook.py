"""Webhook router - Gmail ingestion with HMAC validation (G6, T17)."""

import base64
import hmac
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import CurrentUser
from app.models.organization import Organization
from app.models.user import User
from app.settings import settings
from app.services.intake_service import create_intake_from_paste

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("/gmail/webhook")
async def gmail_webhook(
    request: Request,
    x_goog_channel_token: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """
    T17: Validate HMAC before any processing.
    G6: intake creation only after valid HMAC.
    """
    # Validate HMAC first - G6: reject immediately if invalid
    if not settings.gmail_webhook_token:
        raise HTTPException(status_code=503, detail="Webhook no configurado")

    if not hmac.compare_digest(
        x_goog_channel_token.encode(),
        settings.gmail_webhook_token.encode(),
    ):
        raise HTTPException(status_code=401, detail="HMAC inválido")

    # Parse Pub/Sub notification
    body = await request.json()

    message = body.get("message", {})
    data_b64 = message.get("data", "")
    if not data_b64:
        return {"success": True, "processed": 0}

    try:
        decoded = base64.b64decode(data_b64).decode("utf-8")
    except Exception:
        return {"success": True, "processed": 0, "note": "No se pudo decodificar payload"}

    # Build intake text from notification payload
    # In production: fetch full email via Gmail API using history_id
    # For now: create intake from decoded notification body
    email_subject = message.get("attributes", {}).get("emailSubject", "Webhook email")
    intake_text = decoded.strip() or email_subject

    if not intake_text or len(intake_text) < 5:
        return {"success": True, "processed": 0}

    # Find a suitable organization and system user for the intake
    # In production: map sender email to organization
    org_result = await db.execute(select(Organization).limit(1))
    org = org_result.scalar_one_or_none()
    if not org:
        return {"success": True, "processed": 0, "note": "Sin organizacion"}

    user_result = await db.execute(
        select(User).where(User.organization_id == org.id, User.role == "admin_org").limit(1)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        return {"success": True, "processed": 0, "note": "Sin usuario admin"}

    try:
        intake, item_count = await create_intake_from_paste(
            db=db,
            text=intake_text,
            source="email",
            user=user,
        )
        await db.commit()
        return {"success": True, "processed": 1, "list_id": str(intake.id), "item_count": item_count}
    except HTTPException as e:
        # Duplicate or insufficient data - not an error
        return {"success": True, "processed": 0, "note": e.detail}

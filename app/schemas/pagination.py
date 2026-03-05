"""Cursor-based pagination utilities."""

import base64
import json
from typing import Generic, TypeVar
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel

T = TypeVar("T")


class CursorPage(BaseModel, Generic[T]):
    items: list[T]
    next_cursor: str | None = None
    total: int | None = None


def encode_cursor(last_id: UUID, last_ts: datetime) -> str:
    payload = json.dumps({"id": str(last_id), "ts": last_ts.isoformat()})
    return base64.urlsafe_b64encode(payload.encode()).decode()


def decode_cursor(cursor: str) -> dict:
    try:
        payload = base64.urlsafe_b64decode(cursor.encode()).decode()
        data = json.loads(payload)
        return {"id": UUID(data["id"]), "ts": datetime.fromisoformat(data["ts"])}
    except Exception:
        raise ValueError("Invalid cursor")

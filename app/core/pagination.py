"""
Cursor-based pagination for all list endpoints (ADR-007).
cursor = base64(json({id: last_id, ts: last_timestamp}))
"""

import base64
import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import Column, and_


def encode_cursor(last_id: UUID, last_ts: datetime) -> str:
    payload = json.dumps({"id": str(last_id), "ts": last_ts.isoformat()})
    return base64.urlsafe_b64encode(payload.encode()).decode()


def decode_cursor(cursor: str) -> tuple[UUID, datetime]:
    try:
        payload = base64.urlsafe_b64decode(cursor.encode()).decode()
        data = json.loads(payload)
        return UUID(data["id"]), datetime.fromisoformat(data["ts"])
    except Exception:
        raise ValueError("Invalid cursor")


def apply_cursor_filter(query, cursor: str | None, id_col, ts_col):
    """Apply cursor-based pagination filter to a SQLAlchemy query."""
    if cursor:
        last_id, last_ts = decode_cursor(cursor)
        query = query.where(
            and_(
                ts_col <= last_ts,
                ~and_(ts_col == last_ts, id_col >= last_id),
            )
        )
    return query

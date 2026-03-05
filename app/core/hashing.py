"""
SHA256 hashing for timeline chain integrity (G1).
The event_hash formula matches doc 03 exactly.
"""

import hashlib
from datetime import datetime
from uuid import UUID


def calculate_event_hash(
    event_id: UUID,
    case_id: UUID,
    event_type: str,
    event_timestamp: datetime,
    actor_role: str | None,
    related_doc_ids: list[UUID] | None,
    artifact_hash: str | None,
    prev_event_hash: str,
) -> str:
    """
    SHA256(id|case_id|event_type|timestamp|actor_role|doc_ids|artifact_hash|prev_hash)
    Matches the formula in doc 03 and Golden Rule G1.
    """
    payload = "|".join([
        str(event_id),
        str(case_id),
        event_type,
        str(event_timestamp),
        str(actor_role or ""),
        str(sorted([str(d) for d in (related_doc_ids or [])])),
        str(artifact_hash or ""),
        str(prev_event_hash),
    ])
    return hashlib.sha256(payload.encode()).hexdigest()


def calculate_sha256(data: bytes) -> str:
    """SHA256 hash of file bytes for evidence integrity."""
    return hashlib.sha256(data).hexdigest()


def calculate_pack_signature(pack_data: dict) -> str:
    """SHA256 of the JSON-serialized evidence pack."""
    import json
    payload = json.dumps(pack_data, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()

"""
Scoring Service — Skill 5: score_suppliers.
Single query with LEFT JOINs — eliminates N+1 from v1.
Formula from doc 11.
"""

import uuid
import math
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.supplier import SupplierScore


@dataclass
class ScoringContext:
    item_normalized: str
    category: str
    rfq_lat: float | None = None
    rfq_lng: float | None = None


async def score_suppliers(
    db: AsyncSession,
    org_id: uuid.UUID,
    candidate_ids: list[uuid.UUID],
    context: ScoringContext,
    limit: int = 5,
) -> list[SupplierScore]:
    """
    Score suppliers for an RFQ item using a single query.
    No N+1 — all data fetched in one LEFT JOIN query.
    """
    if not candidate_ids:
        return []

    # Single query with LEFT JOINs (from doc 11, Skill 5)
    query = text("""
        SELECT
            s.id, s.name, s.is_validated,
            s.lat, s.lng,
            s.total_quotes, s.awarded_quotes,
            COALESCE(sii.times_quoted, 0) as item_experience,
            COALESCE(sii.selection_rate, 0) as item_selection_rate,
            COALESCE(sc.num_quotes, 0) as category_experience,
            COALESCE(sc.selection_rate, 0) as category_selection_rate,
            COALESCE(sii.feedback_adjustment, 0) as feedback_adj
        FROM suppliers s
        LEFT JOIN supplier_item_index sii
            ON sii.supplier_id = s.id
            AND sii.item_normalized = :item_normalized
        LEFT JOIN supplier_categories sc
            ON sc.supplier_id = s.id
            AND sc.category = :category
        WHERE s.id = ANY(:supplier_ids)
            AND s.organization_id = :org_id
    """)

    result = await db.execute(query, {
        "item_normalized": context.item_normalized,
        "category": context.category,
        "supplier_ids": candidate_ids,
        "org_id": org_id,
    })
    rows = result.fetchall()

    scores = []
    for row in rows:
        raw_score = _calculate_score(row, context)
        multiplier = 1.0 if row.is_validated else 0.5
        final_score = raw_score * multiplier

        scores.append(SupplierScore(
            supplier_id=row.id,
            supplier_name=row.name,
            score_final=round(final_score, 2),
            is_validated=row.is_validated,
            score_breakdown={
                "experience": min(row.item_experience * 5, 40),
                "category": min(row.category_experience * 2, 20),
                "geo": _geo_score(row.lat, row.lng, context),
                "track_record": _track_record(row),
                "feedback": float(row.feedback_adj),
                "validation_multiplier": multiplier,
            },
        ))

    scores.sort(key=lambda s: s.score_final, reverse=True)
    return scores[:limit]


def _calculate_score(row, context: ScoringContext) -> float:
    """Exact formula from doc 11, Skill 5."""
    # Experience with item: 0-40 pts
    experience = min(row.item_experience * 5, 40)
    if row.item_selection_rate > 0.3:
        experience += 15

    # Category specialization: 0-25 pts
    category = min(row.category_experience * 2, 20)
    if row.category_selection_rate > 0.4:
        category += 5

    # Geographic proximity: 0-20 pts
    geo = _geo_score(row.lat, row.lng, context)

    # Track record: 0-15 pts
    track = _track_record(row)

    # Feedback adjustment
    feedback = float(row.feedback_adj)

    return experience + category + geo + track + feedback


def _geo_score(lat, lng, context: ScoringContext) -> float:
    if not context.rfq_lat or not context.rfq_lng or not lat or not lng:
        return 8.0  # Same country, no coords

    dist = _haversine(float(lat), float(lng), context.rfq_lat, context.rfq_lng)
    if dist < 50:
        return 20.0
    elif dist < 200:
        return 15.0
    elif dist < 500:
        return 10.0
    elif dist < 1000:
        return 5.0
    return 1.0


def _track_record(row) -> float:
    score = 0.0
    total = row.total_quotes or 0
    if total > 50:
        score = 10.0
    elif total > 20:
        score = 7.0
    elif total > 5:
        score = 3.0

    awarded = row.awarded_quotes or 0
    if total > 0 and (awarded / total) > 0.3:
        score += 5.0

    return min(score, 15.0)


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
        * math.sin(dlng / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(a))

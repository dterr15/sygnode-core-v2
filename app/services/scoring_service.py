"""
Scoring Service - Skill 5: score_suppliers.
Single query with LEFT JOINs - eliminates N+1 from v1.
Formula from doc 11.
"""

import uuid
import math
from dataclasses import dataclass

from sqlalchemy import select, text, func, case, cast, Float
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.supplier import Supplier, SupplierItemIndex, SupplierCategories
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
    No N+1 - all data fetched in one LEFT JOIN query.
    Works on both PostgreSQL and SQLite.
    """
    if not candidate_ids:
        return []

    # Convert to strings for IN clause (SQLite-safe)
    ids_str = [str(i) for i in candidate_ids]

    # Single query with LEFT JOINs - SQLite-compatible (no ANY())
    from sqlalchemy.orm import aliased
    from app.models.supplier import SupplierItemIndex as SII, SupplierCategories as SC

    sii = aliased(SII)
    sc = aliased(SC)

    query = (
        select(
            Supplier,
            func.coalesce(sii.times_quoted, 0).label("item_experience"),
            func.coalesce(sii.selection_rate, 0).label("item_selection_rate"),
            func.coalesce(sii.feedback_adjustment, 0).label("feedback_adj"),
            func.coalesce(sc.num_quotes, 0).label("category_experience"),
            func.coalesce(sc.selection_rate, 0).label("category_selection_rate"),
        )
        .outerjoin(sii, (sii.supplier_id == Supplier.id) & (sii.item_normalized == context.item_normalized))
        .outerjoin(sc, (sc.supplier_id == Supplier.id) & (sc.category == context.category))
        .where(
            Supplier.id.in_(candidate_ids),
            Supplier.organization_id == org_id,
        )
    )

    result = await db.execute(query)
    rows = result.all()

    scores = []
    for row in rows:
        supplier = row[0]
        item_experience = row[1] or 0
        item_selection_rate = row[2] or 0
        feedback_adj = float(row[3] or 0)
        category_experience = row[4] or 0
        category_selection_rate = row[5] or 0

        raw_score = _calculate_score_from_parts(
            item_experience=item_experience,
            item_selection_rate=float(item_selection_rate),
            category_experience=category_experience,
            category_selection_rate=float(category_selection_rate),
            lat=float(supplier.lat) if supplier.lat else None,
            lng=float(supplier.lng) if supplier.lng else None,
            total_quotes=supplier.total_quotes or 0,
            awarded_quotes=supplier.awarded_quotes or 0,
            feedback_adj=feedback_adj,
            context=context,
        )
        multiplier = 1.0 if supplier.is_validated else 0.5
        final_score = raw_score * multiplier

        scores.append(SupplierScore(
            supplier_id=supplier.id,
            supplier_name=supplier.name,
            score_final=round(final_score, 2),
            is_validated=supplier.is_validated,
            score_breakdown={
                "experience": min(item_experience * 5, 40),
                "category": min(category_experience * 2, 20),
                "geo": _geo_score(
                    float(supplier.lat) if supplier.lat else None,
                    float(supplier.lng) if supplier.lng else None,
                    context,
                ),
                "track_record": _track_record(supplier.total_quotes or 0, supplier.awarded_quotes or 0),
                "feedback": feedback_adj,
                "validation_multiplier": multiplier,
            },
        ))

    scores.sort(key=lambda s: s.score_final, reverse=True)
    return scores[:limit]


def _calculate_score_from_parts(
    item_experience, item_selection_rate, category_experience, category_selection_rate,
    lat, lng, total_quotes, awarded_quotes, feedback_adj, context: ScoringContext
) -> float:
    # Experience with item: 0-40 pts
    experience = min(item_experience * 5, 40)
    if item_selection_rate > 0.3:
        experience += 15

    # Category specialization: 0-25 pts
    category = min(category_experience * 2, 20)
    if category_selection_rate > 0.4:
        category += 5

    geo = _geo_score(lat, lng, context)
    track = _track_record(total_quotes, awarded_quotes)

    return experience + category + geo + track + feedback_adj


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


def _track_record(total_quotes: int, awarded_quotes: int) -> float:
    score = 0.0
    if total_quotes > 50:
        score = 10.0
    elif total_quotes > 20:
        score = 7.0
    elif total_quotes > 5:
        score = 3.0

    if total_quotes > 0 and (awarded_quotes / total_quotes) > 0.3:
        score += 5.0

    return min(score, 15.0)


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
        * math.sin(dlng / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(a))

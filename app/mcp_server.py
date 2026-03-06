"""
Sygnode MCP Server — puerto 8001.
Expone el pipeline de procurement como tools MCP para agentes.
G4: API keys nunca en respuestas.
G6: Gemini solo con trigger explicito.
"""

import uuid
from contextlib import asynccontextmanager
from typing import Any

import fastmcp
from sqlalchemy import select, func

from app.database import AsyncSessionLocal
from app.models.case import DecisionCase, CaseTimelineEvent, CaseEvidence, CaseFulfillment
from app.models.intake import IntakeList, IntakeItem
from app.models.rfq import RFQ, RFQItem
from app.models.supplier import Supplier
from app.services.intake_service import create_intake_from_paste
from app.services.case_service import get_case_or_404, transition_case
from app.services.timeline_service import append_timeline_event, verify_chain_integrity
from app.services.evidence_service import compile_evidence_pack


# ── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(server: fastmcp.FastMCP):
    yield


# ── MCP Server ────────────────────────────────────────────────────────────────

mcp = fastmcp.FastMCP(
    name="Sygnode Core Engine",
    instructions=(
        "MCP server para el pipeline de procurement B2B de Sygnode. "
        "Permite crear, consultar y gestionar intakes, RFQs, casos y proveedores. "
        "Todas las operaciones son multi-tenant: siempre pasar org_id."
    ),
    lifespan=lifespan,
)


# ── Helper: sesion DB ─────────────────────────────────────────────────────────

def _db_session():
    return AsyncSessionLocal()


def _str_to_uuid(val: str) -> uuid.UUID:
    return uuid.UUID(val)


# ── Tools ─────────────────────────────────────────────────────────────────────

@mcp.tool
async def create_asset(
    asset_type: str,
    title: str,
    content: str,
    org_id: str,
    source: str = "mcp",
) -> dict[str, Any]:
    """
    Crea un asset en el pipeline (intake por defecto).
    asset_type: "intake" | "rfq"
    Retorna asset_id y tipo creado.
    """
    oid = _str_to_uuid(org_id)

    if asset_type == "intake":
        async with _db_session() as db:
            # Crear user stub con org_id para intake_service
            from app.models.user import User
            user_result = await db.execute(
                select(User).where(User.organization_id == oid).limit(1)
            )
            user = user_result.scalar_one_or_none()
            if not user:
                return {"error": f"No hay usuarios en org {org_id}"}

            intake, item_count = await create_intake_from_paste(
                db, content, source, user
            )
            await db.commit()
            return {
                "asset_id": str(intake.id),
                "asset_type": "intake",
                "item_count": item_count,
                "status": intake.validation_status,
            }

    if asset_type == "rfq":
        async with _db_session() as db:
            from app.models.user import User
            from app.services.rfq_service import create_rfq
            from app.schemas.rfq import RFQCreate, RFQItemCreate

            user_result = await db.execute(
                select(User).where(User.organization_id == oid).limit(1)
            )
            user = user_result.scalar_one_or_none()
            if not user:
                return {"error": f"No hay usuarios en org {org_id}"}

            rfq_data = RFQCreate(
                title=title,
                description=content,
                items=[RFQItemCreate(description=content, quantity="1", unit="u")],
            )
            rfq = await create_rfq(db, rfq_data, user)
            await db.commit()
            return {
                "asset_id": str(rfq.id),
                "asset_type": "rfq",
                "reference_code": rfq.reference_code,
                "status": rfq.status,
            }

    return {"error": f"asset_type desconocido: {asset_type}"}


@mcp.tool
async def search_assets(
    query: str,
    org_id: str,
    asset_type: str = "all",
    limit: int = 10,
) -> dict[str, Any]:
    """
    Busca assets en el pipeline por texto libre.
    asset_type: "intake" | "rfq" | "case" | "all"
    Retorna lista de assets con id, tipo, titulo y estado.
    """
    oid = _str_to_uuid(org_id)
    results = []

    async with _db_session() as db:
        if asset_type in ("intake", "all"):
            stmt = (
                select(IntakeList)
                .where(
                    IntakeList.organization_id == oid,
                    IntakeList.title.ilike(f"%{query}%"),
                )
                .limit(limit)
            )
            rows = (await db.execute(stmt)).scalars().all()
            results += [
                {"id": str(r.id), "type": "intake", "title": r.title, "status": r.validation_status}
                for r in rows
            ]

        if asset_type in ("rfq", "all"):
            stmt = (
                select(RFQ)
                .where(
                    RFQ.organization_id == oid,
                    RFQ.title.ilike(f"%{query}%"),
                )
                .limit(limit)
            )
            rows = (await db.execute(stmt)).scalars().all()
            results += [
                {"id": str(r.id), "type": "rfq", "title": r.title, "status": r.status}
                for r in rows
            ]

        if asset_type in ("case", "all"):
            stmt = (
                select(DecisionCase)
                .where(
                    DecisionCase.organization_id == oid,
                    DecisionCase.objeto_resumen.ilike(f"%{query}%"),
                )
                .limit(limit)
            )
            rows = (await db.execute(stmt)).scalars().all()
            results += [
                {
                    "id": str(r.id),
                    "type": "case",
                    "title": r.objeto_resumen or f"Caso {str(r.id)[:8]}",
                    "status": r.status,
                }
                for r in rows
            ]

    return {"results": results, "total": len(results)}


@mcp.tool
async def get_kanban(org_id: str) -> dict[str, Any]:
    """
    Retorna el estado actual del pipeline como tablero kanban.
    Columnas: intake_pendiente, en_cotizacion, casos_abiertos,
              casos_congelados, casos_archivados.
    """
    oid = _str_to_uuid(org_id)

    async with _db_session() as db:
        intake_pending = await db.scalar(
            select(func.count(IntakeList.id)).where(
                IntakeList.organization_id == oid,
                IntakeList.validation_status == "STAGED_PENDING_VALIDATION",
            )
        ) or 0

        en_cotizacion = await db.scalar(
            select(func.count(IntakeList.id)).where(
                IntakeList.organization_id == oid,
                IntakeList.status == "EN_COTIZACION",
            )
        ) or 0

        rfqs_active = await db.scalar(
            select(func.count(RFQ.id)).where(
                RFQ.organization_id == oid,
                RFQ.status.in_(["draft", "open", "sent"]),
            )
        ) or 0

        cases_open = await db.scalar(
            select(func.count(DecisionCase.id)).where(
                DecisionCase.organization_id == oid,
                DecisionCase.status == "OPEN",
            )
        ) or 0

        cases_frozen = await db.scalar(
            select(func.count(DecisionCase.id)).where(
                DecisionCase.organization_id == oid,
                DecisionCase.status == "FROZEN",
            )
        ) or 0

        cases_archived = await db.scalar(
            select(func.count(DecisionCase.id)).where(
                DecisionCase.organization_id == oid,
                DecisionCase.status == "ARCHIVED",
            )
        ) or 0

        # Work queue: 5 cases más recientes en OPEN
        wq_result = await db.execute(
            select(DecisionCase)
            .where(DecisionCase.organization_id == oid, DecisionCase.status == "OPEN")
            .order_by(DecisionCase.created_at.desc())
            .limit(5)
        )
        work_queue = [
            {"case_id": str(c.id), "title": c.objeto_resumen or f"Caso {str(c.id)[:8]}"}
            for c in wq_result.scalars().all()
        ]

    return {
        "columns": {
            "intake_pendiente": intake_pending,
            "en_cotizacion": en_cotizacion,
            "rfqs_activos": rfqs_active,
            "casos_abiertos": cases_open,
            "casos_congelados": cases_frozen,
            "casos_archivados": cases_archived,
        },
        "work_queue": work_queue,
    }


@mcp.tool
async def get_asset(asset_id: str, asset_type: str, org_id: str) -> dict[str, Any]:
    """
    Retorna detalle completo de un asset.
    asset_type: "intake" | "rfq" | "case"
    """
    oid = _str_to_uuid(org_id)
    aid = _str_to_uuid(asset_id)

    async with _db_session() as db:
        if asset_type == "intake":
            result = await db.execute(
                select(IntakeList).where(IntakeList.id == aid, IntakeList.organization_id == oid)
            )
            intake = result.scalar_one_or_none()
            if not intake:
                return {"error": "Intake no encontrado"}

            items_result = await db.execute(
                select(IntakeItem).where(IntakeItem.list_id == aid).order_by(IntakeItem.sort_order)
            )
            return {
                "id": str(intake.id),
                "type": "intake",
                "title": intake.title,
                "validation_status": intake.validation_status,
                "status": intake.status,
                "items": [
                    {"id": str(i.id), "description": i.raw_text, "quantity": str(i.quantity) if i.quantity else None}
                    for i in items_result.scalars().all()
                ],
            }

        if asset_type == "rfq":
            result = await db.execute(
                select(RFQ).where(RFQ.id == aid, RFQ.organization_id == oid)
            )
            rfq = result.scalar_one_or_none()
            if not rfq:
                return {"error": "RFQ no encontrado"}

            items_result = await db.execute(
                select(RFQItem).where(RFQItem.rfq_id == aid)
            )
            return {
                "id": str(rfq.id),
                "type": "rfq",
                "title": rfq.title,
                "status": rfq.status,
                "reference_code": rfq.reference_code,
                "items": [
                    {"description": i.description, "quantity": str(i.quantity) if i.quantity else None, "unit": i.unit}
                    for i in items_result.scalars().all()
                ],
            }

        if asset_type == "case":
            result = await db.execute(
                select(DecisionCase).where(DecisionCase.id == aid, DecisionCase.organization_id == oid)
            )
            case = result.scalar_one_or_none()
            if not case:
                return {"error": "Caso no encontrado"}

            chain = await verify_chain_integrity(db, aid)
            ev_result = await db.execute(
                select(func.count(CaseEvidence.id)).where(CaseEvidence.case_id == aid)
            )
            fulfillment_result = await db.execute(
                select(CaseFulfillment).where(CaseFulfillment.case_id == aid)
            )
            fulfillment = fulfillment_result.scalar_one_or_none()

            return {
                "id": str(case.id),
                "type": "case",
                "status": case.status,
                "objeto_resumen": case.objeto_resumen,
                "criticality": case.criticality,
                "evidence_count": ev_result.scalar() or 0,
                "chain_intact": chain["intact"],
                "fulfillment": {
                    "po_number": fulfillment.po_number,
                    "final_amount": str(fulfillment.final_amount),
                    "reconciliation_status": fulfillment.reconciliation_status,
                } if fulfillment else None,
            }

    return {"error": f"asset_type desconocido: {asset_type}"}


@mcp.tool
async def list_assets(
    org_id: str,
    asset_type: str,
    status: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """
    Lista assets paginados de una organización.
    asset_type: "intake" | "rfq" | "case" | "supplier"
    """
    oid = _str_to_uuid(org_id)

    async with _db_session() as db:
        if asset_type == "intake":
            stmt = select(IntakeList).where(IntakeList.organization_id == oid)
            if status:
                stmt = stmt.where(IntakeList.validation_status == status)
            stmt = stmt.order_by(IntakeList.created_at.desc()).limit(limit)
            rows = (await db.execute(stmt)).scalars().all()
            return {
                "items": [
                    {"id": str(r.id), "title": r.title, "status": r.validation_status, "created_at": r.created_at.isoformat()}
                    for r in rows
                ]
            }

        if asset_type == "rfq":
            stmt = select(RFQ).where(RFQ.organization_id == oid)
            if status:
                stmt = stmt.where(RFQ.status == status)
            stmt = stmt.order_by(RFQ.created_at.desc()).limit(limit)
            rows = (await db.execute(stmt)).scalars().all()
            return {
                "items": [
                    {"id": str(r.id), "title": r.title, "status": r.status, "reference_code": r.reference_code}
                    for r in rows
                ]
            }

        if asset_type == "case":
            stmt = select(DecisionCase).where(DecisionCase.organization_id == oid)
            if status:
                stmt = stmt.where(DecisionCase.status == status)
            stmt = stmt.order_by(DecisionCase.created_at.desc()).limit(limit)
            rows = (await db.execute(stmt)).scalars().all()
            return {
                "items": [
                    {"id": str(r.id), "status": r.status, "objeto_resumen": r.objeto_resumen, "criticality": r.criticality}
                    for r in rows
                ]
            }

        if asset_type == "supplier":
            stmt = select(Supplier).where(Supplier.organization_id == oid)
            if status == "validated":
                stmt = stmt.where(Supplier.is_validated == True)
            stmt = stmt.order_by(Supplier.name).limit(limit)
            rows = (await db.execute(stmt)).scalars().all()
            return {
                "items": [
                    {"id": str(r.id), "name": r.name, "rut": r.rut, "is_validated": r.is_validated}
                    for r in rows
                ]
            }

    return {"error": f"asset_type desconocido: {asset_type}"}


@mcp.tool
async def transition(
    asset_id: str,
    asset_type: str,
    to_status: str,
    org_id: str,
    reason: str | None = None,
) -> dict[str, Any]:
    """
    Transiciona un asset al siguiente estado.
    asset_type: "intake" | "case"
    Valida la maquina de estados antes de transicionar.
    """
    oid = _str_to_uuid(org_id)
    aid = _str_to_uuid(asset_id)

    async with _db_session() as db:
        if asset_type == "intake":
            from app.services.intake_service import transition_intake
            from app.models.user import User

            user_result = await db.execute(
                select(User).where(User.organization_id == oid).limit(1)
            )
            user = user_result.scalar_one_or_none()
            if not user:
                return {"error": "No hay usuarios en la organizacion"}

            try:
                intake = await transition_intake(db, aid, to_status, user)
                await db.commit()
                return {"asset_id": str(intake.id), "status": intake.status, "success": True}
            except ValueError as e:
                return {"error": str(e)}

        if asset_type == "case":
            from app.models.user import User

            user_result = await db.execute(
                select(User).where(User.organization_id == oid).limit(1)
            )
            user = user_result.scalar_one_or_none()
            if not user:
                return {"error": "No hay usuarios en la organizacion"}

            try:
                case = await transition_case(db, aid, to_status, user, reason)
                await db.commit()
                return {"asset_id": str(case.id), "status": case.status, "success": True}
            except Exception as e:
                return {"error": str(e)}

    return {"error": f"asset_type no soportado: {asset_type}"}


@mcp.tool
async def append_timeline(
    case_id: str,
    org_id: str,
    event_type: str,
    description: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Agrega un evento al timeline de un caso (G1: append-only).
    event_type debe ser uno de los tipos permitidos en el schema.
    """
    cid = _str_to_uuid(case_id)
    oid = _str_to_uuid(org_id)

    async with _db_session() as db:
        # Verify case belongs to org
        result = await db.execute(
            select(DecisionCase).where(DecisionCase.id == cid, DecisionCase.organization_id == oid)
        )
        case = result.scalar_one_or_none()
        if not case:
            return {"error": "Caso no encontrado"}

        event = await append_timeline_event(
            db=db,
            case_id=cid,
            event_type=event_type,
            description=description,
            metadata=metadata,
        )
        await db.commit()

        return {
            "event_id": str(event.id),
            "event_hash": event.event_hash,
            "event_type": event.event_type,
            "success": True,
        }


@mcp.tool
async def auto_process(
    asset_id: str,
    asset_type: str,
    org_id: str,
) -> dict[str, Any]:
    """
    Aprueba automaticamente un intake pendiente y crea su DecisionCase.
    Solo funciona con asset_type="intake" en estado STAGED_PENDING_VALIDATION.
    G6: NO llama Gemini automaticamente.
    """
    oid = _str_to_uuid(org_id)
    aid = _str_to_uuid(asset_id)

    if asset_type != "intake":
        return {"error": "auto_process solo soporta intake por ahora"}

    async with _db_session() as db:
        from app.models.user import User
        from app.services.intake_service import approve_intake

        user_result = await db.execute(
            select(User).where(User.organization_id == oid).limit(1)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            return {"error": "No hay usuarios en la organizacion"}

        result = await db.execute(
            select(IntakeList).where(IntakeList.id == aid, IntakeList.organization_id == oid)
        )
        intake = result.scalar_one_or_none()
        if not intake:
            return {"error": "Intake no encontrado"}

        if intake.validation_status != "STAGED_PENDING_VALIDATION":
            return {
                "error": f"Intake en estado {intake.validation_status}, no se puede aprobar automaticamente"
            }

        intake_obj, case = await approve_intake(db, aid, user)
        await db.commit()

        return {
            "intake_id": str(intake_obj.id),
            "case_id": str(case.id),
            "case_status": case.status,
            "success": True,
        }


# ── Entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import asyncio
    asyncio.run(mcp.run_http_async(
        transport="streamable-http",
        host="0.0.0.0",
        port=8001,
        log_level="info",
    ))

from datetime import datetime, date
from uuid import UUID
from pydantic import BaseModel, Field


class ClientCreate(BaseModel):
    razon_social: str = Field(..., max_length=255)
    rut: str = Field(..., max_length=12)
    direccion_comercial: str | None = None
    contrato_vigente: str = "NO"
    contrato_fecha_inicio: date | None = None
    contrato_fecha_termino: date | None = None
    contacto_nombre: str | None = None
    contacto_email: str | None = None
    contacto_telefono: str | None = None
    email_evidencias: str | None = None
    domain_match: str | None = None


class ClientUpdate(BaseModel):
    razon_social: str | None = None
    direccion_comercial: str | None = None
    contrato_vigente: str | None = None
    contacto_nombre: str | None = None
    contacto_email: str | None = None
    archived: bool | None = None


class ClientOut(BaseModel):
    id: UUID
    organization_id: UUID
    razon_social: str
    rut: str
    direccion_comercial: str | None = None
    contrato_vigente: str
    contacto_nombre: str | None = None
    contacto_email: str | None = None
    domain_match: str | None = None
    archived: bool
    created_at: datetime

    model_config = {"from_attributes": True}

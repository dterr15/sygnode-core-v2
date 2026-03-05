from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class OrganizationOut(BaseModel):
    id: UUID
    rut: str
    name: str
    email_contact: str | None = None
    phone: str | None = None
    industry: str | None = None
    city: str | None = None
    region: str | None = None
    country: str = "CL"
    subscription_status: str
    subscription_tier: str
    max_users: int
    created_at: datetime

    model_config = {"from_attributes": True}

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class UserOut(BaseModel):
    id: UUID
    organization_id: UUID
    email: str
    name: str
    role: str
    status: str
    email_verified: bool
    last_login_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}

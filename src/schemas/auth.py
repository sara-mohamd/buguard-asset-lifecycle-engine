import uuid
from pydantic import BaseModel
from src.models.auth import Role

class CurrentTenant(BaseModel):
    tenant_id: uuid.UUID
    role: Role

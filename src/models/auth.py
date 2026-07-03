import uuid
import enum
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID

from src.database import Base

class Role(str, enum.Enum):
    admin = "admin"
    scanner = "scanner"
    viewer = "viewer"

class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hashed_key = Column(String, nullable=False, unique=True, index=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    role = Column(String, nullable=False, default=Role.viewer.value)

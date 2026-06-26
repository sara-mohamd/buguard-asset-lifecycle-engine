import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Enum, UniqueConstraint, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

from src.database import Base
import enum

class AssetType(str, enum.Enum):
    domain = "domain"
    subdomain = "subdomain"
    ip_address = "ip_address"
    service = "service"
    certificate = "certificate"
    technology = "technology"

class AssetStatus(str, enum.Enum):
    active = "active"
    stale = "stale"
    archived = "archived"

class Asset(Base):
    __tablename__ = "assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = Column(String, nullable=False, index=True)
    value = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default=AssetStatus.active.value)
    
    first_seen = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    last_seen = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    
    source = Column(String, nullable=False, default="manual")
    tags = Column(ARRAY(String), default=list, nullable=False)
    metadata_ = Column("metadata", JSONB, default=dict, nullable=False) # metadata is a reserved attribute in SQLAlchemy Base

    __table_args__ = (
        UniqueConstraint('type', 'value', name='uix_asset_type_value'),
    )

class AssetRelationship(Base):
    __tablename__ = "asset_relationships"
    
    source_asset_id = Column(UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True)
    target_asset_id = Column(UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), primary_key=True)
    type = Column(String, nullable=False, primary_key=True)
    first_seen = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

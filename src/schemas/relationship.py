from pydantic import BaseModel, ConfigDict
import uuid
from datetime import datetime
from typing import List

from src.schemas.asset import AssetResponse

class RelationshipCreate(BaseModel):
    source_asset_id: uuid.UUID
    target_asset_id: uuid.UUID
    type: str

class RelationshipResponse(BaseModel):
    source_asset_id: uuid.UUID
    target_asset_id: uuid.UUID
    type: str
    first_seen: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class NeighborResponse(BaseModel):
    asset: AssetResponse
    relationship_type: str
    direction: str

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class AssetWithNeighborsResponse(AssetResponse):
    neighbors: List[NeighborResponse] = []

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

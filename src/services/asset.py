import uuid
from datetime import datetime, timezone
from typing import List, Tuple, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_, and_, insert, update, func

from src.models.asset import Asset, AssetStatus, AssetRelationship
from src.schemas.asset import AssetCreate
from src.schemas.relationship import RelationshipCreate
from src.exceptions import AssetNotFoundError, AssetDuplicateError

def deep_merge_dicts(existing: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deeply merges incoming into existing.
    If both values are dicts, it recurses.
    Otherwise, incoming overrides existing.
    """
    merged = dict(existing)
    for key, value in incoming.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = deep_merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged

async def create_asset(db: AsyncSession, asset_in: AssetCreate) -> Asset:
    """
    Creates a new asset in the database.
    Normalizes tags and handles unique constraint violations.
    """
    # Normalize tags: lowercased, stripped, no duplicates
    normalized_tags = list({tag.strip().lower() for tag in asset_in.tags if tag.strip()})
    
    # Safely extract string values regardless of whether the field is an Enum or an object (like IPvAnyAddress)
    asset_type = asset_in.type if isinstance(asset_in.type, str) else asset_in.type.value
    asset_status = asset_in.status if isinstance(asset_in.status, str) else asset_in.status.value
    
    asset = Asset(
        type=asset_type,
        value=str(asset_in.value),
        status=asset_status,
        source=asset_in.source,
        tags=normalized_tags,
        metadata_=asset_in.metadata,
        first_seen=datetime.now(timezone.utc),
        last_seen=datetime.now(timezone.utc)
    )
    
    db.add(asset)
    try:
        await db.commit()
        await db.refresh(asset)
        return asset
    except IntegrityError as e:
        await db.rollback()
        # SQLAlchemy raises IntegrityError for unique constraint violations
        raise AssetDuplicateError(f"Asset of type '{asset_in.type}' with value '{asset_in.value}' already exists.") from e

async def get_asset(db: AsyncSession, asset_id: uuid.UUID) -> Asset:
    """
    Retrieves an asset by its ID. Raises AssetNotFoundError if it does not exist.
    """
    result = await db.execute(select(Asset).where(Asset.id == asset_id))
    asset = result.scalar_one_or_none()
    
    if not asset:
        raise AssetNotFoundError(str(asset_id))
        
    return asset

def _escape_ilike(value: str) -> str:
    """Escape SQL ILIKE wildcard metacharacters."""
    return (
        value
        .replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )

async def list_assets(
    db: AsyncSession,
    limit: int = 100,
    offset: int = 0,
    type_: Optional[str] = None,
    status: Optional[str] = None,
    tag: Optional[str] = None,
    value: Optional[str] = None
) -> Tuple[List[Asset], int]:
    """
    List assets with pagination and advanced filtering.
    Returns a tuple of (items, total_count).
    """
    conditions = []
    if type_:
        conditions.append(Asset.type == type_)
    if status:
        conditions.append(Asset.status == status)
    if tag:
        conditions.append(Asset.tags.any(tag))
    if value:
        escaped = _escape_ilike(value)
        conditions.append(Asset.value.ilike(f"%{escaped}%", escape="\\"))

    # Build base where clause
    where_clause = and_(*conditions) if conditions else None

    # Count query
    count_query = select(func.count(Asset.id))
    if where_clause is not None:
        count_query = count_query.where(where_clause)
    
    total = await db.scalar(count_query) or 0

    # Data query
    query = select(Asset)
    if where_clause is not None:
        query = query.where(where_clause)
    
    query = query.order_by(Asset.first_seen.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    items = result.scalars().all()

    return list(items), total

async def bulk_import_assets(db: AsyncSession, valid_assets: List[AssetCreate]) -> Tuple[int, int]:
    """
    Idempotent bulk ingestion engine.
    Uses SQLAlchemy Core for high-performance batch operations.
    Returns (created_count, updated_count).
    """
    if not valid_assets:
        return 0, 0
        
    # Gather types and values to check for existing records
    identities = []
    asset_map = {}
    for a in valid_assets:
        a_type = a.type if isinstance(a.type, str) else a.type.value
        a_value = str(a.value)
        identities.append((a_type, a_value))
        # Keep the last incoming version if duplicates exist in the same batch
        asset_map[(a_type, a_value)] = a

    # Fetch existing using Core select
    conditions = [and_(Asset.type == t, Asset.value == v) for t, v in identities]
    
    query = select(Asset).where(or_(*conditions))
    
    result = await db.execute(query)
    existing_records = result.scalars().all()
    
    existing_map = {(r.type, r.value): r for r in existing_records}
    
    insert_data = []
    update_data = []
    now = datetime.now(timezone.utc)
    
    for (a_type, a_value), asset_in in asset_map.items():
        if (a_type, a_value) in existing_map:
            # Update existing
            existing = existing_map[(a_type, a_value)]
            
            new_status = AssetStatus.active.value if existing.status == AssetStatus.stale.value else existing.status
            
            normalized_tags = {tag.strip().lower() for tag in asset_in.tags if tag.strip()}
            merged_tags = list(set(existing.tags) | normalized_tags)
            
            merged_metadata = deep_merge_dicts(existing.metadata_, asset_in.metadata)
            
            update_data.append({
                "id": existing.id,
                "type": existing.type,
                "value": existing.value,
                "source": existing.source,
                "first_seen": existing.first_seen,
                "status": new_status,
                "last_seen": now,
                "tags": merged_tags,
                "metadata_": merged_metadata
            })
        else:
            # Create new
            normalized_tags = list({tag.strip().lower() for tag in asset_in.tags if tag.strip()})
            asset_status = asset_in.status if isinstance(asset_in.status, str) else asset_in.status.value
            insert_data.append({
                "id": uuid.uuid4(),
                "type": a_type,
                "value": a_value,
                "status": asset_status,
                "source": asset_in.source,
                "tags": normalized_tags,
                "metadata_": asset_in.metadata,
                "first_seen": now,
                "last_seen": now
            })
            
    # Execute batch operations
    if insert_data:
        await db.execute(insert(Asset), insert_data)
        
    if update_data:
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        stmt = pg_insert(Asset).values(update_data)
        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={
                "status": stmt.excluded.status,
                "last_seen": stmt.excluded.last_seen,
                "tags": stmt.excluded.tags,
                "metadata": stmt.excluded.metadata,
            },
        )
        await db.execute(stmt)
        
    if insert_data or update_data:
        await db.commit()
        
    return len(insert_data), len(update_data)

async def create_relationship(db: AsyncSession, rel_in: RelationshipCreate) -> AssetRelationship:
    """
    Creates a new relationship between two assets.
    """
    source_asset = await db.get(Asset, rel_in.source_asset_id)
    target_asset = await db.get(Asset, rel_in.target_asset_id)
    if not source_asset:
        raise AssetNotFoundError(str(rel_in.source_asset_id))
    if not target_asset:
        raise AssetNotFoundError(str(rel_in.target_asset_id))

    query = select(AssetRelationship).where(
        and_(
            AssetRelationship.source_asset_id == rel_in.source_asset_id,
            AssetRelationship.target_asset_id == rel_in.target_asset_id,
            AssetRelationship.type == rel_in.type
        )
    )
    result = await db.execute(query)
    existing = result.scalar_one_or_none()
    
    if existing:
        return existing
        
    relationship = AssetRelationship(
        source_asset_id=rel_in.source_asset_id,
        target_asset_id=rel_in.target_asset_id,
        type=rel_in.type,
        first_seen=datetime.now(timezone.utc)
    )
    
    db.add(relationship)
    await db.commit()
    await db.refresh(relationship)
    return relationship

async def get_asset_with_neighbors(db: AsyncSession, asset_id: uuid.UUID) -> dict:
    """
    Retrieves an asset along with its first-degree graph neighbors.
    Returns a dictionary suitable for AssetWithNeighborsResponse.
    """
    asset = await get_asset(db, asset_id)
    
    outbound_query = select(AssetRelationship, Asset).join(
        Asset, AssetRelationship.target_asset_id == Asset.id
    ).where(AssetRelationship.source_asset_id == asset_id)
    outbound_result = await db.execute(outbound_query)
    outbound_records = outbound_result.all()
    
    inbound_query = select(AssetRelationship, Asset).join(
        Asset, AssetRelationship.source_asset_id == Asset.id
    ).where(AssetRelationship.target_asset_id == asset_id)
    inbound_result = await db.execute(inbound_query)
    inbound_records = inbound_result.all()
    
    neighbors = []
    
    for rel, target_asset in outbound_records:
        neighbors.append({
            "asset": target_asset,
            "relationship_type": rel.type,
            "direction": "outbound"
        })
        
    for rel, source_asset in inbound_records:
        neighbors.append({
            "asset": source_asset,
            "relationship_type": rel.type,
            "direction": "inbound"
        })
        
    return {
        "id": asset.id,
        "type": asset.type,
        "value": asset.value,
        "status": asset.status,
        "source": asset.source,
        "tags": asset.tags,
        "metadata": asset.metadata_,
        "first_seen": asset.first_seen,
        "last_seen": asset.last_seen,
        "neighbors": neighbors
    }

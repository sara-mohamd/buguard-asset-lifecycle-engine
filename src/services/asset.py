import uuid
from datetime import datetime, timezone
from typing import List, Tuple, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_, and_, insert, update, func

from src.models.asset import Asset, AssetStatus, AssetRelationship
from src.schemas.asset import AssetCreate, AssetUpdate
from src.schemas.relationship import RelationshipCreate
from src.exceptions import AssetNotFoundError, AssetDuplicateError

def deep_merge_dicts(existing: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(existing)
    for key, value in incoming.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = deep_merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged

async def create_asset(db: AsyncSession, tenant_id: uuid.UUID, asset_in: AssetCreate) -> Asset:
    normalized_tags = list({tag.strip().lower() for tag in asset_in.tags if tag.strip()})
    
    asset_type = asset_in.type if isinstance(asset_in.type, str) else asset_in.type.value
    asset_status = asset_in.status if isinstance(asset_in.status, str) else asset_in.status.value
    
    asset = Asset(
        tenant_id=tenant_id,
        type=asset_type,
        value=str(asset_in.value),
        status=asset_status,
        source=asset_in.source,
        tags=normalized_tags,
        metadata_=asset_in.metadata,
        first_seen=datetime.now(timezone.utc),
        last_seen=datetime.now(timezone.utc)
    )
    
    try:
        async with db.begin_nested():
            db.add(asset)
            await db.flush()
    except IntegrityError as e:
        raise AssetDuplicateError(f"Asset of type '{asset_in.type}' with value '{asset_in.value}' already exists.") from e
        
    await db.commit()
    await db.refresh(asset)
    return asset

async def get_asset(db: AsyncSession, tenant_id: uuid.UUID, asset_id: uuid.UUID) -> Asset:
    result = await db.execute(select(Asset).where(and_(Asset.id == asset_id, Asset.tenant_id == tenant_id)))
    asset = result.scalar_one_or_none()
    
    if not asset:
        raise AssetNotFoundError(str(asset_id))
        
    return asset

def _escape_ilike(value: str) -> str:
    return (
        value
        .replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )

async def list_assets(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    limit: int = 100,
    offset: int = 0,
    type_: Optional[str] = None,
    status: Optional[str] = None,
    tag: Optional[str] = None,
    value: Optional[str] = None
) -> Tuple[List[Asset], int]:
    conditions = [Asset.tenant_id == tenant_id]
    if type_:
        conditions.append(Asset.type == type_)
    if status:
        conditions.append(Asset.status == status)
    if tag:
        conditions.append(Asset.tags.any(tag))
    if value:
        escaped = _escape_ilike(value)
        conditions.append(Asset.value.ilike(f"%{escaped}%", escape="\\"))

    where_clause = and_(*conditions)

    count_query = select(func.count(Asset.id)).where(where_clause)
    total = await db.scalar(count_query) or 0

    query = select(Asset).where(where_clause).order_by(Asset.first_seen.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    items = result.scalars().all()

    return list(items), total

async def bulk_import_assets(db: AsyncSession, tenant_id: uuid.UUID, valid_assets: List[AssetCreate]) -> Tuple[int, int]:
    if not valid_assets:
        return 0, 0
        
    identities = []
    asset_map = {}
    for a in valid_assets:
        a_type = a.type if isinstance(a.type, str) else a.type.value
        a_value = str(a.value)
        identities.append((a_type, a_value))
        asset_map[(a_type, a_value)] = a

    conditions = [and_(Asset.type == t, Asset.value == v) for t, v in identities]
    
    query = select(Asset).where(and_(Asset.tenant_id == tenant_id, or_(*conditions)))
    
    result = await db.execute(query)
    existing_records = result.scalars().all()
    
    existing_map = {(r.type, r.value): r for r in existing_records}
    
    insert_data = []
    update_data = []
    now = datetime.now(timezone.utc)
    
    for (a_type, a_value), asset_in in asset_map.items():
        if (a_type, a_value) in existing_map:
            existing = existing_map[(a_type, a_value)]
            
            new_status = AssetStatus.active.value if existing.status == AssetStatus.stale.value else existing.status
            
            normalized_tags = {tag.strip().lower() for tag in asset_in.tags if tag.strip()}
            merged_tags = list(set(existing.tags) | normalized_tags)
            
            merged_metadata = deep_merge_dicts(existing.metadata_, asset_in.metadata)
            
            update_data.append({
                "id": existing.id,
                "tenant_id": tenant_id,
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
            normalized_tags = list({tag.strip().lower() for tag in asset_in.tags if tag.strip()})
            asset_status = asset_in.status if isinstance(asset_in.status, str) else asset_in.status.value
            insert_data.append({
                "id": uuid.uuid4(),
                "tenant_id": tenant_id,
                "type": a_type,
                "value": a_value,
                "status": asset_status,
                "source": asset_in.source,
                "tags": normalized_tags,
                "metadata_": asset_in.metadata,
                "first_seen": now,
                "last_seen": now
            })
            
    if insert_data:
        await db.execute(insert(Asset), insert_data)
        
    if update_data:
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        stmt = pg_insert(Asset).values(update_data)
        stmt = stmt.on_conflict_do_update(
            index_elements=["tenant_id", "type", "value"],
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

async def create_relationship(db: AsyncSession, tenant_id: uuid.UUID, rel_in: RelationshipCreate) -> AssetRelationship:
    source_asset = await get_asset(db, tenant_id, rel_in.source_asset_id)
    target_asset = await get_asset(db, tenant_id, rel_in.target_asset_id)

    query = select(AssetRelationship).where(
        and_(
            AssetRelationship.tenant_id == tenant_id,
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
        tenant_id=tenant_id,
        source_asset_id=rel_in.source_asset_id,
        target_asset_id=rel_in.target_asset_id,
        type=rel_in.type,
        first_seen=datetime.now(timezone.utc)
    )
    
    db.add(relationship)
    await db.commit()
    await db.refresh(relationship)
    return relationship

async def update_asset(db: AsyncSession, tenant_id: uuid.UUID, asset_id: uuid.UUID, asset_in: AssetUpdate) -> Asset:
    asset = await get_asset(db, tenant_id, asset_id)
    
    if asset_in.status is not None:
        asset.status = asset_in.status if isinstance(asset_in.status, str) else asset_in.status.value
        
    if asset_in.tags is not None:
        normalized_tags = list({tag.strip().lower() for tag in asset_in.tags if tag.strip()})
        asset.tags = normalized_tags
        
    if asset_in.metadata is not None:
        asset.metadata_ = asset_in.metadata
        
    asset.last_seen = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(asset)
    return asset

async def hard_delete_asset(db: AsyncSession, tenant_id: uuid.UUID, asset_id: uuid.UUID) -> None:
    asset = await get_asset(db, tenant_id, asset_id)
    await db.delete(asset)
    await db.commit()

async def get_asset_with_neighbors(db: AsyncSession, tenant_id: uuid.UUID, asset_id: uuid.UUID) -> dict:
    asset = await get_asset(db, tenant_id, asset_id)
    
    outbound_query = select(AssetRelationship, Asset).join(
        Asset, AssetRelationship.target_asset_id == Asset.id
    ).where(
        and_(
            AssetRelationship.tenant_id == tenant_id,
            AssetRelationship.source_asset_id == asset_id,
            Asset.status != AssetStatus.archived.value
        )
    )
    outbound_result = await db.execute(outbound_query)
    outbound_records = outbound_result.all()
    
    inbound_query = select(AssetRelationship, Asset).join(
        Asset, AssetRelationship.source_asset_id == Asset.id
    ).where(
        and_(
            AssetRelationship.tenant_id == tenant_id,
            AssetRelationship.target_asset_id == asset_id,
            Asset.status != AssetStatus.archived.value
        )
    )
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

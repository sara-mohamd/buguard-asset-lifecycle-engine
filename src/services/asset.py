import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError

from src.models.asset import Asset
from src.schemas.asset import AssetCreate
from src.exceptions import AssetNotFoundError, AssetDuplicateError

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

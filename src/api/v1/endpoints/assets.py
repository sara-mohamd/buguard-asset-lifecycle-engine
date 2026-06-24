import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.schemas.asset import AssetCreate, AssetResponse
from src.services import asset as asset_service
from src.exceptions import AssetNotFoundError, AssetDuplicateError

router = APIRouter()

@router.post("/", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def create_asset(asset_in: AssetCreate, db: AsyncSession = Depends(get_db)):
    """
    Create a new asset.
    """
    try:
        asset = await asset_service.create_asset(db=db, asset_in=asset_in)
        return asset
    except AssetDuplicateError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(asset_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Retrieve an asset by its ID.
    """
    try:
        asset = await asset_service.get_asset(db=db, asset_id=asset_id)
        return asset
    except AssetNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

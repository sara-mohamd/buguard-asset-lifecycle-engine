import uuid
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import TypeAdapter, ValidationError
from src.database import get_db
from src.schemas.asset import AssetCreate, AssetResponse
from src.schemas.import_report import ImportReport, RejectedRecord
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

@router.post("/import", response_model=ImportReport, status_code=status.HTTP_200_OK)
async def import_assets(payload: List[Dict[str, Any]], db: AsyncSession = Depends(get_db)):
    """
    Idempotent bulk ingestion endpoint.
    Processes assets, merging tags and metadata for existing ones, and isolates validation failures.
    """
    valid_assets = []
    rejected_records = []
    adapter = TypeAdapter(AssetCreate)
    
    for idx, item in enumerate(payload):
        try:
            asset = adapter.validate_python(item)
            valid_assets.append(asset)
        except ValidationError as e:
            rejected_records.append(
                RejectedRecord(
                    index=idx,
                    record=item,
                    errors=e.errors(include_url=False, include_context=False, include_input=False)
                )
            )
            
    created, updated = await asset_service.bulk_import_assets(db=db, valid_assets=valid_assets)
    
    return ImportReport(
        total_analyzed=len(payload),
        successful_creates=created,
        successful_updates=updated,
        rejected_records=rejected_records
    )

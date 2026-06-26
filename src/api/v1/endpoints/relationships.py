from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db
from src.schemas.relationship import RelationshipCreate, RelationshipResponse
from src.services import asset as asset_service
from src.exceptions import AssetNotFoundError

router = APIRouter()

@router.post("/", response_model=RelationshipResponse, status_code=status.HTTP_201_CREATED)
async def create_relationship(rel_in: RelationshipCreate, db: AsyncSession = Depends(get_db)):
    """
    Create a new relationship between two assets.
    """
    try:
        relationship = await asset_service.create_relationship(db=db, rel_in=rel_in)
        return relationship
    except AssetNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

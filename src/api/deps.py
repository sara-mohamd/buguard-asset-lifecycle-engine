import hashlib
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from src.database import get_db
from src.models.auth import ApiKey
from src.schemas.auth import CurrentTenant

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(
    api_key: str = Depends(api_key_header),
    db: AsyncSession = Depends(get_db)
) -> CurrentTenant:
    """
    Validate the incoming X-API-Key header against the database.
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
        )
    
    hashed_key = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
    
    result = await db.execute(select(ApiKey).where(ApiKey.hashed_key == hashed_key))
    db_api_key = result.scalar_one_or_none()
    
    if not db_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
        )
        
    return CurrentTenant(tenant_id=db_api_key.tenant_id, role=db_api_key.role)

def require_role(allowed_roles: List[str]):
    """
    Dependency factory to enforce RBAC roles.
    """
    def role_checker(current_tenant: CurrentTenant = Depends(verify_api_key)):
        if current_tenant.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
            )
        return current_tenant
    return role_checker

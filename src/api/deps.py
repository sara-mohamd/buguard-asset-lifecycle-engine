from fastapi import Depends, HTTPException, status
import hmac
from fastapi.security import APIKeyHeader
from src.config import get_settings, Settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_api_key(
    api_key: str = Depends(api_key_header),
    settings: Settings = Depends(get_settings)
) -> str:
    """
    Validate the incoming X-API-Key header against the configured API_KEY.
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
        )
    # Constant-time comparison prevents timing-oracle attacks
    if not hmac.compare_digest(api_key.encode("utf-8"), settings.api_key.encode("utf-8")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
        )
    return api_key

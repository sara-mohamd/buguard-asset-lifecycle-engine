import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_auth_missing_api_key(unauth_client: AsyncClient):
    payload = {
        "type": "domain",
        "value": "example.com"
    }
    # Test Create Asset
    r1 = await unauth_client.post("/api/v1/assets/", json=payload)
    assert r1.status_code == 401
    
    # Test Import
    r2 = await unauth_client.post("/api/v1/assets/import", json=[payload])
    assert r2.status_code == 401
    
    # Test Relationship
    rel_payload = {
        "source_asset_id": "12345678-1234-5678-1234-567812345678",
        "target_asset_id": "12345678-1234-5678-1234-567812345678",
        "type": "resolves_to"
    }
    r3 = await unauth_client.post("/api/v1/relationships/", json=rel_payload)
    assert r3.status_code == 401

@pytest.mark.asyncio
async def test_auth_invalid_api_key(unauth_client: AsyncClient):
    payload = {
        "type": "domain",
        "value": "example.com"
    }
    headers = {"X-API-Key": "invalid_key"}
    
    r1 = await unauth_client.post("/api/v1/assets/", json=payload, headers=headers)
    assert r1.status_code == 401

@pytest.mark.asyncio
async def test_auth_valid_api_key(client: AsyncClient):
    payload = {
        "type": "domain",
        "value": "valid-auth-test.com"
    }
    
    # The 'client' fixture is pre-configured with the valid X-API-Key header
    r1 = await client.post("/api/v1/assets/", json=payload)
    assert r1.status_code == 201
    assert r1.json()["value"] == "valid-auth-test.com"

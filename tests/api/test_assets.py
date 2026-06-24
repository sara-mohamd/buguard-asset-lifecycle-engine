import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_asset_success(client: AsyncClient):
    payload = {
        "type": "domain",
        "value": "example.com",
        "status": "active",
        "source": "manual",
        "tags": ["test", "demo"],
        "metadata": {"registrar": "GoDaddy"}
    }
    
    response = await client.post("/api/v1/assets/", json=payload)
    assert response.status_code == 201
    data = response.json()
    
    assert data["type"] == "domain"
    assert data["value"] == "example.com"
    assert "id" in data
    assert "first_seen" in data
    assert "last_seen" in data

@pytest.mark.asyncio
async def test_create_asset_duplicate(client: AsyncClient):
    payload = {
        "type": "ip_address",
        "value": "192.168.1.1",
    }
    
    # First creation should succeed
    response = await client.post("/api/v1/assets/", json=payload)
    assert response.status_code == 201
    
    # Second creation with same type and value should fail due to unique constraint
    response2 = await client.post("/api/v1/assets/", json=payload)
    assert response2.status_code == 409
    assert "already exists" in response2.json()["detail"]

@pytest.mark.asyncio
async def test_create_asset_validation_error(client: AsyncClient):
    payload = {
        "type": "invalid_type", # Not in Enum
        "value": "example.com"
    }
    
    response = await client.post("/api/v1/assets/", json=payload)
    assert response.status_code == 422 # Pydantic validation error

@pytest.mark.asyncio
async def test_get_asset_success(client: AsyncClient):
    payload = {
        "type": "domain",
        "value": "test-get.com",
    }
    
    create_response = await client.post("/api/v1/assets/", json=payload)
    asset_id = create_response.json()["id"]
    
    response = await client.get(f"/api/v1/assets/{asset_id}")
    assert response.status_code == 200
    assert response.json()["id"] == asset_id
    assert response.json()["value"] == "test-get.com"

@pytest.mark.asyncio
async def test_get_asset_not_found(client: AsyncClient):
    # Using a random UUID
    random_uuid = "123e4567-e89b-12d3-a456-426614174000"
    response = await client.get(f"/api/v1/assets/{random_uuid}")
    assert response.status_code == 404

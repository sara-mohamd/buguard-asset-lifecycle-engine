import pytest
import pytest_asyncio
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

@pytest_asyncio.fixture
async def setup_assets(client: AsyncClient):
    # Create diverse set of assets
    assets = [
        {"type": "domain", "value": "test-list-1.com", "status": "active", "tags": ["prod", "frontend"]},
        {"type": "domain", "value": "test-list-2.com", "status": "stale", "tags": ["dev", "backend"]},
        {"type": "subdomain", "value": "api.test-list-1.com", "status": "active", "tags": ["prod", "api"]},
        {"type": "ip_address", "value": "10.0.0.1", "status": "active", "tags": ["prod", "internal"]},
        {"type": "ip_address", "value": "10.0.0.2", "status": "archived", "tags": ["dev", "internal"]},
    ]
    for p in assets:
        await client.post("/api/v1/assets/", json=p)

@pytest.mark.asyncio
async def test_list_assets_pagination(client: AsyncClient, setup_assets):
    # Test limit and offset
    response1 = await client.get("/api/v1/assets/?limit=2&offset=0")
    assert response1.status_code == 200
    data1 = response1.json()
    assert len(data1["items"]) == 2
    assert data1["total"] >= 5

    response2 = await client.get("/api/v1/assets/?limit=2&offset=2")
    assert response2.status_code == 200
    data2 = response2.json()
    assert len(data2["items"]) == 2

    # Verify we got different items
    ids1 = {i["id"] for i in data1["items"]}
    ids2 = {i["id"] for i in data2["items"]}
    assert ids1.isdisjoint(ids2)

@pytest.mark.asyncio
async def test_list_assets_filter_type_status(client: AsyncClient, setup_assets):
    response = await client.get("/api/v1/assets/?type=domain&status=active")
    assert response.status_code == 200
    data = response.json()
    
    # Should find 'test-list-1.com'
    assert len(data["items"]) >= 1
    for item in data["items"]:
        assert item["type"] == "domain"
        assert item["status"] == "active"

@pytest.mark.asyncio
async def test_list_assets_filter_tag(client: AsyncClient, setup_assets):
    response = await client.get("/api/v1/assets/?tag=prod")
    assert response.status_code == 200
    data = response.json()
    
    # Should find 'test-list-1.com', 'api.test-list-1.com', '10.0.0.1'
    assert len(data["items"]) >= 3
    for item in data["items"]:
        assert "prod" in item["tags"]

@pytest.mark.asyncio
async def test_list_assets_filter_value_substring(client: AsyncClient, setup_assets):
    response = await client.get("/api/v1/assets/?value=test-list")
    assert response.status_code == 200
    data = response.json()
    
    # Should find 'test-list-1.com', 'test-list-2.com', 'api.test-list-1.com'
    assert len(data["items"]) >= 3
    for item in data["items"]:
        assert "test-list" in item["value"].lower()

@pytest.mark.asyncio
async def test_update_asset(client: AsyncClient):
    payload = {
        "type": "domain",
        "value": "update-test.com",
    }
    create_response = await client.post("/api/v1/assets/", json=payload)
    asset_id = create_response.json()["id"]
    
    update_payload = {
        "status": "archived",
        "tags": ["updated"]
    }
    
    response = await client.put(f"/api/v1/assets/{asset_id}", json=update_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "archived"
    assert "updated" in data["tags"]

@pytest.mark.asyncio
async def test_delete_asset(client: AsyncClient):
    payload = {
        "type": "domain",
        "value": "delete-test.com",
    }
    create_response = await client.post("/api/v1/assets/", json=payload)
    asset_id = create_response.json()["id"]
    
    response = await client.delete(f"/api/v1/assets/{asset_id}")
    assert response.status_code == 204
    
    # Verify it is deleted
    get_response = await client.get(f"/api/v1/assets/{asset_id}")
    assert get_response.status_code == 404

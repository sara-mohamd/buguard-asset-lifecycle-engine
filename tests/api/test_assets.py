import pytest
import pytest_asyncio
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_asset_success(client: AsyncClient):
    # Arrange
    payload = {
        "type": "domain",
        "value": "example.com",
        "status": "active",
        "source": "manual",
        "tags": ["test", "demo"],
        "metadata": {"registrar": "GoDaddy"}
    }
    
    # Act
    response = await client.post("/api/v1/assets/", json=payload)
    
    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["type"] == "domain"
    assert data["value"] == "example.com"
    assert "id" in data
    assert "first_seen" in data
    assert "last_seen" in data

@pytest.mark.asyncio
async def test_create_asset_duplicate(client: AsyncClient):
    # Arrange
    payload = {
        "type": "ip_address",
        "value": "192.168.1.1",
    }
    await client.post("/api/v1/assets/", json=payload)
    
    # Act
    response = await client.post("/api/v1/assets/", json=payload)
    
    # Assert
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]

@pytest.mark.asyncio
async def test_create_asset_validation_error(client: AsyncClient):
    # Arrange
    payload = {
        "type": "invalid_type",
        "value": "example.com"
    }
    
    # Act
    response = await client.post("/api/v1/assets/", json=payload)
    
    # Assert
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_get_asset_success(client: AsyncClient):
    # Arrange
    payload = {
        "type": "domain",
        "value": "test-get.com",
    }
    create_response = await client.post("/api/v1/assets/", json=payload)
    asset_id = create_response.json()["id"]
    
    # Act
    response = await client.get(f"/api/v1/assets/{asset_id}")
    
    # Assert
    assert response.status_code == 200
    assert response.json()["id"] == asset_id
    assert response.json()["value"] == "test-get.com"

@pytest.mark.asyncio
async def test_get_asset_not_found(client: AsyncClient):
    # Arrange
    random_uuid = "123e4567-e89b-12d3-a456-426614174000"
    
    # Act
    response = await client.get(f"/api/v1/assets/{random_uuid}")
    
    # Assert
    assert response.status_code == 404

@pytest_asyncio.fixture
async def setup_assets(client: AsyncClient):
    # Arrange
    await client.post("/api/v1/assets/", json={"type": "domain", "value": "test-list-1.com", "status": "active", "tags": ["prod", "frontend"]})
    await client.post("/api/v1/assets/", json={"type": "domain", "value": "test-list-2.com", "status": "stale", "tags": ["dev", "backend"]})
    await client.post("/api/v1/assets/", json={"type": "subdomain", "value": "api.test-list-1.com", "status": "active", "tags": ["prod", "api"]})
    await client.post("/api/v1/assets/", json={"type": "ip_address", "value": "10.0.0.1", "status": "active", "tags": ["prod", "internal"]})
    await client.post("/api/v1/assets/", json={"type": "ip_address", "value": "10.0.0.2", "status": "archived", "tags": ["dev", "internal"]})

@pytest.mark.asyncio
async def test_list_assets_pagination(client: AsyncClient, setup_assets):
    # Arrange
    # (Setup handled by fixture)
    
    # Act
    response1 = await client.get("/api/v1/assets/?limit=2&offset=0")
    response2 = await client.get("/api/v1/assets/?limit=2&offset=2")
    
    # Assert
    assert response1.status_code == 200
    data1 = response1.json()
    assert len(data1["items"]) == 2
    assert data1["total"] >= 5

    assert response2.status_code == 200
    data2 = response2.json()
    assert len(data2["items"]) == 2

    ids1 = {data1["items"][0]["id"], data1["items"][1]["id"]}
    ids2 = {data2["items"][0]["id"], data2["items"][1]["id"]}
    assert ids1.isdisjoint(ids2)

@pytest.mark.asyncio
async def test_list_assets_filter_type_status(client: AsyncClient, setup_assets):
    # Arrange
    # (Setup handled by fixture)
    
    # Act
    response = await client.get("/api/v1/assets/?type=domain&status=active")
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) >= 1
    assert data["items"][0]["type"] == "domain"
    assert data["items"][0]["status"] == "active"

@pytest.mark.asyncio
async def test_list_assets_filter_tag(client: AsyncClient, setup_assets):
    # Arrange
    # (Setup handled by fixture)
    
    # Act
    response = await client.get("/api/v1/assets/?tag=prod")
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) >= 3
    assert "prod" in data["items"][0]["tags"]
    assert "prod" in data["items"][1]["tags"]
    assert "prod" in data["items"][2]["tags"]

@pytest.mark.asyncio
async def test_list_assets_filter_value_substring(client: AsyncClient, setup_assets):
    # Arrange
    # (Setup handled by fixture)
    
    # Act
    response = await client.get("/api/v1/assets/?value=test-list")
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) >= 3
    assert "test-list" in data["items"][0]["value"].lower()
    assert "test-list" in data["items"][1]["value"].lower()
    assert "test-list" in data["items"][2]["value"].lower()

@pytest.mark.asyncio
async def test_update_asset(client: AsyncClient):
    # Arrange
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
    
    # Act
    response = await client.put(f"/api/v1/assets/{asset_id}", json=update_payload)
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "archived"
    assert "updated" in data["tags"]

@pytest.mark.asyncio
async def test_delete_asset(client: AsyncClient):
    # Arrange
    payload = {
        "type": "domain",
        "value": "delete-test.com",
    }
    create_response = await client.post("/api/v1/assets/", json=payload)
    asset_id = create_response.json()["id"]
    
    # Act
    response = await client.delete(f"/api/v1/assets/{asset_id}")
    get_response = await client.get(f"/api/v1/assets/{asset_id}")
    
    # Assert
    assert response.status_code == 204
    assert get_response.status_code == 404

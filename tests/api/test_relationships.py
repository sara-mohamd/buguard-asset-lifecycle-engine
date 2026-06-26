import pytest
import pytest_asyncio
from httpx import AsyncClient

@pytest_asyncio.fixture
async def setup_graph_assets(client: AsyncClient):
    # Create two assets to form a relationship
    domain_payload = {
        "type": "domain",
        "value": "graph-test.com",
    }
    ip_payload = {
        "type": "ip_address",
        "value": "10.10.10.10",
    }
    
    r1 = await client.post("/api/v1/assets/", json=domain_payload)
    r2 = await client.post("/api/v1/assets/", json=ip_payload)
    
    return {
        "domain": r1.json(),
        "ip": r2.json()
    }

@pytest.mark.asyncio
async def test_create_relationship(client: AsyncClient, setup_graph_assets):
    domain = setup_graph_assets["domain"]
    ip = setup_graph_assets["ip"]
    
    payload = {
        "source_asset_id": domain["id"],
        "target_asset_id": ip["id"],
        "type": "resolves_to"
    }
    
    response = await client.post("/api/v1/relationships/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["source_asset_id"] == domain["id"]
    assert data["target_asset_id"] == ip["id"]
    assert data["type"] == "resolves_to"
    assert "first_seen" in data

@pytest.mark.asyncio
async def test_create_relationship_invalid_asset(client: AsyncClient):
    import uuid
    payload = {
        "source_asset_id": str(uuid.uuid4()),
        "target_asset_id": str(uuid.uuid4()),
        "type": "resolves_to"
    }
    
    response = await client.post("/api/v1/relationships/", json=payload)
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_get_asset_relationships(client: AsyncClient, setup_graph_assets):
    domain = setup_graph_assets["domain"]
    ip = setup_graph_assets["ip"]
    
    # Create relationship
    payload = {
        "source_asset_id": domain["id"],
        "target_asset_id": ip["id"],
        "type": "resolves_to"
    }
    await client.post("/api/v1/relationships/", json=payload)
    
    # Fetch domain relationships
    response_domain = await client.get(f"/api/v1/assets/{domain['id']}/relationships")
    assert response_domain.status_code == 200
    data_domain = response_domain.json()
    
    assert data_domain["id"] == domain["id"]
    assert len(data_domain["neighbors"]) == 1
    neighbor = data_domain["neighbors"][0]
    assert neighbor["asset"]["id"] == ip["id"]
    assert neighbor["relationship_type"] == "resolves_to"
    assert neighbor["direction"] == "outbound"
    
    # Fetch ip relationships
    response_ip = await client.get(f"/api/v1/assets/{ip['id']}/relationships")
    assert response_ip.status_code == 200
    data_ip = response_ip.json()
    
    assert data_ip["id"] == ip["id"]
    assert len(data_ip["neighbors"]) == 1
    neighbor_ip = data_ip["neighbors"][0]
    assert neighbor_ip["asset"]["id"] == domain["id"]
    assert neighbor_ip["relationship_type"] == "resolves_to"
    assert neighbor_ip["direction"] == "inbound"

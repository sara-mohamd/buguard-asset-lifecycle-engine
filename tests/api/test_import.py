import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.models.asset import Asset, AssetType, AssetStatus
@pytest.mark.asyncio
async def test_import_assets_success(client: AsyncClient, db_session: AsyncSession):
    """
    Test that valid assets can be imported successfully.
    """
    payload = [
        {
            "type": "domain",
            "value": "example.com",
            "tags": ["prod"],
            "metadata": {"registrar": "AWS"}
        },
        {
            "type": "ip_address",
            "value": "192.168.1.1",
            "tags": ["internal"],
            "metadata": {"datacenter": "us-east-1"}
        }
    ]
    
    response = await client.post("/api/v1/assets/import", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total_analyzed"] == 2
    assert data["successful_creates"] == 2
    assert data["successful_updates"] == 0
    assert len(data["rejected_records"]) == 0
@pytest.mark.asyncio
async def test_import_idempotent_updates(client: AsyncClient, db_session: AsyncSession):
    """
    Test that re-importing the same asset updates metadata and tags, but doesn't duplicate.
    """
    payload_1 = [
        {
            "type": "domain",
            "value": "update-me.com",
            "tags": ["v1"],
            "metadata": {"key1": "val1"}
        }
    ]
    
    # First import
    res1 = await client.post("/api/v1/assets/import", json=payload_1)
    assert res1.status_code == 200
    
    payload_2 = [
        {
            "type": "domain",
            "value": "update-me.com",
            "tags": ["v2"],
            "metadata": {"key2": "val2", "key1": "new-val1"} # key1 overridden, key2 added
        }
    ]
    
    # Second import
    res2 = await client.post("/api/v1/assets/import", json=payload_2)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["successful_creates"] == 0
    assert data2["successful_updates"] == 1
    
    # Verify in DB
    result = await db_session.execute(select(Asset).where(Asset.value == "update-me.com"))
    asset = result.scalar_one()
    
    # Tags should be unioned
    assert "v1" in asset.tags
    assert "v2" in asset.tags
    
    # Metadata should be deeply merged
    assert asset.metadata_["key2"] == "val2"
    assert asset.metadata_["key1"] == "new-val1"
    
    # timestamps
    assert asset.last_seen > asset.first_seen
@pytest.mark.asyncio
async def test_import_state_transition(client: AsyncClient, db_session: AsyncSession):
    """
    Test that a stale asset becomes active upon re-sighting.
    """
    payload_1 = [
        {
            "type": "domain",
            "value": "stale-test.com",
            "status": "stale"
        }
    ]
    
    # Import as stale
    await client.post("/api/v1/assets/import", json=payload_1)
    
    payload_2 = [
        {
            "type": "domain",
            "value": "stale-test.com"
            # default status is active
        }
    ]
    
    # Re-import should set it to active
    await client.post("/api/v1/assets/import", json=payload_2)
    
    result = await db_session.execute(select(Asset).where(Asset.value == "stale-test.com"))
    asset = result.scalar_one()
    assert asset.status == AssetStatus.active.value
@pytest.mark.asyncio
async def test_import_partial_failure(client: AsyncClient, db_session: AsyncSession):
    """
    Test that malformed records do not crash the batch.
    """
    payload = [
        {
            "type": "domain",
            "value": "valid-domain.com"
        },
        {
            "type": "ip_address",
            "value": "not-an-ip" # invalid IP
        },
        {
            "type": "service",
            "value": "80" # Invalid service format, should be port/proto
        }
    ]
    
    response = await client.post("/api/v1/assets/import", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert data["total_analyzed"] == 3
    assert data["successful_creates"] == 1
    assert len(data["rejected_records"]) == 2
    
    # Check that the valid one is in the DB
    result = await db_session.execute(select(Asset).where(Asset.value == "valid-domain.com"))
    asset = result.scalar_one_or_none()
    assert asset is not None

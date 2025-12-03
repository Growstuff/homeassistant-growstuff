
import asyncio
from unittest.mock import MagicMock, AsyncMock
from datetime import date

import pytest
from custom_components.growstuff.api.client import GrowstuffApiClient

@pytest.fixture
def mock_session():
    """Mock aiohttp.ClientSession."""
    session = MagicMock()
    session.get = MagicMock()
    session.patch = MagicMock()
    session.delete = MagicMock()
    return session

@pytest.mark.asyncio
async def test_get_member(mock_session):
    """Test getting a member."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={
        "data": [{"id": "123", "attributes": {"login-name": "testuser"}}]
    })
    mock_session.get.return_value.__aenter__.return_value = mock_response

    client = GrowstuffApiClient(mock_session)
    member = await client.get_member("testuser")

    assert member is not None
    assert member["id"] == "123"
    mock_session.get.assert_called_once_with(
        "https://www.growstuff.org/api/v1/members",
        params={"filter[login-name]": "testuser"},
        headers={"Accept": "application/vnd.api+json", "Content-Type": "application/vnd.api+json"},
    )

@pytest.mark.asyncio
async def test_get_all_pages(mock_session):
    """Test getting all pages from a paginated endpoint."""
    mock_response_1 = MagicMock()
    mock_response_1.status = 200
    mock_response_1.json = AsyncMock(return_value={
        "data": [{"id": "1"}, {"id": "2"}],
        "links": {"next": "https://example.com/page2"},
    })

    mock_response_2 = MagicMock()
    mock_response_2.status = 200
    mock_response_2.json = AsyncMock(return_value={
        "data": [{"id": "3"}],
        "links": {},
    })

    cm1 = MagicMock()
    cm1.__aenter__.return_value = mock_response_1
    cm2 = MagicMock()
    cm2.__aenter__.return_value = mock_response_2

    mock_session.get.side_effect = [cm1, cm2]

    client = GrowstuffApiClient(mock_session)
    items = await client._get_all("https://example.com/page1")

    assert len(items) == 3
    assert items[0]["id"] == "1"
    assert items[1]["id"] == "2"
    assert items[2]["id"] == "3"

    assert mock_session.get.call_count == 2

@pytest.mark.asyncio
async def test_update_activity(mock_session):
    """Test updating an activity."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"data": {}})
    mock_session.patch.return_value.__aenter__.return_value = mock_response

    client = GrowstuffApiClient(mock_session, "fake_api_key")
    await client.update_activity("123", date.fromisoformat("2023-01-01"), "New description", True)

    mock_session.patch.assert_called_once()

@pytest.mark.asyncio
async def test_delete_activity(mock_session):
    """Test deleting an activity."""
    mock_response = MagicMock()
    mock_response.status = 204
    mock_session.delete.return_value.__aenter__.return_value = mock_response

    client = GrowstuffApiClient(mock_session, "fake_api_key")
    await client.delete_activity("123")

    mock_session.delete.assert_called_once()

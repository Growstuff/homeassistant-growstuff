"""Test Growstuff setup and unload."""
from unittest.mock import AsyncMock, MagicMock, patch
import aiohttp
import pytest

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from custom_components.growstuff import async_setup_entry, async_unload_entry
from custom_components.growstuff.const import DOMAIN, PLATFORMS
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .const import MOCK_CONFIG

MEMBER_ID = "123"
MEMBER_NAME = "test-member"


def create_mock_response(status=200, json_data=None, text_data=""):
    """Create a mock aiohttp response context manager."""
    response = AsyncMock()
    response.status = status
    response.text = AsyncMock(return_value=text_data)
    if json_data is not None:
        response.json = AsyncMock(return_value=json_data)
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=response)
    cm.__aexit__ = AsyncMock(return_value=None)
    return cm, response


async def test_setup_entry_success(hass: HomeAssistant) -> None:
    """Test successful setup of Growstuff config entry."""
    cm, _ = create_mock_response(
        200,
        {
            "data": [
                {
                    "id": MEMBER_ID,
                    "attributes": {"login-name": MEMBER_NAME},
                }
            ]
        },
    )
    mock_session = MagicMock()
    mock_session.get.return_value = cm

    with patch(
        "custom_components.growstuff.async_get_clientsession",
        return_value=mock_session,
    ), patch.object(
        hass.config_entries, "async_forward_entry_setups", return_value=None
    ) as mock_forward:
        entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG["data"])
        entry.add_to_hass(hass)

        assert await async_setup_entry(hass, entry) is True
        assert entry.runtime_data == {"member_id": MEMBER_ID}
        mock_forward.assert_called_once_with(entry, PLATFORMS)


async def test_setup_entry_not_ready_on_non_200(hass: HomeAssistant) -> None:
    """Test setup raises ConfigEntryNotReady when member endpoint returns non-200."""
    cm, _ = create_mock_response(404)
    mock_session = MagicMock()
    mock_session.get.return_value = cm

    with patch(
        "custom_components.growstuff.async_get_clientsession",
        return_value=mock_session,
    ), patch.object(
        hass.config_entries, "async_forward_entry_setups"
    ) as mock_forward:
        entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG["data"])
        entry.add_to_hass(hass)

        with pytest.raises(ConfigEntryNotReady) as exc_info:
            await async_setup_entry(hass, entry)

        assert "Member not found" in str(exc_info.value)
        mock_forward.assert_not_called()


async def test_setup_entry_not_ready_on_empty_member(hass: HomeAssistant) -> None:
    """Test setup raises ConfigEntryNotReady when member list is empty."""
    cm, _ = create_mock_response(200, {"data": []})
    mock_session = MagicMock()
    mock_session.get.return_value = cm

    with patch(
        "custom_components.growstuff.async_get_clientsession",
        return_value=mock_session,
    ), patch.object(
        hass.config_entries, "async_forward_entry_setups"
    ) as mock_forward:
        entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG["data"])
        entry.add_to_hass(hass)

        with pytest.raises(ConfigEntryNotReady) as exc_info:
            await async_setup_entry(hass, entry)

        assert "Member not found" in str(exc_info.value)
        mock_forward.assert_not_called()


async def test_setup_entry_not_ready_on_client_error(hass: HomeAssistant) -> None:
    """Test setup raises ConfigEntryNotReady when client error occurs."""
    mock_session = MagicMock()
    mock_session.get.side_effect = aiohttp.ClientError("Connection refused")

    with patch(
        "custom_components.growstuff.async_get_clientsession",
        return_value=mock_session,
    ), patch.object(
        hass.config_entries, "async_forward_entry_setups"
    ) as mock_forward:
        entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG["data"])
        entry.add_to_hass(hass)

        with pytest.raises(ConfigEntryNotReady) as exc_info:
            await async_setup_entry(hass, entry)

        assert "Error communicating with API" in str(exc_info.value)
        mock_forward.assert_not_called()


async def test_unload_entry(hass: HomeAssistant) -> None:
    """Test unloading Growstuff config entry."""
    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG["data"])
    entry.add_to_hass(hass)

    with patch.object(
        hass.config_entries, "async_unload_platforms", return_value=True
    ) as mock_unload:
        assert await async_unload_entry(hass, entry) is True
        mock_unload.assert_called_once_with(entry, PLATFORMS)

"""The Growstuff integration."""
from __future__ import annotations

import logging
import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, PLATFORMS, _API_URL

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Growstuff from a config entry."""
    session = async_get_clientsession(hass)
    member_name = entry.data.get("member")
    member_url = f"{_API_URL}/members?filter[login-name]={member_name}"

    _LOGGER.debug("Fetching %s", member_url)
    try:
        async with session.get(member_url) as response:
            if response.status != 200:
                raise ConfigEntryNotReady(
                    f"Member not found, check configuration: {response.status}"
                )
            data = await response.json()
            member_result = data.get("data")
    except aiohttp.ClientError as err:
        raise ConfigEntryNotReady(f"Error communicating with API: {err}") from err

    if not member_result:
        raise ConfigEntryNotReady("Member not found, check configuration")

    member = member_result[0]
    member_id = member.get("id")

    entry.runtime_data = {"member_id": member_id}

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

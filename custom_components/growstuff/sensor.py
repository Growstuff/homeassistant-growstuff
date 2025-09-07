"""HA component to import plantings status from growstuff.org."""

import logging
from homeassistant.helpers.aiohttp_client import async_get_clientsession

import homeassistant.exceptions

from homeassistant.components.sensor import SensorEntity

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from .const import DOMAIN, _API_URL

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up all plantings."""
    session = async_get_clientsession(hass)
    member_name = config_entry.data.get("member")
    member_url = f"{_API_URL}/members?filter[login-name]={member_name}"

    _LOGGER.debug("Fetching " + member_url)
    async with session.get(member_url) as response:
        if response.status != 200:
            raise homeassistant.exceptions.ConfigEntryNotReady(
                f"Member not found, check configuration: {response.status}"
            )
        member_result = (await response.json()).get("data")

    if len(member_result) == 0:
        raise homeassistant.exceptions.ConfigEntryNotReady(
            "Member not found, check configuration"
        )

    member = member_result[0]
    plantings_url = f"{_API_URL}/plantings?filter[owner-id]={member.get('id')}&filter[finished]=false"

    await add_plantings(plantings_url, async_add_entities, session)


async def add_plantings(plantings_url, async_add_entities, session):
    """Add plantings until we added them all."""
    _LOGGER.debug("Fetching " + plantings_url)
    async with session.get(plantings_url) as response:
        if response.status != 200:
            _LOGGER.error(f"Failed to fetch plantings: {response.status}")
            return
        data = await response.json()

    entities = []
    for planting in data.get("data"):
        entities.append(GrowstuffPlantingSensor(planting, session))
    async_add_entities(entities)
    links = data.get("links")
    if links.get("next"):
        await add_plantings(links.get("next"), async_add_entities, session)


# Device
class GrowstuffPlantingEntity(SensorEntity):
    @property
    def device_info(self):
        """Return device information for the device registry."""
        return {
            "identifiers": {
                (DOMAIN, self._attributes.get("slug"))
            },
            "name": self.name,
            "manufacturer": "Growstuff",
            "model": "Planting",
            "sw_version": "0.0.1",
        }


# Specific sensor
class GrowstuffPlantingSensor(GrowstuffPlantingEntity):
    """Grow stuff."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:sprout"

    def __init__(self, planting, session):
        """Initialize the sensor."""
        self.planting_id = planting.get("id")
        self._links = planting.get("links")
        self._attributes = planting.get("attributes")
        self._relationships = planting.get("relationships")
        self._session = session

    @property
    def unique_id(self):
        """Return the ID of the sensor."""
        return self._attributes.get("slug")

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._attributes.get("crop-name")

    @property
    def state(self):
        """Return the state of the sensor."""
        percent = self._attributes.get("percentage-grown")
        if isinstance(percent, float):
            return round(percent, 2)
        return None

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    def _url(self):
        return self._links.get("self")

    @property
    def entity_picture(self):
        """Icon to use in the frontend, if any."""
        return self._attributes.get("thumbnail")

    @property
    def unit_of_measurement(self):
        """Return the unit this state is expressed in."""
        return "%"

    async def async_update(self):
        """Get the latest data from Growstuff and update the states."""
        _LOGGER.debug("Fetching " + self._url())
        async with self._session.get(self._url()) as response:
            if response.status == 200:
                data = await response.json()
                planting = data.get("data")
                self._links = planting.get("links")
                self._attributes = planting.get("attributes")
                self._relationships = planting.get("relationships")

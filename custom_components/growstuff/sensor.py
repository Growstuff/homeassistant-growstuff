"""HA component to import plantings status from growstuff.org."""

import logging
from datetime import timedelta
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import device_registry as dr

import homeassistant.exceptions

from homeassistant.components.sensor import SensorEntity

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from .const import DOMAIN, SENSOR_TYPES
from .entity import GrowstuffEntity
from .api.client import GrowstuffApiClient

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(days=1)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up all entities."""
    session = async_get_clientsession(hass)
    api_client = GrowstuffApiClient(session)

    member_name = config_entry.data.get("member")
    member = await api_client.get_member(member_name)
    if not member:
        raise homeassistant.exceptions.ConfigEntryNotReady(
            "Member not found, check configuration"
        )
    member_id = member.get("id")

    device_registry = dr.async_get(hass)
    gardens_result = await api_client.get_gardens(member_id)
    gardens = {}
    for garden in gardens_result:
        device = device_registry.async_get_or_create(
            config_entry_id=config_entry.entry_id,
            identifiers={(DOMAIN, garden.get("id"))},
            name=garden.get("attributes").get("name"),
            manufacturer="Growstuff",
            suggested_area=garden.get("attributes").get("name"),
        )
        gardens[garden.get("id")] = device

    entities = []
    for entity_type in SENSOR_TYPES:
        if entity_type == "plantings":
            for item in await api_client.get_plantings(member_id):
                garden = item.get("relationships").get("garden")
                if garden and garden.get("data"):
                    garden_id = garden.get("data").get("id")
                    entities.append(GrowstuffPlantingSensor(item, api_client, gardens.get(garden_id)))
        elif entity_type == "harvests":
            for item in await api_client.get_harvests(member_id):
                entities.append(GrowstuffHarvestSensor(item, api_client))
        elif entity_type == "seeds":
            for item in await api_client.get_seeds(member_id):
                entities.append(GrowstuffSeedSensor(item, api_client))
    async_add_entities(entities)


class GrowstuffSensorEntity(GrowstuffEntity, SensorEntity):
    """Base class for Growstuff sensors."""

    def __init__(self, data, client):
        """Initialize the sensor."""
        super().__init__(data, client)
        self.entity_id = "sensor.growstuff_" + data.get("id")


# Device
class GrowstuffPlantingEntity(GrowstuffSensorEntity):
    def __init__(self, data, client, garden_device=None):
        """Initialize the sensor."""
        super().__init__(data, client)
        self._garden_device = garden_device

    @property
    def device_info(self):
        """Return device information for the device registry."""
        device_info = {
            "identifiers": {(DOMAIN, self._attributes.get("slug"))},
            "name": self.name,
            "manufacturer": "Growstuff",
            "model": "Planting",
            "sw_version": "0.0.1",
        }
        if self._garden_device:
            device_info["via_device"] = (DOMAIN, self._garden_device.id)
        return device_info


# Specific sensor
class GrowstuffPlantingSensor(GrowstuffPlantingEntity):
    """Grow stuff."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:sprout"

    def __init__(self, data, client, garden_device=None):
        """Initialize the sensor."""
        super().__init__(data, client, garden_device)
        self.entity_id = "sensor.planting_" + data.get("id")

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
    def unit_of_measurement(self):
        """Return the unit this state is expressed in."""
        return "%"


class GrowstuffHarvestSensor(GrowstuffSensorEntity):
    """Growstuff Harvest Sensor."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:food-apple"

    def __init__(self, harvest, client):
        """Initialize the sensor."""
        super().__init__(harvest, client)
        self.entity_id = "sensor.harvest_" + harvest.get("id")

    @property
    def unique_id(self):
        """Return the ID of the sensor."""
        return self.entity_id

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"Harvest {self.entity_id}"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._attributes.get("weight_quantity")

    @property
    def unit_of_measurement(self):
        """Return the unit this state is expressed in."""
        return self._attributes.get("weight_unit")


class GrowstuffSeedSensor(GrowstuffSensorEntity):
    """Growstuff Seed Sensor."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:seed"

    def __init__(self, seed, client):
        """Initialize the sensor."""
        super().__init__(seed, client)
        self.entity_id = "sensor.seed_" + seed.get("id")

    @property
    def unique_id(self):
        """Return the ID of the sensor."""
        return self.entity_id

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._attributes.get("description") or f"Seed {self.entity_id}"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._attributes.get("quantity")

"""HA component to import plantings status from growstuff.org."""

import logging
from homeassistant.helpers.aiohttp_client import async_get_clientsession

import homeassistant.exceptions

from homeassistant.components.sensor import SensorEntity

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from .const import DOMAIN, _API_URL, SENSOR_TYPES
from .entity import GrowstuffEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up all entities."""
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
    member_id = member.get("id")

    for entity_type in SENSOR_TYPES:
        url = f"{_API_URL}/{entity_type}?filter[owner-id]={member_id}"
        if entity_type == "plantings":
            url += "&filter[finished]=false"
        await add_entities_for_type(url, entity_type, async_add_entities, session)


async def add_entities_for_type(url, entity_type, async_add_entities, session):
    """Add entities for a given type until we added them all."""
    _LOGGER.debug(f"Fetching {entity_type} from {url}")
    async with session.get(url) as response:
        if response.status != 200:
            _LOGGER.error(f"Failed to fetch {entity_type}: {response.status}")
            return
        data = await response.json()

    entities = []
    for item in data.get("data"):
        if entity_type == "plantings":
            entities.append(GrowstuffPlantingSensor(item, session))
        elif entity_type == "gardens":
            entities.append(GrowstuffGardenSensor(item, session))
        elif entity_type == "harvests":
            entities.append(GrowstuffHarvestSensor(item, session))
        elif entity_type == "seeds":
            entities.append(GrowstuffSeedSensor(item, session))
    async_add_entities(entities)
    links = data.get("links")
    if "next" in links and links.get("next"):
        await add_entities_for_type(
            links.get("next"), entity_type, async_add_entities, session
        )


class GrowstuffSensorEntity(GrowstuffEntity, SensorEntity):
    """Base class for Growstuff sensors."""

    def __init__(self, data, session):
        """Initialize the sensor."""
        super().__init__(data, session)
        self.entity_id = "sensor.growstuff_" + data.get("id")


# Device
class GrowstuffPlantingEntity(GrowstuffSensorEntity):
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

    def __init__(self, data, session):
        """Initialize the sensor."""
        super().__init__(data, session)
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


class GrowstuffGardenSensor(GrowstuffSensorEntity):
    """Growstuff Garden Sensor."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:flower"

    def __init__(self, garden, session):
        """Initialize the sensor."""
        super().__init__(garden, session)
        self.entity_id = "sensor.garden_" + garden.get("id")

    @property
    def unique_id(self):
        """Return the ID of the sensor."""
        return self.entity_id

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._attributes.get("name")

    @property
    def state(self):
        """Return the state of the sensor."""
        # The API doesn't provide a direct state for gardens, so we'll use the name.
        return self._attributes.get("name")


class GrowstuffHarvestSensor(GrowstuffSensorEntity):
    """Growstuff Harvest Sensor."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:food-apple"

    def __init__(self, harvest, session):
        """Initialize the sensor."""
        super().__init__(harvest, session)
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

    def __init__(self, seed, session):
        """Initialize the sensor."""
        super().__init__(seed, session)
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

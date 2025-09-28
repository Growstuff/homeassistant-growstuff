"""HA component to import plantings status from growstuff.org."""

import logging
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import device_registry as dr

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

    device_registry = dr.async_get(hass)
    gardens_url = f"{_API_URL}/gardens?filter[owner-id]={member_id}"
    gardens = {}
    async with session.get(gardens_url) as response:
        if response.status == 200:
            data = await response.json()
            for garden in data.get("data"):
                device = device_registry.async_get_or_create(
                    config_entry_id=config_entry.entry_id,
                    identifiers={(DOMAIN, garden.get("id"))},
                    name=garden.get("attributes").get("name"),
                    manufacturer="Growstuff",
                    suggested_area=garden.get("attributes").get("name"),
                )
                gardens[garden.get("id")] = device

    for entity_type in SENSOR_TYPES:
        url = f"{_API_URL}/{entity_type}?filter[owner-id]={member_id}"
        # TODO: Activities may want to include all activities
        if entity_type == "plantings" or entity_type == "activities" or entity_type == "seeds":
            url += "&filter[finished]=false"
        await add_entities_for_type(
            url, entity_type, async_add_entities, session, gardens
        )


async def add_entities_for_type(
    url, entity_type, async_add_entities, session, gardens
):
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
            garden = item.get("relationships").get("garden")
            # As of https://github.com/Growstuff/growstuff/pull/4272 this will start populating.
            if garden.get("data"):
                garden_id = garden.get("data").get("id")
                entities.append(GrowstuffPlantingSensor(item, session, gardens.get(garden_id)))
        elif entity_type == "harvests":
            entities.append(GrowstuffHarvestSensor(item, session))
        elif entity_type == "seeds":
            entities.append(GrowstuffSeedSensor(item, session))
    async_add_entities(entities)
    links = data.get("links")
    if "next" in links and links.get("next"):
        await add_entities_for_type(
            links.get("next"), entity_type, async_add_entities, session, gardens
        )


class GrowstuffSensorEntity(GrowstuffEntity, SensorEntity):
    """Base class for Growstuff sensors."""

    def __init__(self, data, session):
        """Initialize the sensor."""
        super().__init__(data, session)
        self.entity_id = "sensor.growstuff_" + data.get("id")


# Device
class GrowstuffPlantingEntity(GrowstuffSensorEntity):
    def __init__(self, data, session, garden_device=None):
        """Initialize the sensor."""
        super().__init__(data, session)
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

    def __init__(self, data, session, garden_device=None):
        """Initialize the sensor."""
        super().__init__(data, session, garden_device)
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

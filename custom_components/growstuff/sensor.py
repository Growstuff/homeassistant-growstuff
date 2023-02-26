"""HA component to import plantings status from growstuff.org."""
import logging
import requests

from homeassistant.helpers.entity import Entity

_API_URL = "https://www.growstuff.org/api/v1"
_LOGGER = logging.getLogger("growstuff")


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up all plantings."""
    member_url = "{api_url}/members?filter[login-name]={member}".format(
        api_url=_API_URL, member=config.get("member")
    )

    member_result = requests.get(member_url).json().get("data")
    _LOGGER.debug("Fetching " + member_url)

    if len(member_result) == 0:
        raise homeassistant.exceptions.ConfigEntryNotReady(
            "Member not found, check configuration"
        )

    member = member_result[0]
    plantings_url = "{api_url}/plantings?filter[owner-id]={member_id}&filter[finished]=false".format(
        api_url=_API_URL, member_id=member.get("id")
    )

    add_plantings(plantings_url, add_devices)


def add_plantings(plantings_url, add_devices):
    """Add plantings until we added them all."""
    _LOGGER.debug("Fetching " + plantings_url)
    response = requests.get(plantings_url).json()
    devices = []
    for planting in response.get("data"):
        devices.append(GrowstuffPlantingSensor(planting))
    add_devices(devices)
    links = response.get("links")
    if links.get("next"):
        add_plantings(links.get("next"), add_devices)

# Device
class GrowstuffPlantingEntity(Entity):
    @property
    def device_info(self):
        """Return device information for the device registry."""
        return {
            "identifiers": {
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self._attributes.get("slug"))
            },
            "name": self.name,
            "manufacturer": "Growstuff",
            "model": "Planting",
            "sw_version": 1.0,
        }

# Specific sensor
class GrowstuffPlantingSensor(GrowstuffPlantingEntity):
    """Grow stuff."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:sprout"

    def __init__(self, planting):
        """Initialize the sensor."""
        self.planting_id = planting.get("id")
        self._links = planting.get("links")
        self._attributes = planting.get("attributes")
        self._relationships = planting.get("relationships")

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

    @property
    def device_state_attributes(self):
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

    def update(self):
        """Get the latest data from Growstuff and update the states."""
        _LOGGER.debug("Fetching " + self._url())
        response = requests.get(self._url())
        self.__init__(response.json().get("data"))

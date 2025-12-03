"""Base entity for the Growstuff integration."""
import logging
from homeassistant.helpers.entity import Entity

from .api.client import GrowstuffApiClient

_LOGGER = logging.getLogger(__name__)


class GrowstuffEntity(Entity):
    """Base class for Growstuff entities."""

    def __init__(self, data: dict, client: GrowstuffApiClient):
        """Initialize the sensor."""
        self._links = data.get("links")
        self._attributes = data.get("attributes")
        self._relationships = data.get("relationships")
        self._client = client
        self._id = data.get("id")

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    def _url(self):
        return self._links.get("self")

    @property
    def entity_picture(self):
        """Icon to use in the frontend, if any."""
        if self._attributes.get("thumbnail"):
            return "https://growstuff.org/" + self._attributes.get("thumbnail")

    async def async_update(self):
        """Get the latest data from Growstuff and update the states."""
        _LOGGER.debug("Fetching " + self._url())
        data = await self._client.get_url(self._url())
        if data:
            item = data.get("data")
            self._links = item.get("links")
            self._attributes = item.get("attributes")
            self._relationships = item.get("relationships")

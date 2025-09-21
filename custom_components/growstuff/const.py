"""Constants for growstuff integration."""
from homeassistant.const import Platform

from homeassistant.const import CONF_API_TOKEN, CONF_USERNAME

DOMAIN = "growstuff"
_API_URL = "https://www.growstuff.org/api/v1"

PLATFORMS = [Platform.SENSOR, Platform.TODO]

SENSOR_TYPES = {
    "harvests": "Harvests",
    "seeds": "Seeds",
    "plantings": "Plantings",
}

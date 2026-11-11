"""Constants for growstuff integration."""
from datetime import timedelta
from homeassistant.const import Platform

DOMAIN = "growstuff"
_API_URL = "https://www.growstuff.org/api/v1"
SCAN_INTERVAL = timedelta(minutes=1)

PLATFORMS = [Platform.SENSOR, Platform.TODO]

SENSOR_TYPES = {
    "harvests": "Harvests",
    "seeds": "Seeds",
    "plantings": "Plantings",
}

"""Constants for growstuff integration."""
from homeassistant.const import Platform

DOMAIN = "growstuff"

PLATFORMS = [Platform.SENSOR, Platform.TODO]

SENSOR_TYPES = {
    "harvests": "Harvests",
    "seeds": "Seeds",
    "plantings": "Plantings",
}

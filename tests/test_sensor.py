"""Test the Growstuff sensor platform."""
from datetime import timedelta

from custom_components.growstuff.sensor import SCAN_INTERVAL


def test_sensor_scan_interval() -> None:
    """Test that SCAN_INTERVAL in sensor platform is 1 day."""
    assert SCAN_INTERVAL == timedelta(days=1)

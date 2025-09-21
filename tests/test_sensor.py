"""Test the Growstuff sensor."""
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.growstuff.const import DOMAIN
from custom_components.growstuff.sensor import (
    GrowstuffPlantingSensor,
    async_setup_entry,
)

from .const import MOCK_CONFIG
from pytest_homeassistant_custom_component.common import MockConfigEntry


MEMBER_ID = "123"
MEMBER_NAME = "test-member"
PLANTING_ID = "456"

@pytest.fixture
def mock_session():
    """Mock aiohttp client session."""
    with patch("homeassistant.helpers.aiohttp_client.async_get_clientsession") as mock_session:
        yield mock_session

async def test_async_setup_entry(hass: HomeAssistant, mock_session: AsyncMock) -> None:
    """Test a successful setup."""
    # Mock the API responses
    mock_session.return_value.get.side_effect = [
        AsyncMock(
            status=200,
            json=AsyncMock(
                return_value={
                    "data": [
                        {
                            "id": MEMBER_ID,
                            "attributes": {"login-name": MEMBER_NAME},
                        }
                    ]
                }
            ),
        ),
        AsyncMock(
            status=200,
            json=AsyncMock(
                return_value={
                    "data": [
                        {
                            "id": PLANTING_ID,
                            "attributes": {
                                "crop-name": "Tomato",
                                "slug": "tomato-1",
                                "percentage-grown": 50.0,
                            },
                            "links": {"self": "http://fake.com/planting/1"},
                        }
                    ],
                    "links": {"next": None},
                }
            ),
        ),
    ]

    # Set up the component
    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG["data"])
    entry.add_to_hass(hass)
    await async_setup_entry(hass, entry, AsyncMock())
    await hass.async_block_till_done()


    # Check that the sensor was added
    sensor = hass.states.get("sensor.tomato")
    assert sensor is not None
    assert sensor.state == "50.0"
    assert sensor.name == "Tomato"
    assert sensor.attributes.get("slug") == "tomato-1"

async def test_async_update(hass: HomeAssistant, mock_session: AsyncMock) -> None:
    """Test a successful update."""
    # Set up a sensor
    planting = {
        "id": PLANTING_ID,
        "attributes": {
            "crop-name": "Tomato",
            "slug": "tomato-1",
            "percentage-grown": 50.0,
        },
        "links": {"self": "http://fake.com/planting/1"},
    }
    sensor = GrowstuffPlantingSensor(planting, mock_session.return_value)
    sensor.hass = hass
    sensor.entity_id = "sensor.tomato"


    # Mock the API response for the update
    mock_session.return_value.get.return_value = AsyncMock(
        status=200,
        json=AsyncMock(
            return_value={
                "data": {
                    "id": PLANTING_ID,
                    "attributes": {
                        "crop-name": "Tomato",
                        "slug": "tomato-1",
                        "percentage-grown": 75.0,
                    },
                    "links": {"self": "http://fake.com/planting/1"},
                }
            }
        ),
    )

    # Update the sensor
    await sensor.async_update()
    await hass.async_block_till_done()


    # Check that the state was updated
    assert sensor.state == 75.0

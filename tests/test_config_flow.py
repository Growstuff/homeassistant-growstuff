"""Test the Growstuff config flow."""
from unittest.mock import patch

import pytest
from homeassistant import config_entries, setup
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.growstuff.const import DOMAIN
from custom_components.growstuff.config_flow import InvalidData


async def test_form(hass: HomeAssistant) -> None:
    """Test we get the form."""
    await setup.async_setup_component(hass, "persistent_notification", {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] is None

    with patch(
        "custom_components.growstuff.config_flow.validate_input",
        return_value={"title": "test-member"},
    ), patch(
        "custom_components.growstuff.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "member": "test-member",
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == "test-member"
    assert result2["data"] == {
        "member": "test-member",
    }
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_invalid_data(hass: HomeAssistant) -> None:
    """Test we handle invalid data."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "custom_components.growstuff.config_flow.validate_input",
        side_effect=InvalidData,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "member": "a",
            },
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_data"}

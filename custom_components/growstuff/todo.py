"""Todo platform for the Growstuff integration."""
from __future__ import annotations
from datetime import datetime
import logging
from typing import cast

from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.exceptions
from homeassistant.util import dt as dt_util

from .const import DOMAIN, _API_URL
from .entity import GrowstuffEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Growstuff todo platform."""
    session = async_get_clientsession(hass)
    api_key = config_entry.data.get("api_key")
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

    async_add_entities([GrowstuffTodoListEntity(member_id, api_key, session)])


class GrowstuffTodoListEntity(TodoListEntity):
    """A class to display a growstuff todo list."""

    _attr_has_entity_name = True
    _attr_supported_features = (
        TodoListEntityFeature.UPDATE_TODO_ITEM
        | TodoListEntityFeature.SET_DUE_DATE_ON_ITEM
        | TodoListEntityFeature.SET_DESCRIPTION_ON_ITEM
    )

    def __init__(self, member_id, api_key, session):
        """Initialize the sensor."""
        self._member_id = member_id
        self._api_key = api_key
        self._session = session
        self._attr_name = "Growstuff Gardening Activities"
        self._attr_unique_id = f"growstuff_{member_id}_todo"
        self._items: list[TodoItem] = []

    @property
    def todo_items(self) -> list[TodoItem] | None:
        """Get the todo items."""
        return self._items

    async def async_create_todo_item(self, item: TodoItem) -> None:
        """Create a new todo item."""
        raise NotImplementedError()

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """Update a todo item."""
        uid = item.uid
        url = f"{_API_URL}/activities/{uid}"
        payload = {
            "data": {
                "type": "activities",
                "id": uid,
                "attributes": {
                    "due": item.due,
                    "description": item.description,
                    "finished": item.status == TodoItemStatus.COMPLETED,
                },
            }
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/vnd.api+json",
        }
        async with self._session.patch(url, json=payload, headers=headers) as response:
            if response.status != 200:
                _LOGGER.error(f"Failed to update activity: {response.status}")
                return
            await self.async_update()

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        """Delete todo items."""
        for uid in uids:
            url = f"{_API_URL}/activities/{uid}"
            async with self._session.delete(url) as response:
                if response.status != 204:
                    _LOGGER.error(f"Failed to delete activity: {response.status}")
                    return
        await self.async_update()

    async def async_update(self) -> None:
        """Update the items in the todo list."""
        url = f"{_API_URL}/activities?filter[owner-id]={self._member_id}"
        items = []
        while url:
            async with self._session.get(url) as response:
                if response.status != 200:
                    _LOGGER.error(f"Failed to fetch activities: {response.status}")
                    return
                data = await response.json()
            for item in data.get("data", []):
                attributes = item.get("attributes", {})
                due = None
                if due_date := attributes.get("due-date"):
                    due = datetime.fromisoformat(due_date).date()

                if attributes.get("finished"):
                    status = TodoItemStatus.COMPLETED
                else:
                    status = TodoItemStatus.NEEDS_ACTION
                items.append(
                    TodoItem(
                        uid=item.get("id"),
                        summary=attributes.get("name"),
                        description=attributes.get("description"),
                        status=status,
                        due=due,
                    )
                )
            links = data.get("links", {})
            url = links.get("next")
        self._items = items

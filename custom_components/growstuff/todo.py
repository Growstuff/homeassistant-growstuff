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

from .api.client import GrowstuffApiClient

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Growstuff todo platform."""
    session = async_get_clientsession(hass)
    api_key = config_entry.data.get("api_key")
    api_client = GrowstuffApiClient(session, api_key)
    member_name = config_entry.data.get("member")

    member = await api_client.get_member(member_name)
    if not member:
        raise homeassistant.exceptions.ConfigEntryNotReady(
            "Member not found, check configuration"
        )
    member_id = member.get("id")

    async_add_entities([GrowstuffTodoListEntity(member_id, api_client)])


class GrowstuffTodoListEntity(TodoListEntity):
    """A class to display a growstuff todo list."""

    _attr_has_entity_name = True
    _attr_supported_features = (
        TodoListEntityFeature.UPDATE_TODO_ITEM
        | TodoListEntityFeature.SET_DUE_DATE_ON_ITEM
        | TodoListEntityFeature.SET_DESCRIPTION_ON_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
    )

    def __init__(self, member_id, client: GrowstuffApiClient):
        """Initialize the sensor."""
        self._member_id = member_id
        self._client = client
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
        await self._client.update_activity(
            item.uid,
            item.due,
            item.description,
            item.status == TodoItemStatus.COMPLETED,
        )
        await self.async_update()

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        """Delete todo items."""
        for uid in uids:
            await self._client.delete_activity(uid)
        await self.async_update()

    async def async_update(self) -> None:
        """Update the items in the todo list."""
        items = []
        for item in await self._client.get_activities(self._member_id):
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
        self._items = items

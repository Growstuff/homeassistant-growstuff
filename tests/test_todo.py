"""Test the Growstuff todo platform."""
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.components.todo import TodoItem, TodoItemStatus
from homeassistant.core import HomeAssistant

from custom_components.growstuff.const import DOMAIN
from custom_components.growstuff.todo import (
    GrowstuffTodoListEntity,
    async_setup_entry,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .const import MOCK_CONFIG

MEMBER_ID = "123"
MEMBER_NAME = "test-member"


def create_mock_response(status=200, json_data=None, text_data=""):
    """Create a mock aiohttp response context manager."""
    response = AsyncMock()
    response.status = status
    response.text = AsyncMock(return_value=text_data)
    if json_data is not None:
        response.json = AsyncMock(return_value=json_data)
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=response)
    cm.__aexit__ = AsyncMock(return_value=None)
    return cm, response


async def test_async_setup_entry_with_runtime_data(hass: HomeAssistant) -> None:
    """Test setting up todo platform when runtime_data contains member_id."""
    mock_session = MagicMock()
    with patch(
        "custom_components.growstuff.todo.async_get_clientsession",
        return_value=mock_session,
    ):
        entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG["data"])
        entry.add_to_hass(hass)
        entry.runtime_data = {"member_id": MEMBER_ID}

        added_entities = []

        def mock_add_entities(entities):
            added_entities.extend(entities)

        await async_setup_entry(hass, entry, mock_add_entities)

    assert len(added_entities) == 1
    entity = added_entities[0]
    assert isinstance(entity, GrowstuffTodoListEntity)
    assert entity.name == "Growstuff Gardening Jobs"
    assert entity.unique_id == f"growstuff_{MEMBER_ID}_todo"


async def test_async_setup_entry(hass: HomeAssistant) -> None:
    """Test setting up todo platform adds the entity with jobs endpoint fallback."""
    cm, _ = create_mock_response(
        200,
        {
            "data": [
                {
                    "id": MEMBER_ID,
                    "attributes": {"login-name": MEMBER_NAME},
                }
            ]
        },
    )
    mock_session = MagicMock()
    mock_session.get.return_value = cm

    with patch(
        "custom_components.growstuff.todo.async_get_clientsession",
        return_value=mock_session,
    ):
        entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG["data"])
        entry.add_to_hass(hass)

        added_entities = []

        def mock_add_entities(entities):
            added_entities.extend(entities)

        await async_setup_entry(hass, entry, mock_add_entities)

    assert len(added_entities) == 1
    entity = added_entities[0]
    assert isinstance(entity, GrowstuffTodoListEntity)
    assert entity.name == "Growstuff Gardening Jobs"
    assert entity.unique_id == f"growstuff_{MEMBER_ID}_todo"


async def test_async_setup_entry_error_fallback(hass: HomeAssistant) -> None:
    """Test setting up todo platform when member fetch fails in fallback."""
    cm, _ = create_mock_response(404)
    mock_session = MagicMock()
    mock_session.get.return_value = cm

    with patch(
        "custom_components.growstuff.todo.async_get_clientsession",
        return_value=mock_session,
    ):
        entry = MockConfigEntry(domain=DOMAIN, data=MOCK_CONFIG["data"])
        entry.add_to_hass(hass)

        added_entities = []

        def mock_add_entities(entities):
            added_entities.extend(entities)

        await async_setup_entry(hass, entry, mock_add_entities)

    assert len(added_entities) == 0


async def test_async_update_fetches_jobs(hass: HomeAssistant) -> None:
    """Test fetching jobs from the jobs endpoint."""
    cm, _ = create_mock_response(
        200,
        {
            "data": [
                {
                    "id": "1",
                    "attributes": {
                        "name": "Water tomato",
                        "description": "Give 1L of water",
                        "finished": False,
                        "due-date": "2026-05-01",
                    },
                },
                {
                    "id": "2",
                    "attributes": {
                        "name": "Harvest lettuce",
                        "description": "Pick outer leaves",
                        "finished": True,
                        "due-date": None,
                    },
                },
            ],
            "links": {},
        },
    )
    session = MagicMock()
    session.get.return_value = cm

    entity = GrowstuffTodoListEntity(MEMBER_ID, "api_token_123", session)
    await entity.async_update()

    session.get.assert_called_once_with(
        f"https://www.growstuff.org/api/v1/jobs?filter[owner-id]={MEMBER_ID}"
    )

    assert len(entity.todo_items) == 2
    item1 = entity.todo_items[0]
    assert item1.uid == "1"
    assert item1.summary == "Water tomato"
    assert item1.description == "Give 1L of water"
    assert item1.status == TodoItemStatus.NEEDS_ACTION
    assert item1.due == date(2026, 5, 1)

    item2 = entity.todo_items[1]
    assert item2.uid == "2"
    assert item2.summary == "Harvest lettuce"
    assert item2.description == "Pick outer leaves"
    assert item2.status == TodoItemStatus.COMPLETED
    assert item2.due is None


async def test_async_update_todo_item_patches_jobs(hass: HomeAssistant) -> None:
    """Test updating a job sends a PATCH to /jobs/{uid} with jobs type and due-date."""
    cm_patch, _ = create_mock_response(200)
    cm_get, _ = create_mock_response(200, {"data": [], "links": {}})

    session = MagicMock()
    session.patch.return_value = cm_patch
    session.get.return_value = cm_get

    entity = GrowstuffTodoListEntity(MEMBER_ID, "api_token_123", session)
    item = TodoItem(
        uid="42",
        summary="Prune basil",
        description="Top the basil plant",
        status=TodoItemStatus.COMPLETED,
        due=date(2026, 6, 15),
    )

    await entity.async_update_todo_item(item)

    session.patch.assert_called_once_with(
        "https://www.growstuff.org/api/v1/jobs/42",
        json={
            "data": {
                "type": "jobs",
                "id": "42",
                "attributes": {
                    "due-date": "2026-06-15",
                    "description": "Top the basil plant",
                    "finished": True,
                },
            }
        },
        headers={
            "Authorization": "Bearer api_token_123",
            "Accept": "application/vnd.api+json",
            "Content-Type": "application/vnd.api+json",
        },
    )


async def test_async_delete_todo_items_deletes_jobs(hass: HomeAssistant) -> None:
    """Test deleting jobs sends DELETE to /jobs/{uid}."""
    cm_delete, _ = create_mock_response(204)
    cm_get, _ = create_mock_response(200, {"data": [], "links": {}})

    session = MagicMock()
    session.delete.return_value = cm_delete
    session.get.return_value = cm_get

    entity = GrowstuffTodoListEntity(MEMBER_ID, "api_token_123", session)
    await entity.async_delete_todo_items(["99"])

    session.delete.assert_called_once_with("https://www.growstuff.org/api/v1/jobs/99")


async def test_async_update_error_response(hass: HomeAssistant) -> None:
    """Test error response during async_update logs text without AttributeError."""
    cm, _ = create_mock_response(500, text_data="Internal Server Error")
    session = MagicMock()
    session.get.return_value = cm

    entity = GrowstuffTodoListEntity(MEMBER_ID, "api_token_123", session)
    await entity.async_update()

    assert entity.todo_items == []


async def test_async_update_todo_item_error_response(hass: HomeAssistant) -> None:
    """Test error response during async_update_todo_item logs text without AttributeError."""
    cm_patch, _ = create_mock_response(400, text_data="Bad Request")
    session = MagicMock()
    session.patch.return_value = cm_patch

    entity = GrowstuffTodoListEntity(MEMBER_ID, "api_token_123", session)
    item = TodoItem(
        uid="42",
        summary="Prune basil",
        description="Top the basil plant",
        status=TodoItemStatus.COMPLETED,
    )

    await entity.async_update_todo_item(item)
    session.get.assert_not_called()


async def test_async_delete_todo_items_error_response(hass: HomeAssistant) -> None:
    """Test error response during async_delete_todo_items logs text without AttributeError."""
    cm_delete, _ = create_mock_response(404, text_data="Not Found")
    session = MagicMock()
    session.delete.return_value = cm_delete

    entity = GrowstuffTodoListEntity(MEMBER_ID, "api_token_123", session)
    await entity.async_delete_todo_items(["99"])
    session.get.assert_not_called()

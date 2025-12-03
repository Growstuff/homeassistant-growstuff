
import logging
from typing import Optional, List, Dict, Any
from datetime import date

from aiohttp import ClientSession

_LOGGER = logging.getLogger(__name__)

_API_URL = "https://www.growstuff.org/api/v1"


class GrowstuffApiClient:
    """A client for the Growstuff API."""

    def __init__(self, session: ClientSession, api_key: Optional[str] = None):
        """Initialize the client."""
        self._session = session
        self._api_key = api_key
        self._headers = {
            "Accept": "application/vnd.api+json",
            "Content-Type": "application/vnd.api+json",
        }
        if self._api_key:
            self._headers["Authorization"] = f"Bearer {self._api_key}"

    async def _get(self, url: str, params: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
        """Make a GET request to the API."""
        _LOGGER.debug(f"Fetching {url} with params {params}")
        async with self._session.get(url, params=params, headers=self._headers) as response:
            if response.status != 200:
                _LOGGER.error(f"Failed to fetch {url}: {response.status}")
                return None
            return await response.json()

    async def _patch(self, url: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Make a PATCH request to the API."""
        _LOGGER.debug(f"Patching {url} with payload {payload}")
        async with self._session.patch(url, json=payload, headers=self._headers) as response:
            if response.status != 200:
                _LOGGER.error(f"Failed to update {url}: {response.status}")
                _LOGGER.debug(f"Response: {await response.text()}")
                return None
            return await response.json()

    async def _delete(self, url: str) -> bool:
        """Make a DELETE request to the API."""
        _LOGGER.debug(f"Deleting {url}")
        async with self._session.delete(url, headers=self._headers) as response:
            if response.status != 204:
                _LOGGER.error(f"Failed to delete {url}: {response.status}")
                _LOGGER.debug(f"Response: {await response.text()}")
                return False
            return True

    async def get_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Make a GET request to an arbitrary URL."""
        return await self._get(url)

    async def _get_all(self, url: str, params: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """Get all items from a paginated endpoint."""
        items = []
        while url:
            data = await self._get(url, params)
            if data:
                items.extend(data.get("data", []))
                links = data.get("links", {})
                url = links.get("next")
                params = None  # Params are already included in the next url
            else:
                break
        return items

    async def get_member(self, login_name: str) -> Optional[Dict[str, Any]]:
        """Get a member by login name."""
        url = f"{_API_URL}/members"
        params = {"filter[login-name]": login_name}
        data = await self._get(url, params)
        if data and data.get("data"):
            return data["data"][0]
        return None

    async def get_gardens(self, owner_id: str) -> List[Dict[str, Any]]:
        """Get all gardens for a member."""
        url = f"{_API_URL}/gardens"
        params = {"filter[owner-id]": owner_id}
        return await self._get_all(url, params)

    async def get_plantings(self, owner_id: str, finished: bool = False) -> List[Dict[str, Any]]:
        """Get all plantings for a member."""
        url = f"{_API_URL}/plantings"
        params = {"filter[owner-id]": owner_id, "filter[finished]": str(finished).lower()}
        return await self._get_all(url, params)

    async def get_harvests(self, owner_id: str) -> List[Dict[str, Any]]:
        """Get all harvests for a member."""
        url = f"{_API_URL}/harvests"
        params = {"filter[owner-id]": owner_id}
        return await self._get_all(url, params)

    async def get_seeds(self, owner_id: str, finished: bool = False) -> List[Dict[str, Any]]:
        """Get all seeds for a member."""
        url = f"{_API_URL}/seeds"
        params = {"filter[owner-id]": owner_id, "filter[finished]": str(finished).lower()}
        return await self._get_all(url, params)

    async def get_activities(self, owner_id: str, finished: bool = False) -> List[Dict[str, Any]]:
        """Get all activities for a member."""
        url = f"{_API_URL}/activities"
        params = {"filter[owner-id]": owner_id, "filter[finished]": str(finished).lower()}
        return await self._get_all(url, params)

    async def update_activity(self, activity_id: str, due: Optional[date], description: str, finished: bool) -> Optional[Dict[str, Any]]:
        """Update an activity."""
        url = f"{_API_URL}/activities/{activity_id}"
        payload = {
            "data": {
                "type": "activities",
                "id": activity_id,
                "attributes": {
                    "due-date": due.isoformat() if due else None,
                    "description": description,
                    "finished": finished,
                },
            }
        }
        return await self._patch(url, payload)

    async def delete_activity(self, activity_id: str) -> bool:
        """Delete an activity."""
        url = f"{_API_URL}/activities/{activity_id}"
        return await self._delete(url)

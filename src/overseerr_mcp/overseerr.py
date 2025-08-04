import httpx
from typing import Any, Dict, Optional

class Overseerr:
    def __init__(
        self,
        api_key: str,
        url: str,
        timeout: tuple = (3, 30),
        client: Optional[httpx.AsyncClient] = None
    ):
        self.api_key = api_key
        self.url = url
        self.timeout = httpx.Timeout(timeout[0], read=timeout[1])
        self.client = client or httpx.AsyncClient()

    def _get_headers(self) -> dict:
        return {
            'Accept': 'application/json',
            'X-Api-Key': self.api_key
        }

    async def _safe_call(self, call_fn):
        try:
            return await call_fn()
        except httpx.HTTPStatusError as e:
            try:
                error_data = e.response.json()
                message = error_data.get('message', '<unknown>')
            except Exception:
                message = e.response.text
            raise Exception(f"HTTP Error {e.response.status_code}: {message}")
        except httpx.RequestError as e:
            raise Exception(f"Request failed: {str(e)}")

    async def get_status(self) -> Dict[str, Any]:
        """Get the status of the Overseerr server."""
        url = f"{self.url}/api/v1/status"
        
        async def call_fn():
            response = await self.client.get(url, headers=self._get_headers(), timeout=self.timeout)
            response.raise_for_status()
            return response.json()

        return await self._safe_call(call_fn)

    async def get_movie_details(self, movie_id: int) -> Dict[str, Any]:
        """Get movie details for a specific movie ID."""
        url = f"{self.url}/api/v1/movie/{movie_id}"
        
        async def call_fn():
            response = await self.client.get(url, headers=self._get_headers(), timeout=self.timeout)
            response.raise_for_status()
            return response.json()

        return await self._safe_call(call_fn)

    async def get_tv_details(self, tv_id: int) -> Dict[str, Any]:
        """Get TV details for a specific TV ID."""
        url = f"{self.url}/api/v1/tv/{tv_id}"
        
        async def call_fn():
            response = await self.client.get(url, headers=self._get_headers(), timeout=self.timeout)
            response.raise_for_status()
            return response.json()

        return await self._safe_call(call_fn)

    async def get_season_details(self, tv_id: int, season_id: int) -> Dict[str, Any]:
        """Get season details including episodes for a specific TV show and season."""
        url = f"{self.url}/api/v1/tv/{tv_id}/season/{season_id}"
        
        async def call_fn():
            response = await self.client.get(url, headers=self._get_headers(), timeout=self.timeout)
            response.raise_for_status()
            return response.json()

        return await self._safe_call(call_fn)

    async def get_requests(self, params: Dict[str, Any] = {}) -> Dict[str, Any]:
        """Get requests from the Overseerr API."""
        url = f"{self.url}/api/v1/request"
        
        async def call_fn():
            response = await self.client.get(url, params=params, headers=self._get_headers(), timeout=self.timeout)
            response.raise_for_status()
            return response.json()

        return await self._safe_call(call_fn)
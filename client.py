import os
from typing import Any

import httpx

DEFAULT_SERVICE_URL = "http://127.0.0.1:8000"


class MarineKnowledgeServiceClient:
    def __init__(
        self,
        base_url: str | None = None,
        timeout_seconds: float = 30.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        configured_url = base_url or os.getenv("MARINE_KNOWLEDGE_SERVICE_URL", DEFAULT_SERVICE_URL)
        self.base_url = configured_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self._client = client

    async def health(self) -> dict[str, Any]:
        return await self._request("GET", "/health")

    async def places(self) -> dict[str, Any]:
        return await self._request("GET", "/v1/marine/places")

    async def sources(self) -> dict[str, Any]:
        return await self._request("GET", "/v1/marine/sources")

    async def context(self, place_id: str, response_profile: str = "compact_llm") -> dict[str, Any]:
        return await self._request(
            "POST",
            "/v1/marine/context",
            json={
                "place_id": place_id,
                "response_profile": response_profile,
            },
        )

    async def sailing_conditions(
        self,
        area_id: str = "chicago_lakefront",
        response_profile: str = "compact_llm",
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/v1/marine/sailing-conditions",
            json={
                "area_id": area_id,
                "response_profile": response_profile,
            },
        )

    async def _request(
        self,
        method: str,
        path: str,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        if self._client is not None:
            response = await self._client.request(method, url, json=json)
            response.raise_for_status()
            return response.json()

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.request(method, url, json=json)
            response.raise_for_status()
            return response.json()


def service_client() -> MarineKnowledgeServiceClient:
    return MarineKnowledgeServiceClient()

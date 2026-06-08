import httpx
import pytest

from client import MarineKnowledgeServiceClient


@pytest.mark.anyio
async def test_context_posts_place_and_profile():
    captured = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["json"] = request.read().decode()
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = MarineKnowledgeServiceClient(
            base_url="http://service.test",
            client=http_client,
        )
        result = await client.context("monroe_harbor", "compact_llm")

    assert result == {"ok": True}
    assert captured["method"] == "POST"
    assert captured["url"] == "http://service.test/v1/marine/context"
    assert '"place_id":"monroe_harbor"' in captured["json"]
    assert '"response_profile":"compact_llm"' in captured["json"]


@pytest.mark.anyio
async def test_places_gets_places_endpoint():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert str(request.url) == "http://service.test/v1/marine/places"
        return httpx.Response(200, json={"places": []})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = MarineKnowledgeServiceClient(
            base_url="http://service.test/",
            client=http_client,
        )
        result = await client.places()

    assert result == {"places": []}


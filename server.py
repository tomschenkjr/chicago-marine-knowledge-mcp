"""
Chicago Marine Knowledge MCP

Thin MCP wrapper around the Chicago Marine Knowledge Service REST API.
This server does not call City, GLERL, or NOAA sources directly.
"""

import json
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from client import service_client

mcp = FastMCP(
    "Chicago Marine Knowledge",
    instructions=(
        "Use this MCP server for Chicago lakefront marine context. "
        "It delegates source collection and interpretation to the Chicago Marine "
        "Knowledge Service API."
    ),
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)


@mcp.tool()
async def check_marine_knowledge_service() -> dict[str, Any]:
    """
    Check whether the Chicago Marine Knowledge Service API is reachable.
    """
    return await service_client().health()


@mcp.tool()
async def list_marine_places() -> dict[str, Any]:
    """
    List supported Chicago marine places and their sensor relationships.
    """
    return await service_client().places()


@mcp.tool()
async def get_marine_sources() -> dict[str, Any]:
    """
    Get source health and availability for City sensors, Dever Crib, and weather MCP.
    """
    return await service_client().sources()


@mcp.tool()
async def get_marine_context(
    place_id: str = "monroe_harbor",
    response_profile: str = "compact_llm",
) -> dict[str, Any]:
    """
    Get source-grounded marine context for a Chicago lakefront place.

    Args:
        place_id: Supported place id, such as monroe_harbor, oak_street_beach,
            foster_beach, or 63rd_street_beach.
        response_profile: Optional response profile requested from the service.
    """
    return await service_client().context(place_id, response_profile)


@mcp.tool()
async def get_marine_conditions(
    place_id: str = "monroe_harbor",
    response_profile: str = "compact_llm",
) -> dict[str, Any]:
    """
    Alias for get_marine_context, named for condition-focused user requests.
    """
    return await service_client().context(place_id, response_profile)


@mcp.tool()
async def get_sailing_conditions(
    area_id: str = "chicago_lakefront",
    response_profile: str = "compact_llm",
) -> dict[str, Any]:
    """
    Get lakewide Chicago sailing conditions.

    This uses NOAA Marine Forecast/alerts as the baseline, then calls out
    current wind or wave observations that differ materially from that baseline.

    Args:
        area_id: Area identifier. The current supported value is chicago_lakefront.
        response_profile: Optional response profile requested from the service.
    """
    return await service_client().sailing_conditions(area_id, response_profile)


@mcp.resource("marine://places")
async def marine_places_resource() -> str:
    """
    Resource containing supported marine places as JSON.
    """
    return json.dumps(await service_client().places(), indent=2)


@mcp.resource("marine://sources")
async def marine_sources_resource() -> str:
    """
    Resource containing current source health as JSON.
    """
    return json.dumps(await service_client().sources(), indent=2)


@mcp.prompt()
def chicago_marine_briefing_prompt(place_id: str = "monroe_harbor") -> str:
    """
    Prompt template for producing a sailor-oriented Chicago marine briefing.
    """
    return (
        f"Use get_marine_context with place_id='{place_id}'. "
        "Summarize shoreline observations, Dever Crib offshore observations, "
        "NOAA forecast context, active alerts, freshness, and any source quality "
        "flags. Keep the answer source-grounded and call out uncertainty."
    )


@mcp.prompt()
def lakewide_sailing_conditions_prompt(area_id: str = "chicago_lakefront") -> str:
    """
    Prompt template for broad Chicago lakefront sailing-condition questions.
    """
    return (
        f"Use get_sailing_conditions with area_id='{area_id}'. Start with marine "
        "alerts/advisories, then NOAA Marine Forecast wind/waves, then call out "
        "only meaningful differences in current observations across shoreline, "
        "Dever Crib, and buoy stations. Explain implications for sailing using "
        "the returned risk, wind, wave, variation, and caution fields."
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")

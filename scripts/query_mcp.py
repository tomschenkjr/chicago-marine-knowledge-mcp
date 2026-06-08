#!/usr/bin/env python
"""
Query the Chicago Marine Knowledge MCP server and print a compact sailing brief.

This is a deterministic test harness, not an LLM. It maps a user-style query to
the MCP tool that should answer it, then formats the returned marine context.
"""

import argparse
import asyncio
import json
from typing import Any

from mcp import ClientSession
from mcp.client.sse import sse_client


DEFAULT_MCP_URL = "http://127.0.0.1:3001/sse"


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "query",
        nargs="?",
        default="give me the current sailing conditions",
        help="Natural-language-ish query to test.",
    )
    parser.add_argument(
        "--place-id",
        default="monroe_harbor",
        help="Marine place id, e.g. monroe_harbor, foster_beach, oak_street_beach.",
    )
    parser.add_argument(
        "--area-id",
        default="chicago_lakefront",
        help="Lakewide area id for sailing-condition queries.",
    )
    parser.add_argument(
        "--mcp-url",
        default=DEFAULT_MCP_URL,
        help="MCP SSE endpoint.",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Print raw JSON returned by the MCP tool.",
    )
    args = parser.parse_args()

    tool_name = choose_tool(args.query)
    tool_args = {"area_id": args.area_id} if tool_name == "get_sailing_conditions" else {"place_id": args.place_id}

    async with sse_client(args.mcp_url) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, tool_args)

    if not result.content:
        raise RuntimeError("MCP tool returned no content")

    data = json.loads(result.content[0].text)
    if args.raw:
        print(json.dumps(data, indent=2))
        return

    if "llm_briefing_context" in data:
        print(format_lakewide_sailing_conditions(data))
        return

    print(format_sailing_conditions(data))


def choose_tool(query: str) -> str:
    normalized = query.lower()
    if "source" in normalized:
        return "get_marine_sources"
    if "sailing" in normalized or "conditions" in normalized:
        return "get_sailing_conditions"
    return "get_marine_context"


def format_sailing_conditions(data: dict[str, Any]) -> str:
    place = data["place"]["name"]
    lines = [f"Sailing conditions for {place}", ""]

    shoreline = first(data.get("shoreline_weather"))
    if shoreline:
        values = shoreline["values"]
        lines.append(f"Shoreline weather ({shoreline['sensor_name']}):")
        lines.append(f"- Wind: {fmt(values.get('wind_speed_mps'))} m/s from {fmt(values.get('wind_direction_deg'))} deg")
        lines.append(f"- Gust/max: {fmt(values.get('maximum_wind_speed_mps'))} m/s")
        lines.append(f"- Air temp: {fmt(values.get('air_temperature_c'))} C")
        lines.append(f"- Humidity: {fmt(values.get('relative_humidity_percent'))}%")
        lines.append(f"- Observed: {shoreline.get('observed_at_label') or shoreline.get('observed_at')}")
        if shoreline.get("quality_flags"):
            lines.append(f"- Quality flags: {', '.join(shoreline['quality_flags'])}")
        lines.append("")

    offshore = first(data.get("offshore_observations"))
    if offshore:
        values = offshore["values"]
        lines.append(f"Offshore reference ({offshore['sensor_name']}):")
        lines.append(f"- Wind: {fmt(values.get('wind_speed_mps'))} m/s from {fmt(values.get('wind_direction_deg'))} deg")
        lines.append(f"- Gust: {fmt(values.get('wind_gust_mps'))} m/s")
        lines.append(f"- Air temp: {fmt(values.get('air_temperature_c'))} C")
        lines.append(f"- Observed: {offshore.get('observed_at_label') or offshore.get('observed_at')}")
        lines.append("")

    water = first(data.get("shoreline_water"))
    if water:
        values = water["values"]
        lines.append(f"Nearshore water ({water['sensor_name']}):")
        lines.append(f"- Water temp: {fmt(values.get('water_temperature_c'))} C")
        lines.append(f"- Wave height: {fmt(values.get('wave_height_m'))} m")
        lines.append(f"- Wave period: {fmt(values.get('wave_period_s'))} s")
        lines.append(f"- Observed: {water.get('observed_at_label') or water.get('observed_at')}")
        if water.get("quality_flags"):
            lines.append(f"- Quality flags: {', '.join(water['quality_flags'])}")
        lines.append("")

    forecast = data.get("forecast_context", {}).get("forecast") or {}
    periods = forecast.get("periods") or []
    if periods:
        period = periods[0]
        lines.append("NOAA forecast:")
        lines.append(f"- {period['name']}: {period['short_forecast']}")
        lines.append(f"- Wind: {period['wind_speed']} {period['wind_direction']}")
        lines.append(f"- Details: {period['detailed_forecast']}")
        lines.append("")

    alerts = data.get("forecast_context", {}).get("alerts") or {}
    alert_items = alerts.get("alerts") or []
    lines.append("Alerts:")
    if alert_items:
        for alert in alert_items:
            lines.append(f"- {alert.get('event')}: {alert.get('headline')}")
    else:
        lines.append(f"- {alerts.get('message', 'No active alerts reported.')}")

    lines.append("")
    lines.append(f"Summary: {data['summary']}")
    return "\n".join(lines)


def format_lakewide_sailing_conditions(data: dict[str, Any]) -> str:
    lines = ["Lakewide Chicago sailing conditions", ""]
    lines.append(f"Headline: {data['headline']}")
    lines.append(f"Risk level: {data['risk_level']}")
    lines.append("")

    alerts = data.get("alerts_first", {})
    lines.append("Alerts / advisories:")
    alert_items = alerts.get("alerts") or []
    if alert_items:
        for alert in alert_items:
            lines.append(f"- {alert.get('event')}: {alert.get('headline')}")
    else:
        lines.append(f"- {alerts.get('message', 'No active marine alerts reported.')}")
    lines.append("")

    baseline = data.get("marine_forecast_baseline", {})
    lines.append("NOAA Marine Forecast baseline:")
    lines.append(f"- Zone: {baseline.get('zone_id')} ({baseline.get('zone_name')})")
    lines.append(f"- Wind: {range_text(baseline.get('wind_kt'), 'kt')}")
    lines.append(f"- Waves: {range_text(baseline.get('waves_ft'), 'ft')}")
    lines.append("")

    wind = data.get("wind_assessment", {})
    lines.append("Wind observations:")
    lines.append(f"- Assessment: {wind.get('category')} ({wind.get('comparison')})")
    max_wind = wind.get("max_observed") or {}
    if max_wind:
        lines.append(f"- Highest observed: {max_wind.get('wind_kt', 0):.1f} kt at {max_wind.get('name')}")
    lines.append("")

    waves = data.get("wave_assessment", {})
    lines.append("Wave observations:")
    lines.append(f"- Assessment: {waves.get('category')} ({waves.get('comparison')})")
    max_wave = waves.get("max_observed") or {}
    if max_wave:
        lines.append(f"- Highest observed: {max_wave.get('wave_ft', 0):.1f} ft at {max_wave.get('name')}")
    lines.append("")

    if data.get("variations"):
        lines.append("Callouts:")
        for variation in data["variations"]:
            lines.append(f"- {variation}")
        lines.append("")

    if data.get("cautions"):
        lines.append("Cautions:")
        for caution in data["cautions"]:
            lines.append(f"- {caution}")
        lines.append("")

    lines.append("LLM briefing context:")
    lines.append(data["llm_briefing_context"])
    return "\n".join(lines)


def range_text(value: dict[str, Any] | None, unit: str) -> str:
    if not value or value.get("min") is None:
        return "n/a"
    if value.get("min") == value.get("max"):
        return f"{value['min']:.0f} {unit}"
    return f"{value['min']:.0f}-{value['max']:.0f} {unit}"


def first(items: list[dict[str, Any]] | None) -> dict[str, Any] | None:
    return items[0] if items else None


def fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.1f}"
    return str(value)


if __name__ == "__main__":
    asyncio.run(main())

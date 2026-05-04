"""Data Fetcher agent — collects real-time weather and water temperature."""
import json
import anthropic
from tools.weather import get_weather_conditions, get_water_temperature

SYSTEM_PROMPT = """You are the Data Fetcher for Swim Scout, an AI crew that evaluates open water swimming conditions.

Your job: collect ALL available real-time environmental data for the requested location using your tools.
1. Always call get_weather_conditions to get wind, air temp, and precipitation.
2. Always call get_water_temperature to get lake/bay water temp from USGS sensors.

Report every number you find. Note clearly when a sensor is unavailable so the rest of the crew can account for gaps."""

TOOLS = [
    {
        "name": "get_weather_conditions",
        "description": "Fetch current air temperature, wind speed, wind gusts, precipitation, and sky conditions from Open-Meteo",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "Lake or swimming location name (e.g. 'lake tahoe')"}
            },
            "required": ["location"],
        },
    },
    {
        "name": "get_water_temperature",
        "description": "Fetch current water temperature from the nearest USGS NWIS monitoring station",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "Lake or swimming location name"}
            },
            "required": ["location"],
        },
    },
]

TOOL_HANDLERS = {
    "get_weather_conditions": get_weather_conditions,
    "get_water_temperature": get_water_temperature,
}


async def run(location: str, client: anthropic.AsyncAnthropic) -> dict:
    messages = [
        {"role": "user", "content": f"Collect all current environmental conditions for open water swimming at: {location}"}
    ]
    raw_data: dict = {}

    while True:
        response = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            summary = next((b.text for b in response.content if hasattr(b, "text")), "")
            return {"summary": summary, "raw_data": raw_data}

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    handler = TOOL_HANDLERS.get(block.name)
                    result = await handler(**block.input) if handler else {"error": f"Unknown tool: {block.name}"}
                    raw_data[block.name] = result
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result),
                    })
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})
        else:
            break

    return {"summary": "Data collection incomplete.", "raw_data": raw_data}

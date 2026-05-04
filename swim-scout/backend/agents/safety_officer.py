"""Safety Officer agent — checks algae blooms and water quality alerts."""
import json
import anthropic
from tools.safety import check_algae_bloom_alerts, check_water_quality

SYSTEM_PROMPT = """You are the Safety Officer for Swim Scout, an AI crew that evaluates open water swimming conditions.

Your job: run a full safety assessment using your tools before any swimmer enters the water.
1. Always call check_algae_bloom_alerts — cyanobacteria toxins can be invisible and deadly.
2. Always call check_water_quality — abnormal pH or low dissolved oxygen are red flags.

Issue one of three verdicts and explain your reasoning:
- SAFE: no concerns found
- CAUTION: minor issues present, swim with awareness
- WARNING: active hazard detected, strongly advise against swimming

When sensor data is unavailable, say so explicitly and advise checking state health department advisories before swimming."""

TOOLS = [
    {
        "name": "check_algae_bloom_alerts",
        "description": "Check EPA Water Quality Portal for cyanobacteria/algae bloom reports in the last 30 days",
        "input_schema": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "Lake or swimming location name"}
            },
            "required": ["location"],
        },
    },
    {
        "name": "check_water_quality",
        "description": "Check USGS sensors for pH and dissolved oxygen levels near the location",
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
    "check_algae_bloom_alerts": check_algae_bloom_alerts,
    "check_water_quality": check_water_quality,
}


async def run(location: str, client: anthropic.AsyncAnthropic) -> dict:
    messages = [
        {"role": "user", "content": f"Conduct a full safety assessment for open water swimming at: {location}"}
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

    return {"summary": "Safety assessment incomplete.", "raw_data": raw_data}

import json
from typing import Any

from shared.external_tools import get_weather
from shared.tool_schemas import TOOL_SCHEMAS
from shared.venue_tools import (
    get_venue_details,
    search_venues,
)

TOOL_FUNCTIONS = {
    "search_venues": search_venues,
    "get_venue_details": get_venue_details,
    "get_weather": get_weather,
}


def dispatch_tool(
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    function = TOOL_FUNCTIONS.get(tool_name)

    if function is None:
        return {
            "ok": False,
            "error": f"Unknown tool: {tool_name}",
        }

    if not isinstance(arguments, dict):
        return {
            "ok": False,
            "error": "Arguments must be a JSON object",
        }

    try:
        result = function(**arguments)
        return {
            "ok": True,
            "result": result,
        }
    except (TypeError, ValueError, KeyError) as exc:
        return {
            "ok": False,
            "error": str(exc),
        }
    except Exception:
        return {
            "ok": False,
            "error": "Tool execution failed",
        }


def execute_tool_call(tool_call: Any) -> dict[str, Any]:
    try:
        name = tool_call.function.name
        raw_arguments = tool_call.function.arguments

        if isinstance(raw_arguments, str):
            arguments = json.loads(raw_arguments)
        else:
            arguments = raw_arguments

        if not isinstance(arguments, dict):
            raise ValueError("Arguments must be a JSON object")

        return dispatch_tool(name, arguments)

    except (AttributeError, json.JSONDecodeError, ValueError) as exc:
        return {
            "ok": False,
            "error": f"Invalid tool call: {exc}",
        }
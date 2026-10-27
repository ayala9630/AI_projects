
import json
from typing import Any

from shared.venue_tools import (
    search_venues,
    get_venue_details,
)


# Schemas sent to Groq so the model knows which tools are available.
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_venues",
            "description": (
                "Search venues by city, minimum capacity, "
                "and required features."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": ["string", "null"],
                        "description": "City name, or null for any city",
                    },
                    "min_capacity": {
                        "type": "integer",
                        "description": "Minimum number of attendees",
                    },
                    "required_features": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Features that must be available",
                    },
                },
                "required": [
                    "city",
                    "min_capacity",
                    "required_features",
                ],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_venue_details",
            "description": "Get full details for a venue by its ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "venue_id": {
                        "type": "string",
                        "description": "ID of the venue",
                    },
                },
                "required": ["venue_id"],
                "additionalProperties": False,
            },
        },
    },
]


# Maps tool names to the Python functions that execute them.
TOOL_FUNCTIONS = {
    "search_venues": search_venues,
    "get_venue_details": get_venue_details,
}


def dispatch_tool(
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Validate and execute a tool call requested by the model."""

    print(f"[tools.py] Dispatching tool: {tool_name}")

    function = TOOL_FUNCTIONS.get(tool_name)

    if function is None:
        return {
            "ok": False,
            "error": f"Unknown tool: {tool_name}",
        }

    if not isinstance(arguments, dict):
        return {
            "ok": False,
            "error": "Tool arguments must be a JSON object",
        }

    try:
        result = function(**arguments)

        # Return compact JSON-compatible data to the model.
        return {
            "ok": True,
            "result": result,
        }

    except TypeError:
        # Usually indicates missing or unexpected arguments.
        return {
            "ok": False,
            "error": "Invalid tool arguments",
        }

    except (ValueError, KeyError) as exc:
        return {
            "ok": False,
            "error": str(exc),
        }

    except Exception:
        # Avoid exposing internal details to the model.
        print(f"[tools.py] Tool execution failed: {tool_name}")
        return {
            "ok": False,
            "error": "Tool execution failed",
        }


def execute_tool_call(tool_call: Any) -> dict[str, Any]:
    """Parse a Groq tool call and dispatch it."""

    try:
        tool_name = tool_call.function.name
        raw_arguments = tool_call.function.arguments

        if isinstance(raw_arguments, str):
            arguments = json.loads(raw_arguments)
        elif isinstance(raw_arguments, dict):
            arguments = raw_arguments
        else:
            return {
                "ok": False,
                "error": "Tool arguments must be JSON",
            }

        if not isinstance(arguments, dict):
            return {
                "ok": False,
                "error": "Tool arguments must be a JSON object",
            }

        return dispatch_tool(tool_name, arguments)

    except (AttributeError, json.JSONDecodeError):
        return {
            "ok": False,
            "error": "Invalid tool call format",
        }

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
                        "type": ["string", "null"]
                    },
                    "min_capacity": {
                        "type": "integer",
                        "minimum": 1
                    },
                    "required_features": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": [
                    "city",
                    "min_capacity",
                    "required_features"
                ],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_venue_details",
            "description": "Get details for a venue by its ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "venue_id": {"type": "string"}
                },
                "required": ["venue_id"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string"}
                },
                "required": ["city"],
                "additionalProperties": False
            }
        }
    }
]
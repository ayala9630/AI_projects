from typing import Any

from API.harness.memory import get_relevant_memory

SYSTEM_INSTRUCTIONS = """
You are a venue recommendation agent.

Rules:
- Use search_venues to find venues from the local dataset.
- Use get_venue_details when detailed information about a venue is needed.
- Never invent venue details, prices, capacity, or features.
- If information is unknown, state that it is unknown.
- Respect explicit constraints in the current request over saved defaults.
- Do not change saved preferences unless the user explicitly asks to save them.
- Base recommendations on tool results.
- Reply in the same language as the user's latest request.
""".strip()


def build_context(
    user_request: str,
    *,
    event_details: dict[str, Any] | None = None,
    recent_search_results: list[dict[str, Any]] | None = None,
    selected_venue: dict[str, Any] | None = None,
    include_search_results: bool = False,
) -> list[dict[str, str]]:
    event_details = event_details or {}

    relevant_memory = get_relevant_memory(event_details)

    context_data: dict[str, Any] = {
        "event_details": event_details,
        "relevant_preferences": relevant_memory,
    }

    if include_search_results and recent_search_results:
        context_data["recent_search_results"] = recent_search_results

    if selected_venue:
        context_data["selected_venue_details"] = selected_venue

    import json

    context_json = json.dumps(
        context_data,
        ensure_ascii=False,
        indent=2,
    )

    print("[context.py] Built context")

    return [
        {"role": "system", "content": SYSTEM_INSTRUCTIONS},
        {
            "role": "user",
            "content": (
                f"Current request:\n{user_request}\n\n"
                f"Relevant context:\n{context_json}"
            ),
        },
    ]
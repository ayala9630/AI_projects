from typing import Any


def compact_history(
    messages: list[dict[str, Any]],
    *,
    keep_last: int = 8,
) -> list[dict[str, Any]]:
    if keep_last < 2:
        raise ValueError("keep_last must be at least 2")

    if len(messages) <= keep_last:
        return list(messages)

    # Keep the system instructions and the most recent messages.
    system_messages = [
        message
        for message in messages
        if message.get("role") == "system"
    ]

    non_system_messages = [
        message
        for message in messages
        if message.get("role") != "system"
    ]

    compacted = system_messages + non_system_messages[-keep_last:]

    print(
        f"[compaction.py] Reduced messages from "
        f"{len(messages)} to {len(compacted)}"
    )

    return compacted
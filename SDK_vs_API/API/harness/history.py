from typing import Any


class ConversationHistory:
    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []

    def add(self, message: dict[str, Any]) -> None:
        self.messages.append(message)

    def extend(self, messages: list[dict[str, Any]]) -> None:
        self.messages.extend(messages)

    def get_messages(self) -> list[dict[str, Any]]:
        return [dict(message) for message in self.messages]

    def clear(self) -> None:
        self.messages.clear()

    def __len__(self) -> int:
        return len(self.messages)
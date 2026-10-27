import json
import time
from typing import Any

from API.harness.tokens import (
    create_turn_metrics,
    record_model_usage,
    record_tool_call,
    save_turn_metrics,
)
from API.harness.tools import TOOL_SCHEMAS, execute_tool_call


def run_agent_loop(
    client: Any,
    messages: list[dict[str, Any]],
    *,
    model: str,
    session_id: str = "session-1",
    turn_number: int = 1,
    max_steps: int = 6,
) -> dict[str, Any]:
    metrics = create_turn_metrics()
    started_at = time.perf_counter()
    current_messages = list(messages)

    try:
        for step in range(max_steps):
            response = client.chat.completions.create(
                model=model,
                messages=current_messages,
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
            )

            record_model_usage(metrics, response)

            message = response.choices[0].message
            tool_calls = getattr(message, "tool_calls", None)

            assistant_message: dict[str, Any] = {
                "role": "assistant",
                "content": message.content or "",
            }

            if tool_calls:
                assistant_message["tool_calls"] = [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.function.name,
                            "arguments": call.function.arguments,
                        },
                    }
                    for call in tool_calls
                ]

            current_messages.append(assistant_message)

            if not tool_calls:
                return {
                    "answer": message.content or "",
                    "messages": current_messages,
                    "metrics": metrics,
                    "stop_reason": "final_answer",
                }

            for tool_call in tool_calls:
                tool_name = tool_call.function.name
                record_tool_call(metrics, tool_name)

                print(f"[loop.py] Executing tool: {tool_name}")
                tool_result = execute_tool_call(tool_call)

                current_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(
                        tool_result,
                        ensure_ascii=False,
                    ),
                })

        return {
            "answer": "",
            "messages": current_messages,
            "metrics": metrics,
            "stop_reason": "max_steps",
        }

    finally:
        metrics["duration_ms"] = round(
            (time.perf_counter() - started_at) * 1000
        )
        save_turn_metrics(
            metrics,
            session_id=session_id,
            turn_number=turn_number,
        )
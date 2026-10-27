import json
import os

from dotenv import load_dotenv
from groq import Groq
load_dotenv()  # טוען את .env מתיקיית העבודה
    
from API.harness.tools import (
    TOOL_SCHEMAS,
    dispatch_tool,
)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """
You are a venue-search assistant.

Use the available tools to search the local venue database.
Do not invent venue details.
If information is missing, state that it is unknown.
"""


def run_agent(user_text: str, max_steps: int = 6) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_text},
    ]

    for step in range(max_steps):
        print(f"[loop.py] Model call, step={step + 1}")

        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
        )

        message = response.choices[0].message

        # Add the assistant message, including any tool calls,
        # to the conversation history.
        messages.append(message.model_dump(exclude_none=True))

        tool_calls = message.tool_calls or []

        # No tool calls means the model has produced its final answer.
        if not tool_calls:
            return message.content or ""

        # Execute all tool calls from this response.
        for tool_call in tool_calls:
            tool_name = tool_call.function.name

            try:
                arguments = json.loads(
                    tool_call.function.arguments
                )
            except json.JSONDecodeError:
                result = {
                    "ok": False,
                    "error": "Tool arguments were not valid JSON",
                }
            else:
                result = dispatch_tool(
                    tool_name,
                    arguments,
                )

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(
                    result,
                    ensure_ascii=False,
                ),
            })

    return "The agent reached the maximum number of steps."
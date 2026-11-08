from netfree_unstrict_ssl import unstrict_ssl
unstrict_ssl()
import json
import os

from dotenv import load_dotenv
from groq import Groq
import groq

load_dotenv()  # טוען את .env מתיקיית העבודה

from API.harness.tools import (
    TOOL_SCHEMAS,
    dispatch_tool,
)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MODEL = "" + os.getenv("GROQ_MODEL")

SYSTEM_PROMPT = """
You are a venue-search assistant.

**Always** use the available tools to search the local venue database.
Do not invent venue details.
include in your answer the tools that you checked if they are relevant to the user query.
If information is missing, state that it is unknown.
"""


def _is_blocked_page(exc: Exception) -> bool:
    """בודק אם התשובה היא דף חסימה של נטפרי ולא שגיאת API אמיתית."""
    resp = getattr(exc, "response", None)
    if resp is None:
        return False
    content_type = (resp.headers.get("content-type") or "").lower()
    body = resp.text or ""
    return "text/html" in content_type or "netfree.link/block" in body


def ask(messages, tools=None, model=MODEL):
    """עטיפה לכל קריאה למודל, עם זיהוי חסימת רשת."""
    try:
        return client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools or [],
            tool_choice="auto",
        )
    except groq.APIStatusError as e:
        if _is_blocked_page(e):
            raise RuntimeError(
                "הבקשה נחסמה על ידי סינון הרשת (נטפרי). "
                "יש לפתוח את api.groq.com מול התמיכה."
            ) from e
        raise


def run_agent(user_text: str, max_steps: int = 6) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_text},
    ]

    for step in range(max_steps):
        print(f"[loop.py] Model call, step={step + 1}")

        response = ask(messages, tools=TOOL_SCHEMAS)
        

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
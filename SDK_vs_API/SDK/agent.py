import os

from dotenv import load_dotenv
from groq import Groq

from API.harness.context import build_context
from API.harness.loop import run_agent_loop

MODEL = "llama-3.3-70b-versatile"


def run_agent(
    request: str,
    session_id: str = "default",
    event_details: dict | None = None,
) -> str:
    load_dotenv()

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is missing. Set it in .env."
        )

    client = Groq(api_key=api_key)

    messages = build_context(
        request,
        event_details=event_details,
    )

    result = run_agent_loop(
        client,
        messages,
        model=MODEL,
        session_id=session_id,
        turn_number=1,
        max_steps=6,
    )

    return result["answer"] or (
        "The agent reached the maximum number of steps."
    )
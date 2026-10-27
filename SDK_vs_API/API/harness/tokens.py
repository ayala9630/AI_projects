import json
from pathlib import Path
from typing import Any

METRICS_FILE = (
    Path(__file__).resolve().parents[2]
    / "results"
    / "usage.jsonl"
)


def create_turn_metrics() -> dict[str, Any]:
    return {
        "input_tokens": None,
        "cache_read_tokens": None,
        "cache_write_tokens": None,
        "output_tokens": None,
        "model_calls": 0,
        "tool_calls": [],
        "cost_usd": None,
        "duration_ms": 0,
    }


def record_model_usage(
    metrics: dict[str, Any],
    response: Any,
) -> None:
    """Record usage returned by the API, if available."""
    metrics["model_calls"] += 1

    usage = getattr(response, "usage", None)
    if usage is None:
        print("[tokens.py] API usage unavailable")
        return

    prompt_tokens = getattr(usage, "prompt_tokens", None)
    completion_tokens = getattr(usage, "completion_tokens", None)

    if prompt_tokens is not None:
        previous = metrics["input_tokens"] or 0
        metrics["input_tokens"] = previous + prompt_tokens

    if completion_tokens is not None:
        previous = metrics["output_tokens"] or 0
        metrics["output_tokens"] = previous + completion_tokens

    # Do not assume the provider exposes cache token counts.
    cached = getattr(usage, "prompt_tokens_details", None)
    if cached is not None:
        cache_read = getattr(cached, "cached_tokens", None)
        if cache_read is not None:
            previous = metrics["cache_read_tokens"] or 0
            metrics["cache_read_tokens"] = previous + cache_read

    print("[tokens.py] Recorded model usage")


def record_tool_call(
    metrics: dict[str, Any],
    tool_name: str,
) -> None:
    metrics["tool_calls"].append(tool_name)


def calculate_cost(
    input_tokens: int | None,
    output_tokens: int | None,
    *,
    input_price_per_million: float | None,
    output_price_per_million: float | None,
) -> float | None:
    """
    Calculate cost only when token counts and both prices are known.

    Prices are USD per million tokens. Keep the rates and their
    effective date in your report.
    """
    values = (
        input_tokens,
        output_tokens,
        input_price_per_million,
        output_price_per_million,
    )

    if any(value is None for value in values):
        return None

    return (
        input_tokens * input_price_per_million
        + output_tokens * output_price_per_million
    ) / 1_000_000


def save_turn_metrics(
    metrics: dict[str, Any],
    *,
    session_id: str,
    turn_number: int,
) -> None:
    METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "session_id": session_id,
        "turn_number": turn_number,
        **metrics,
    }

    with METRICS_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"[tokens.py] Recorded usage for turn {turn_number}")
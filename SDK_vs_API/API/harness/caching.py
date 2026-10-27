from typing import Any


def extract_cache_usage(response: Any) -> dict[str, int | None]:
    usage = getattr(response, "usage", None)

    result: dict[str, int | None] = {
        "cache_read_tokens": None,
        "cache_write_tokens": None,
    }

    if usage is None:
        print("[caching.py] Cache usage unavailable")
        return result

    details = getattr(usage, "prompt_tokens_details", None)

    if details is not None:
        cached_tokens = getattr(details, "cached_tokens", None)
        if cached_tokens is not None:
            result["cache_read_tokens"] = cached_tokens

    print("[caching.py] Inspected cache usage")
    return result
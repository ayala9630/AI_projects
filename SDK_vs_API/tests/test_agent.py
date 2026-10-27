import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from API.harness import memory, tokens
from API.harness.loop import run_agent_loop
from API.harness.tools import dispatch_tool
from shared import venue_tools


@pytest.fixture
def temporary_memory(tmp_path, monkeypatch):
    path = tmp_path / "memory.json"
    monkeypatch.setattr(memory, "MEMORY_FILE", path)
    return path


def test_save_and_load_memory(temporary_memory):
    memory.save_memory({
        "default_city": "תל אביב",
        "minimum_capacity": 50,
    })

    saved = json.loads(
        temporary_memory.read_text(encoding="utf-8")
    )

    assert saved["preferences"]["default_city"] == "תל אביב"
    assert saved["preferences"]["minimum_capacity"] == 50

    loaded = memory.load_memory()
    assert loaded["preferences"]["default_city"] == "תל אביב"


def test_current_request_overrides_default_without_saving(
    temporary_memory,
):
    memory.save_memory({
        "default_city": "תל אביב",
        "minimum_capacity": 50,
    })

    current = memory.get_relevant_memory({
        "city": "ירושלים",
        "min_capacity": 70,
    })

    assert current["default_city"] == "ירושלים"
    assert current["minimum_capacity"] == 70

    persisted = memory.load_memory()["preferences"]
    assert persisted["default_city"] == "תל אביב"
    assert persisted["minimum_capacity"] == 50


def test_search_filters_capacity_and_preserves_source_page(monkeypatch):
    venues = [
        {
            "id": "v1",
            "name": "Venue A",
            "city": "תל אביב",
            "capacity": 40,
            "features": ["parking"],
            "source_page": 2,
        },
        {
            "id": "v2",
            "name": "Venue B",
            "city": "תל אביב",
            "capacity": 80,
            "features": ["parking"],
            "source_page": 7,
        },
    ]

    monkeypatch.setattr(venue_tools, "load_venues", lambda: venues)

    results = venue_tools.search_venues(
        city="תל אביב",
        min_capacity=50,
        required_features=["parking"],
    )

    assert [venue["id"] for venue in results] == ["v2"]
    assert results[0]["source_page"] == 7


def test_dispatch_unknown_tool_returns_error():
    result = dispatch_tool("tool_that_does_not_exist", {})

    assert result["ok"] is False
    assert "Unknown tool" in result["error"]


def test_calculate_cost():
    cost = tokens.calculate_cost(
        1_000_000,
        500_000,
        input_price_per_million=0.20,
        output_price_per_million=0.80,
    )

    assert cost == pytest.approx(0.60)


def test_calculate_cost_returns_none_when_rates_unknown():
    cost = tokens.calculate_cost(
        100,
        50,
        input_price_per_million=None,
        output_price_per_million=0.80,
    )

    assert cost is None


def test_agent_loop_stops_when_model_returns_final_answer(
    tmp_path,
    monkeypatch,
):
    # Prevent test output from being written to the real results folder.
    monkeypatch.setattr(tokens, "METRICS_FILE", tmp_path / "usage.jsonl")

    final_message = SimpleNamespace(
        content="נמצאו אפשרויות מתאימות.",
        tool_calls=None,
    )

    response = SimpleNamespace(
        choices=[
            SimpleNamespace(message=final_message)
        ],
        usage=SimpleNamespace(
            prompt_tokens=12,
            completion_tokens=8,
            prompt_tokens_details=None,
        ),
    )

    client = Mock()
    client.chat.completions.create.return_value = response

    result = run_agent_loop(
        client,
        [{"role": "user", "content": "מצא מקום"}],
        model="test-model",
        session_id="offline-test",
        turn_number=1,
        max_steps=3,
    )

    assert result["stop_reason"] == "final_answer"
    assert result["answer"] == "נמצאו אפשרויות מתאימות."
    assert client.chat.completions.create.call_count == 1

    saved_metrics = (tmp_path / "usage.jsonl").read_text(
        encoding="utf-8"
    )
    assert '"model_calls": 1' in saved_metrics
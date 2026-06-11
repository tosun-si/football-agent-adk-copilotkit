"""Run the golden dataset against a live ADK API server.

Prerequisites:
    The agent must be reachable at $ADK_URL (default: http://localhost:8080).
    Run `docker compose up` before running this.

Usage:
    uv run python -m golden_dataset.runner

Exit codes:
    0 — every case passed
    1 — at least one case failed (regressions printed to stdout)
"""
from __future__ import annotations

import json
import os
import sys
import unicodedata
import uuid
from pathlib import Path
from typing import Any, Callable
from urllib.request import Request, urlopen

import yaml

from golden_dataset.response import (
    AgentResponse,
    extract_text_from_adk_events,
    parse_response,
)

ADK_URL = os.environ.get("ADK_URL", "http://localhost:8080")
APP_NAME = "football_stats_agent"
USER_ID = "golden-runner"
DATASET_PATH = Path(__file__).parent / "dataset.yaml"


# === ADK call ===

def _post_json(url: str, payload: dict[str, Any]) -> Any:
    request = Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=120) as response:
        return json.loads(response.read())


def ask_agent(question: str) -> AgentResponse:
    session_id = f"golden-{uuid.uuid4().hex[:8]}"
    _post_json(
        f"{ADK_URL}/apps/{APP_NAME}/users/{USER_ID}/sessions/{session_id}",
        {},
    )
    events = _post_json(
        f"{ADK_URL}/run",
        {
            "appName": APP_NAME,
            "userId": USER_ID,
            "sessionId": session_id,
            "newMessage": {"parts": [{"text": question}]},
        },
    )
    return parse_response(extract_text_from_adk_events(events))


# === Assertions ===
# Each assertion returns None on success, or a human-readable error string.

Assertion = Callable[[AgentResponse, dict[str, Any]], str | None]


def _normalize(text: str) -> str:
    """Lower-case and strip accents, so comparisons survive `é` vs `e`."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).lower()


def _assert_contains_number(response: AgentResponse, expect: dict[str, Any]) -> str | None:
    value = float(expect["value"])
    if value in response.numbers:
        return None
    # Also look at chart data values — the agent sometimes answers a "how many"
    # with a chart even though we'd expect plain text.
    if response.chart:
        chart_values = [
            float(d.get("value")) for d in response.chart.get("data", [])
            if isinstance(d.get("value"), (int, float))
        ]
        if value in chart_values:
            return None
    return f"expected number {value} in text or chart, got numbers={response.numbers}"


def _assert_ordered_list(response: AgentResponse, expect: dict[str, Any]) -> str | None:
    expected: list[str] = expect["values"]
    expected_norm = [_normalize(v) for v in expected]

    # Prefer the chart data when available — it's the canonical ordering.
    if response.chart and isinstance(response.chart.get("data"), list):
        actual = [str(d.get("name", "")) for d in response.chart["data"]]
        actual_norm = [_normalize(v) for v in actual]
        if actual_norm[: len(expected)] == expected_norm:
            return None
        return f"chart data order {actual[: len(expected)]} != expected {expected}"

    # Fallback: check substrings appear in the right order in the text.
    haystack = _normalize(response.text)
    cursor = -1
    for needle in expected_norm:
        position = haystack.find(needle)
        if position == -1 or position < cursor:
            return f"ordered list {expected} not found in order in response text"
        cursor = position
    return None


def _assert_chart_spec(response: AgentResponse, expect: dict[str, Any]) -> str | None:
    if response.chart is None:
        return "expected a ```chart``` block, none found"

    expected_type = expect.get("chart_type")
    actual_type = response.chart.get("chart_type")
    if expected_type and actual_type != expected_type:
        return f"chart_type mismatch: expected {expected_type!r}, got {actual_type!r}"

    data = response.chart.get("data") or []
    n = len(data)
    lo = expect.get("min_data_points", 0)
    hi = expect.get("max_data_points", 10_000)
    if not lo <= n <= hi:
        return f"expected {lo}-{hi} data points, got {n}"
    return None


def _assert_no_chart(response: AgentResponse, expect: dict[str, Any]) -> str | None:
    if response.chart is not None:
        return f"expected no chart block, got chart_type={response.chart.get('chart_type')!r}"
    must_contain = expect.get("must_contain")
    if must_contain is None:
        return None
    needles = [must_contain] if isinstance(must_contain, str) else list(must_contain)
    haystack = _normalize(response.text)
    if any(_normalize(n) in haystack for n in needles):
        return None
    return f"expected text to contain one of {needles!r}"


ASSERTIONS: dict[str, Assertion] = {
    "contains_number": _assert_contains_number,
    "ordered_list": _assert_ordered_list,
    "chart_spec": _assert_chart_spec,
    "no_chart": _assert_no_chart,
}


# === Runner ===

def run(dataset_path: Path = DATASET_PATH) -> int:
    cases = yaml.safe_load(dataset_path.read_text())
    passes: list[str] = []
    failures: list[tuple[str, str]] = []

    for case in cases:
        case_id = case["id"]
        print(f"→ {case_id} ... ", end="", flush=True)

        try:
            response = ask_agent(case["question"])
        except Exception as exc:
            failures.append((case_id, f"agent call failed: {exc}"))
            print("ERROR")
            continue

        expect = case["expect"]
        check = ASSERTIONS.get(expect["type"])
        if check is None:
            failures.append((case_id, f"unknown assertion type {expect['type']!r}"))
            print("CONFIG ERROR")
            continue

        error = check(response, expect)
        if error:
            failures.append((case_id, error))
            print("FAIL")
        else:
            passes.append(case_id)
            print("ok")

    print()
    print(f"=== {len(passes)} passed, {len(failures)} failed (out of {len(cases)}) ===")

    if failures:
        print("\nFailures:")
        for case_id, reason in failures:
            print(f"  - {case_id}: {reason}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(run())

"""Pytest version of the golden dataset.

Each YAML case becomes a parametrized test that can pass / fail
independently. LLM responses are inherently stochastic, so flaky cases
are retried up to twice (with a 3s pause) before being marked as
failures — same dataset, same assertions as the standalone runner.

Usage:
    uv run pytest tests/test_golden.py -v
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from golden_dataset.runner import ASSERTIONS, ask_agent

CASES = yaml.safe_load(
    (Path(__file__).parent.parent / "golden_dataset" / "dataset.yaml").read_text()
)


@pytest.mark.flaky(reruns=2, reruns_delay=3)
@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_golden_case(case: dict) -> None:
    response = ask_agent(case["question"])
    expect = case["expect"]
    check = ASSERTIONS[expect["type"]]
    error = check(response, expect)
    assert error is None, f"{case['id']}: {error}"

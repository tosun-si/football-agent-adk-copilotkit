"""Parse the ADK agent's raw `/run` response into a structured form
usable by the golden-dataset assertions."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentResponse:
    """Structured view of the agent's response.

    Fields:
        text: full natural-language text (chart block included)
        text_without_chart: same, with the ```chart``` block stripped
        chart: parsed chart spec (or None if no chart block)
        numbers: numeric values found in the natural-language part
    """
    text: str
    text_without_chart: str = ""
    chart: dict[str, Any] | None = None
    numbers: list[float] = field(default_factory=list)


_CHART_BLOCK = re.compile(r"```chart\s*\n(.*?)\n```", re.DOTALL)
_NUMBER_TOKEN = re.compile(r"\b\d+(?:\.\d+)?\b")


def parse_response(text: str) -> AgentResponse:
    response = AgentResponse(text=text, text_without_chart=text)

    match = _CHART_BLOCK.search(text)
    if match:
        try:
            response.chart = json.loads(match.group(1))
        except json.JSONDecodeError:
            response.chart = None
        response.text_without_chart = text.replace(match.group(0), "")

    response.numbers = [
        float(m) for m in _NUMBER_TOKEN.findall(response.text_without_chart)
    ]
    return response


def extract_text_from_adk_events(events: list[Any] | dict[str, Any]) -> str:
    """Concatenate every textual `parts[*].text` from an ADK `/run` payload."""
    text = ""
    iterable = events if isinstance(events, list) else [events]
    for event in iterable:
        for part in (event.get("content", {}) or {}).get("parts", []) or []:
            chunk = part.get("text")
            if chunk:
                text += chunk
    return text

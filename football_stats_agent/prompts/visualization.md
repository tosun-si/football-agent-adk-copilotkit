## Visualization Output

When the question implies a comparison, ranking, distribution, or top-N
list across multiple entities (players, teams, positions...), output:

1. A short natural-language answer FIRST (max 3-4 sentences).
2. Then a single fenced code block tagged `chart` with a JSON spec.

There are TWO supported shapes: mono-series (one metric) and
multi-series (several metrics side by side).

### A. Mono-series (one metric)

Use this when the question asks about ONE quantitative metric only
(e.g. "top scorers", "save percentage by goalkeeper").

```chart
{
  "chart_type": "bar" | "line" | "pie",
  "title": "Descriptive chart title",
  "x_key": "name",
  "y_key": "value",
  "data": [
    {"name": "<label>", "value": <number>},
    ...
  ]
}
```

Mono-series rules:
- Use exactly `"name"` and `"value"` as the keys in every data item.
- Set `"x_key": "name"` and `"y_key": "value"`.

### B. Multi-series (several metrics)

Use this when the question explicitly asks for two or more metrics for
the same entities (e.g. "goals AND tackles per Lille player",
"goals vs assists for top 5 scorers"). Bars are rendered side by side
per x entry, with a legend.

```chart
{
  "chart_type": "bar" | "line",
  "title": "Descriptive chart title",
  "x_key": "name",
  "y_keys": ["goals", "tackles"],
  "y_labels": {"goals": "Buts marqués", "tackles": "Tacles réussis"},
  "data": [
    {"name": "Tim Weah", "goals": 0, "tackles": 2.5},
    {"name": "Jonathan David", "goals": 1, "tackles": 0.8}
  ]
}
```

Multi-series rules:
- `y_keys` is the array of metric keys, IN ORDER of appearance in legend.
- Each `data` item MUST contain `name` PLUS one numeric field per key.
- `y_labels` is optional but RECOMMENDED — use human-readable French
  labels (e.g. `"Buts marqués"`, `"Tacles réussis"`, `"Pourcentage d'arrêts"`).
- The `name` field is still the x-axis label and MUST stay literal.
- Do NOT mix `y_key` and `y_keys` — pick one shape.
- Pie charts are mono-series only — never use them with `y_keys`.

### General rules (both shapes)

- Use `bar` for rankings, top-N, comparisons across categories.
- Use `line` for trends over an ordered axis (rare).
- Use `pie` only when values represent shares of a whole (<=6 slices, mono only).
- Limit `data` to AT MOST 10 entries.
- Numeric values MUST be real numbers (not strings). Apply SAFE_CAST in SQL.
- Emit EXACTLY ONE chart block per response, or none at all.
- For purely factual questions (a single value, yes/no, identity), do NOT
  emit a chart block.
- Make `name` human-readable (e.g. `"Kylian Mbappe"` not `"k_mbappe"`).

### Examples

Question "Top buteurs France ?" → MONO with `y_key="value"`:
```json
{"chart_type":"bar","title":"Top buteurs France","x_key":"name","y_key":"value","data":[{"name":"Kylian Mbappe","value":8}]}
```

Question "Joueurs de Lille avec buts et tacles" → MULTI with `y_keys`:
```json
{"chart_type":"bar","title":"Joueurs de Lille — Buts vs Tacles","x_key":"name","y_keys":["goals","tackles"],"y_labels":{"goals":"Buts marqués","tackles":"Tacles réussis / 90"},"data":[{"name":"Tim Weah","goals":0,"tackles":2.5},{"name":"Jonathan David","goals":1,"tackles":0.8}]}
```

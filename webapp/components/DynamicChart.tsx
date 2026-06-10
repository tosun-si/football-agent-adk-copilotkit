"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export type ChartType = "bar" | "line" | "pie";

export interface ChartSpec {
  chart_type: ChartType;
  title?: string;
  x_key?: string;
  // Mono-series (legacy): one y axis.
  y_key?: string;
  // Multi-series (new): multiple side-by-side bars/lines per x entry.
  y_keys?: string[];
  // Optional human-readable label for each y key (legend), e.g. {"goals": "Buts"}.
  y_labels?: Record<string, string>;
  data: Array<Record<string, string | number>>;
}

const PALETTE = [
  "#065f46",
  "#10b981",
  "#34d399",
  "#0ea5e9",
  "#7c3aed",
  "#e11d48",
  "#f59e0b",
  "#84cc16",
  "#06b6d4",
  "#a855f7",
];

function resolveKey(
  preferred: string | undefined,
  fallbacks: string[],
  sampleItem: Record<string, unknown>
): string {
  if (preferred && preferred in sampleItem) return preferred;
  for (const fb of fallbacks) {
    if (fb in sampleItem) return fb;
  }
  return Object.keys(sampleItem)[0] ?? "name";
}

export function DynamicChart({ spec }: { spec: ChartSpec }) {
  if (!Array.isArray(spec.data) || spec.data.length === 0) {
    return (
      <div className="my-3 rounded-md border border-dashed border-gray-300 p-4 text-sm text-gray-500">
        Empty chart data.
      </div>
    );
  }

  const sample = spec.data[0] as Record<string, unknown>;
  const xKey = resolveKey(spec.x_key, ["name", "label", "category"], sample);

  // Resolve series: prefer y_keys (multi), fall back to y_key (mono).
  const seriesKeys: string[] =
    spec.y_keys && spec.y_keys.length > 0
      ? spec.y_keys.filter((k) => k in sample)
      : [resolveKey(spec.y_key, ["value", "count", "total"], sample)];
  const isMultiSeries = seriesKeys.length > 1;
  const labelFor = (k: string) => spec.y_labels?.[k] ?? k;

  return (
    <div className="my-4 rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      {spec.title && (
        <h3 className="mb-3 text-sm font-semibold text-gray-700">
          {spec.title}
        </h3>
      )}
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          {spec.chart_type === "line" ? (
            <LineChart data={spec.data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey={xKey} fontSize={12} />
              <YAxis fontSize={12} />
              <Tooltip />
              {isMultiSeries && <Legend />}
              {seriesKeys.map((k, i) => (
                <Line
                  key={k}
                  type="monotone"
                  dataKey={k}
                  name={labelFor(k)}
                  stroke={PALETTE[i % PALETTE.length]}
                  strokeWidth={2}
                  dot={{ r: 3 }}
                />
              ))}
            </LineChart>
          ) : spec.chart_type === "pie" ? (
            <PieChart>
              <Tooltip />
              <Legend />
              <Pie
                data={spec.data}
                dataKey={seriesKeys[0]}
                nameKey={xKey}
                outerRadius={80}
                label={(entry) => `${entry[xKey]}`}
              >
                {spec.data.map((_, i) => (
                  <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
                ))}
              </Pie>
            </PieChart>
          ) : (
            <BarChart data={spec.data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis
                dataKey={xKey}
                fontSize={12}
                interval={0}
                angle={-20}
                textAnchor="end"
                height={60}
              />
              <YAxis fontSize={12} />
              <Tooltip />
              {isMultiSeries && <Legend />}
              {seriesKeys.map((k, i) => (
                <Bar
                  key={k}
                  dataKey={k}
                  name={labelFor(k)}
                  fill={PALETTE[i % PALETTE.length]}
                >
                  {!isMultiSeries &&
                    spec.data.map((_, j) => (
                      <Cell key={j} fill={PALETTE[j % PALETTE.length]} />
                    ))}
                </Bar>
              ))}
            </BarChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}

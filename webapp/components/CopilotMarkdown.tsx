"use client";

import { DynamicChart, ChartSpec } from "./DynamicChart";

function tryParseChart(raw: string): ChartSpec | null {
  try {
    const parsed = JSON.parse(raw.trim());
    if (
      parsed &&
      typeof parsed === "object" &&
      typeof parsed.chart_type === "string" &&
      Array.isArray(parsed.data)
    ) {
      return parsed as ChartSpec;
    }
  } catch {
    // not valid JSON yet (streaming) — fall through
  }
  return null;
}

type CodeProps = {
  className?: string;
  children?: React.ReactNode;
};

function ChartAwareCode({ className, children, ...rest }: CodeProps) {
  const lang = /language-(\w+)/.exec(className ?? "")?.[1];
  if (lang === "chart") {
    const spec = tryParseChart(String(children));
    if (spec) {
      return <DynamicChart spec={spec} />;
    }
    return <code className="text-xs text-gray-400">(chart loading…)</code>;
  }
  return (
    <code className={className} {...rest}>
      {children}
    </code>
  );
}

export const chartTagRenderers = {
  code: ChartAwareCode,
};

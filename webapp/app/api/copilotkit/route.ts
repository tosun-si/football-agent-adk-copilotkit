import {
  CopilotRuntime,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { BuiltInAgent } from "@copilotkit/runtime/v2";
import { EventType } from "@ag-ui/core";
import { NextRequest } from "next/server";

const CLOUD_RUN_URL = process.env.CLOUD_RUN_API_URL ?? "http://localhost:8080";
const APP_NAME = "football_stats_agent";
const USER_ID = "webapp-copilot-user";

async function ensureSession(sessionId: string): Promise<void> {
  const url = `${CLOUD_RUN_URL}/apps/${APP_NAME}/users/${USER_ID}/sessions/${sessionId}`;
  await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
}

async function callAdk(
  userText: string,
  sessionId: string
): Promise<string> {
  await ensureSession(sessionId);

  const res = await fetch(`${CLOUD_RUN_URL}/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      appName: APP_NAME,
      userId: USER_ID,
      sessionId,
      newMessage: { parts: [{ text: userText }] },
    }),
  });

  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`ADK error ${res.status}: ${errText}`);
  }

  const data = await res.json();
  let text = "";
  const events = Array.isArray(data) ? data : [data];
  for (const event of events) {
    const parts = event?.content?.parts ?? [];
    for (const part of parts) {
      if (part?.text) text += part.text;
    }
  }
  return text || "(empty response)";
}

function extractUserText(message: unknown): string {
  if (!message || typeof message !== "object") return "";
  const m = message as { content?: unknown };
  if (typeof m.content === "string") return m.content;
  if (Array.isArray(m.content)) {
    return m.content
      .map((part: unknown) => {
        if (part && typeof part === "object" && "text" in part) {
          return (part as { text?: string }).text ?? "";
        }
        return "";
      })
      .join("");
  }
  return "";
}

const adkAgent = new BuiltInAgent({
  type: "custom",
  factory: async function* (ctx) {
    const messages = (ctx.input.messages ?? []) as Array<{ role: string }>;
    const lastUser = [...messages].reverse().find((m) => m?.role === "user");
    const userText = extractUserText(lastUser);
    const sessionId = `cpk-${ctx.input.threadId ?? "default"}`;

    let text: string;
    try {
      text = await callAdk(userText, sessionId);
    } catch (err) {
      text = `Error calling ADK: ${
        err instanceof Error ? err.message : String(err)
      }`;
    }

    const messageId = crypto.randomUUID();

    yield {
      type: EventType.TEXT_MESSAGE_START,
      messageId,
      role: "assistant",
    } as never;
    yield {
      type: EventType.TEXT_MESSAGE_CONTENT,
      messageId,
      delta: text,
    } as never;
    yield {
      type: EventType.TEXT_MESSAGE_END,
      messageId,
    } as never;
  },
});

const runtime = new CopilotRuntime({
  agents: { default: adkAgent },
});

export const POST = async (req: NextRequest) => {
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    endpoint: "/api/copilotkit",
  });
  return handleRequest(req);
};

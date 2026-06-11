# CFP (EN) — Football Agent ADK + Copilot Kit

Reusable speaker notes for submitting this talk to English-speaking
Call for Papers. Each section can be copied as-is into the relevant
field of the CFP form.

---

## Title

> Who scored the most goals? Building an AI agent that queries data in natural language

---

## Abstract

Designing an end-to-end agentic application remains a real challenge as soon as you need to integrate actual data and business rules.

In this talk, I walk through a concrete case: a statistics agent for the FIFA World Cup ⚽, able to answer questions in natural language, generate and execute SQL queries, then present the results in a human-readable form, alongside dynamically generated charts inside a conversational UI.

We will see how to build this agent with the Agent Development Kit (ADK) framework, combining prompting and business rules to produce reliable queries. The agent is connected to BigQuery via the MCP protocol and deployed on Google Cloud, with different runtime options (Cloud Run and Agent Engine).

The goal is to illustrate, through this concrete case, a complete agentic architecture along with the design and deployment choices required to move to production. Even though this implementation relies on Google Cloud, the patterns shown stay reusable with other infrastructures and any data source exposed through MCP.

---

## Elevator pitch (Twitter-length / short summary)

> An AI agent that answers natural-language questions about the 2022 FIFA World Cup, generates SQL through MCP and renders its own charts in a conversational UI. Demoed end-to-end on Google Cloud — but the patterns (ADK, MCP, modular prompts, agentic UI) are portable to any infrastructure.

---

## Target audience

Intermediate-level talk for front / back / data engineers, DevOps / SRE — and more broadly for any developer who wants to see a real agentic stack beyond a "hello world" demo. Python basics and curiosity about LLMs are enough — no prior ADK or MCP experience required.

---

## Takeaways

By the end of the session, attendees will leave with:

1. **A clear mental model** of ADK and how it compares to other agent frameworks (LangChain, LlamaIndex).
2. **A practical understanding of MCP**: what the protocol is for and what a cloud-managed MCP server brings to the table vs a custom one.
3. **Two deployment paths** compared live (Cloud Run vs Agent Engine), with their real trade-offs (cold start, observability, cost, control).
4. **A modular prompt pattern**: splitting the system prompt into one `.md` file per concern (role, schema, query workflow, business rules, visualization) so non-developers can review and edit them.
5. **A recipe for conversational visualization**: making an LLM agent draw inside a React UI via Copilot Kit + Recharts, without writing a custom parser for every question type.
6. **The actual production pitfalls**: subtle env vars, IAM gotchas, OpenTelemetry exporters, `pyproject.toml` extras — all the technical debt an idealised blog post hides.

---

## Tech stack

- **Agent**: Google ADK 2.1 (`LlmAgent`, AgentRegistry, MCP toolset)
- **Model**: Gemini 2.5 Flash via Vertex AI
- **Data**: BigQuery (2022 FIFA World Cup dataset)
- **MCP**: Google-managed BigQuery MCP server, discovered through Agent Registry
- **Agent API**: `adk api_server` (FastAPI) deployed on Cloud Run
- **Managed runtime**: Vertex AI Agent Engine (rebranded "Agent Platform" since 2026)
- **Conversational frontend**: Next.js + Copilot Kit + Recharts for dynamic charts
- **Python packaging**: uv + Docker multi-stage + Docker Bake
- **CI/CD**: Cloud Build with registry cache
- **Observability**: OpenTelemetry + Cloud Trace + the Trace tab in Agent Platform

---

## Format

- **Duration**: 45 minutes
- **Mix**: ~60% live demo + ~40% architecture slides
- **End-to-end architecture**: the session walks the full chain, from local development (Docker Compose orchestrating the ADK agent, the MCP server and the Copilot Kit webapp side by side) to a serverless deployment on Google Cloud (Cloud Run + Agent Engine, driven by Cloud Build). The local-to-prod transition concretely illustrates the Docker packaging choices, the CI/CD pipeline and the runtime differences between the two worlds.
- **Demos**: 3 questions over the dataset (top scorers, Mbappé vs Messi comparison, Lille players benchmarked against Mbappé), going up in complexity — simple bar chart, then multi-series, then a data story with a local twist. All demos run locally through Docker Compose (`adk web` + Copilot Kit webapp + MCP); the production version on Cloud Run and the Agent Platform Playground are shown at the end.

---

## Notes for organisers

- The frontend shipped in this repo is a custom **Next.js + Copilot Kit** UI that renders the agent's answers as **Recharts charts** (bar / pie / line, mono or multi-series) directly inside the conversation. That UI is what makes the agent feel production-ready and user-friendly instead of just being a technical chat. During the demo I also use the UI bundled with `adk web` (shipped by the ADK framework, not coded in this repo) to show the raw agent and its execution DAG.
- The agent is intentionally **read-only on BigQuery** at the IAM layer (`bigquery.dataViewer` + `bigquery.jobUser` roles), which doubles as a concrete defense-in-depth example during the governance part of the talk.

---

## References

- 📦 **Source code**: https://github.com/tosun-si/football-agent-adk-copilotkit
- 📝 **In-depth Medium article**: https://medium.com/google-cloud/end-to-end-ai-agent-on-gcp-adk-bigquery-mcp-agent-engine-and-cloud-run-4843fec27c13
- 🎞️ **Slides (DevLille example deck)**: https://docs.google.com/presentation/d/19iBG2qq_2fFLu2J2NDfEkp0fsZD2Lzu9/edit?usp=sharing&ouid=107222582194830665741&rtpof=true&sd=true
- 🎨 **Architecture diagrams**: `diagrams/` folder in the repo

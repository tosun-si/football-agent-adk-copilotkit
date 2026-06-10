import os
from pathlib import Path

from google.adk.agents import LlmAgent
from google.adk.integrations.agent_registry import AgentRegistry
from vertexai.agent_engines import AdkApp

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "gb-poc-373711")
DATASET_LOCATION = os.environ.get("LOCATION", "europe-west1")  # For BigQuery Dataset
REGISTRY_LOCATION = "global"  # Agent Registry is global only for MCP servers
MODEL = "gemini-2.5-flash"

# System instructions are split across `prompts/*.md` files, one per
# concern, so business stakeholders can review and edit them without
# touching Python. Files are concatenated in the order below at agent
# creation time. The `{{PROJECT_ID}}` placeholder is substituted with
# the actual project id so the prompts can stay project-agnostic.
PROMPTS_DIR = Path(__file__).parent / "prompts"
PROMPT_ORDER = [
    "role.md",
    "schema.md",
    "query_workflow.md",
    "business_rules.md",
    "visualization.md",
]


def _load_system_instruction() -> str:
    parts = [(PROMPTS_DIR / name).read_text() for name in PROMPT_ORDER]
    return "\n\n".join(parts).replace("{{PROJECT_ID}}", PROJECT_ID)


SYSTEM_INSTRUCTION = _load_system_instruction()


def session_service_builder():
    from google.adk.sessions import VertexAiSessionService
    return VertexAiSessionService(project=PROJECT_ID, location=DATASET_LOCATION)


def get_header(context):
    return {"x-goog-user-project": PROJECT_ID}


BIGQUERY_MCP_DISPLAY_NAME = "bigquery.googleapis.com"


def _resolve_mcp_server_name(registry: AgentRegistry, display_name: str) -> str:
    """Look up an MCP server's resource name by its display name.

    Agent Registry assigns opaque UUIDs to each MCP server (e.g.
    `projects/.../mcpServers/agentregistry-00000000-...-921a-c233b003d75f`)
    so we cannot hardcode the resource name as we could with the old
    Cloud API Registry. We list servers and match by `displayName`
    (e.g. `bigquery.googleapis.com`).
    """
    response = registry.list_mcp_servers()
    for server in response.get("mcpServers", []):
        if server.get("displayName") == display_name:
            return server["name"]
    raise ValueError(
        f"No MCP server with displayName {display_name!r} found in Agent Registry "
        f"(project={PROJECT_ID}, location={REGISTRY_LOCATION})."
    )


def create_agent():
    agent_registry = AgentRegistry(
        project_id=PROJECT_ID,
        location=REGISTRY_LOCATION,
        header_provider=get_header,
    )

    mcp_server_name = _resolve_mcp_server_name(
        agent_registry, BIGQUERY_MCP_DISPLAY_NAME
    )
    toolset = agent_registry.get_mcp_toolset(mcp_server_name)

    if not toolset:
        raise ValueError("Could not load BigQuery toolset from Agent Registry.")

    return LlmAgent(
        model=MODEL,
        name="football_stats_agent",
        description=(
            "Answers questions about Qatar 2022 FIFA World Cup using BigQuery: "
            "player stats, team rankings, goals, assists, defensive metrics, "
            "goalkeeper save percentages, and computed performance ratings."
        ),
        instruction=SYSTEM_INSTRUCTION,
        tools=[toolset],
    )


def create_app():
    """Used for programmatic deployment via ModuleAgent and agent_engines.create()."""
    agent = create_agent()
    return AdkApp(
        agent=agent,
        session_service_builder=session_service_builder
    )


root_agent = create_agent()

import json
import logging
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import aiplatform_v1beta1
from pydantic import BaseModel

logger = logging.getLogger(__name__)

app = FastAPI(title="Agent Engine Proxy")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST"],
    allow_headers=["*"],
)

LOCATION = os.environ.get("LOCATION", "europe-west1")
try:
    PROJECT_NUMBER = os.environ["PROJECT_NUMBER"]
    ENGINE_ID = os.environ["ENGINE_ID"]
except KeyError as exc:
    raise RuntimeError(
        f"{exc.args[0]} env var is required. PROJECT_NUMBER is the numeric "
        "GCP project number; ENGINE_ID is the Vertex AI Agent Engine "
        "resource id (last segment of projects/.../reasoningEngines/<id>)."
    ) from exc
RESOURCE_NAME = (
    f"projects/{PROJECT_NUMBER}/locations/{LOCATION}/reasoningEngines/{ENGINE_ID}"
)
USER_ID = "proxy-user"

client = aiplatform_v1beta1.ReasoningEngineExecutionServiceClient(
    client_options={"api_endpoint": f"{LOCATION}-aiplatform.googleapis.com"}
)


class QueryRequest(BaseModel):
    message: str


class QueryResponse(BaseModel):
    response: str


def _create_session() -> str:
    response = client.query_reasoning_engine(
        request=aiplatform_v1beta1.types.QueryReasoningEngineRequest(
            name=RESOURCE_NAME,
            class_method="async_create_session",
            input={"user_id": USER_ID},
        ),
        timeout=30,
    )
    return response.output.get("id")


def _extract_text(event_data: bytes) -> str:
    """Concatenate every textual `parts[*].text` from a single event."""
    data = json.loads(event_data.decode("utf-8"))
    parts = data.get("content", {}).get("parts", [])
    return "".join(
        part["text"]
        for part in parts
        if isinstance(part, dict) and part.get("text")
    )


def _stream_query(message: str, session_id: str) -> str:
    """Stream a query to the Agent Engine and return the full text response.

    A single agent turn can emit multiple text parts (natural-language
    answer, fenced chart block, etc.) across one or more events. We
    concatenate every text we see so the frontend gets the complete
    response (notably the ```chart``` block that the Copilot Kit
    markdown renderer expects).
    """
    response_stream = client.stream_query_reasoning_engine(
        request=aiplatform_v1beta1.types.StreamQueryReasoningEngineRequest(
            name=RESOURCE_NAME,
            class_method="async_stream_query",
            input={
                "message": message,
                "user_id": USER_ID,
                "session_id": session_id,
            },
        ),
        timeout=120,
    )

    chunks = []
    for event in response_stream:
        if event.data:
            chunk = _extract_text(event.data)
            if chunk:
                chunks.append(chunk)

    return "".join(chunks)


@app.post("/query", response_model=QueryResponse)
async def query_agent(request: QueryRequest):
    try:
        session_id = _create_session()
        text = _stream_query(request.message, session_id)
        return QueryResponse(response=text or "No response from agent")
    except Exception as e:
        logger.error("Agent Engine error: %s", e)
        raise HTTPException(status_code=502, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "ok"}

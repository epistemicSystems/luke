"""
FastAPI server for Insight Graph.

Provides REST endpoints for external integrations (webhooks, dashboards, etc.)
"""

import os
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ..core.graph import InsightGraph
from ..core.models import Issue, IssueSeverity, IssueStatus, Message, MessageLabel
from ..core.vector_store import VectorStore
from ..rag.actions import DevActions
from ..rag.chat import InsightCopilot
from ..rag.retriever import DualIndexRetriever

load_dotenv()

# Initialize
graph_data_dir = Path(os.getenv("GRAPH_DATA_DIR", "./data/graph"))
chroma_persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma")
openai_api_key = os.getenv("OPENAI_API_KEY")

graph = InsightGraph(data_dir=graph_data_dir)
vector_store = None

if openai_api_key:
    vector_store = VectorStore(
        persist_dir=chroma_persist_dir,
        collection_name="insight_graph",
        openai_api_key=openai_api_key,
    )

copilot = InsightCopilot(graph, vector_store) if vector_store else None
actions = DevActions(graph)

# Create app
app = FastAPI(
    title="Insight Graph API",
    description="Community intelligence API for game developers",
    version="0.1.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === Request/Response Models ===


class ChatRequest(BaseModel):
    query: str
    channel_filter: Optional[str] = None


class ChatResponse(BaseModel):
    query: str
    answer: str
    context_summary: dict[str, int]


class CreateIssueRequest(BaseModel):
    title: str
    description: str
    message_ids: list[str]
    severity: str
    tags: Optional[list[str]] = None


class SearchRequest(BaseModel):
    query: str
    top_k: int = 10


class PersonaSimulationRequest(BaseModel):
    change_description: str
    context_refs: Optional[list[str]] = None


# === Health Check ===


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "service": "Insight Graph API",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
def health():
    """Health check."""
    return {
        "status": "healthy",
        "graph_available": True,
        "vector_store_available": vector_store is not None,
        "copilot_available": copilot is not None,
    }


# === Stats ===


@app.get("/stats")
def get_stats():
    """Get graph statistics."""
    users = graph.list_users()
    messages = graph.list_messages(limit=10000)
    issues = graph.list_issues()
    personas = graph.list_personas()

    stats = {
        "users": len(users),
        "messages": len(messages),
        "issues": len(issues),
        "personas": len(personas),
    }

    if vector_store:
        vec_stats = vector_store.get_stats()
        stats["embeddings"] = vec_stats["count"]

    return stats


# === Chat ===


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """Query the copilot."""
    if not copilot:
        raise HTTPException(status_code=503, detail="Copilot not available (OpenAI key required)")

    result = copilot.chat(request.query, channel_filter=request.channel_filter)

    context_summary = {
        "messages": len(result["context"]["messages"]),
        "issues": len(result["context"]["issues"]),
        "personas": len(result["context"]["personas"]),
    }

    return ChatResponse(
        query=request.query,
        answer=result["answer"],
        context_summary=context_summary,
    )


# === Search ===


@app.post("/search")
def search(request: SearchRequest):
    """Semantic search over messages."""
    if not vector_store:
        raise HTTPException(status_code=503, detail="Vector store not available")

    results = vector_store.search(request.query, top_k=request.top_k)

    return {
        "query": request.query,
        "results": results,
    }


# === Issues ===


@app.get("/issues")
def list_issues(status: Optional[str] = None, limit: int = Query(default=20, le=100)):
    """List issues."""
    issues = graph.list_issues(status=status)[:limit]

    return {
        "count": len(issues),
        "issues": [issue.model_dump(mode="json") for issue in issues],
    }


@app.get("/issues/{issue_id}")
def get_issue(issue_id: str):
    """Get issue details."""
    try:
        issue = graph.get_issue(UUID(issue_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid issue ID")

    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    return issue.model_dump(mode="json")


@app.post("/issues")
def create_issue(request: CreateIssueRequest):
    """Create a new issue."""
    try:
        severity = IssueSeverity(request.severity)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid severity")

    try:
        message_ids = [UUID(mid) for mid in request.message_ids]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid message IDs")

    issue = actions.create_issue_from_messages(
        title=request.title,
        description=request.description,
        message_ids=message_ids,
        severity=severity,
        tags=set(request.tags) if request.tags else set(),
    )

    return issue.model_dump(mode="json")


@app.patch("/issues/{issue_id}/status")
def update_issue_status(issue_id: str, status: str, owner: Optional[str] = None):
    """Update issue status."""
    try:
        issue_uuid = UUID(issue_id)
        new_status = IssueStatus(status)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid issue ID or status")

    actions.update_issue_status(issue_uuid, new_status, owner)

    return {"status": "updated", "issue_id": issue_id}


# === Personas ===


@app.get("/personas")
def list_personas():
    """List personas."""
    personas = graph.list_personas()

    return {
        "count": len(personas),
        "personas": [persona.model_dump(mode="json") for persona in personas],
    }


@app.post("/personas/simulate")
def simulate_persona(request: PersonaSimulationRequest):
    """Simulate persona reactions."""
    if not vector_store:
        raise HTTPException(status_code=503, detail="Vector store not available")

    from ..personas.agents import PersonaSimulator

    profiles_dir = Path(__file__).parent.parent / "personas" / "profiles"
    simulator = PersonaSimulator(graph, vector_store, profiles_dir)

    context_refs = None
    if request.context_refs:
        try:
            context_refs = [UUID(ref) for ref in request.context_refs]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid context reference IDs")

    result = simulator.simulate_change(request.change_description, context_refs)

    return result


# === Timeline ===


@app.get("/timeline")
def get_timeline(entity_type: Optional[str] = None, hours: int = Query(default=24, le=168)):
    """Get recent timeline events."""
    from datetime import datetime, timedelta

    since = datetime.utcnow() - timedelta(hours=hours)
    events = graph.get_timeline(entity_type=entity_type, since=since)

    return {
        "count": len(events),
        "events": events,
    }


# === Briefs ===


@app.get("/brief/daily")
def generate_daily_brief(hours: int = Query(default=24, le=168), format: str = "discord"):
    """Generate daily brief."""
    if not vector_store:
        raise HTTPException(status_code=503, detail="Vector store not available")

    from ..briefs.daily import DailyBriefGenerator

    generator = DailyBriefGenerator(graph, vector_store)
    result = generator.generate(lookback_hours=hours, format=format)

    return result


# === Run Server ===


def main():
    """Run the API server."""
    import uvicorn

    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()

# Insight Graph

A living, multi-modal PKM brain for private-beta game communities that turns Discord chaos into durable knowledge, emergent personas, and on-tap copilots.

## Value Proposition

**Reduce developer toil by 10×** with a unified "Insight Graph" that ingests Discord + helpdesk, auto-triages bugs, surfaces clustered personas, and lets devs query everything via chat/voice. Personas become interactive agents that role-play expected reactions to new changes and predict impact by cohort.

## System Architecture

```
Ingest → Structure → Understand → Summarize → Act
```

- **Ingest**: Discord, helpdesk, crash logs, hardware telemetry, screenshots/clips
- **Structure**: Normalize to Insight Graph (users, threads, issues, builds) + vector store
- **Understand**: RAG + clustering + spectral analytics → Persona bases + pain-point maps
- **Summarize**: LLMs produce daily/weekly briefs, PRD-ready excerpts, change diffs
- **Act**: Chat/voice interface, one-click tickets, persona sims, impact forecasts

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Discord token, OpenAI key, etc.

# Initialize the graph
python -m insight_graph.init

# Start ingestion (Discord)
python -m insight_graph.ingest.discord

# Launch RAG chat interface
python -m insight_graph.chat

# Generate daily brief
python -m insight_graph.briefs.daily
```

## Project Structure

```
insight_graph/
├── core/                 # Core data models and graph
│   ├── models.py        # User, Message, Thread, Issue, Persona, etc.
│   ├── graph.py         # Insight Graph operations
│   └── vector_store.py  # Embedding storage and retrieval
├── ingest/              # Data ingestion pipelines
│   ├── discord_bot.py   # Discord event consumer
│   ├── helpdesk.py      # Ticket import
│   └── normalize.py     # Cleanup and deduplication
├── understand/          # Analytics and persona extraction
│   ├── clustering.py    # Spectral clustering, NMF
│   ├── personas.py      # Persona basis extraction
│   └── sheaf.py         # Hodge decomposition (optional)
├── rag/                 # Retrieval and generation
│   ├── retriever.py     # Dual index search
│   ├── chat.py          # Conversational interface
│   └── actions.py       # Dev actions (create ticket, tag, etc.)
├── personas/            # Persona profiles and agents
│   ├── profiles/        # YAML persona definitions
│   ├── agents.py        # Interactive persona LLM agents
│   └── simulator.py     # Impact forecasting
├── briefs/              # Summarization and reporting
│   ├── daily.py         # Daily standup brief
│   ├── weekly.py        # Weekly rollup
│   └── voice.py         # TTS generation
└── api/                 # Optional REST/WebSocket API
    └── server.py        # FastAPI server
```

## Core Concepts

### Data Model

- **User**: Community member with capability bands (hardware, playstyle)
- **Message**: Discord message with embeddings and labels
- **Thread**: Conversation with topic labels and sentiment timeline
- **Issue**: Bug/feature with repro steps, severity, linked threads
- **Persona**: Archetypal user basis with weights and prompt profile
- **Insight**: Hypothesis with evidence and confidence
- **Decision**: Choice with context, rationale, and expected impact

### Personas

Emergent archetypes extracted via spectral analysis and NMF:
- **Low-VRAM Explorer**: Performance-sensitive, exploration-focused
- **Meta-Chaser Min/Maxer**: Competitive, optimization-driven
- **Controller-First Console Dad**: Comfort-focused, time-constrained
- **Lore-Driven Completionist**: Story-focused, high engagement

Each persona becomes an interactive agent for impact simulation.

## Development Phases

### Phase 1 (MVP, 2-3 weeks)
- ✓ Discord ingestion + vector store
- ✓ RAG chat with dev actions
- ✓ Two seed personas
- ✓ Daily auto-brief

### Phase 2 (4-6 weeks)
- Spectral clustering + NMF personas
- Impact heuristics
- Git-style timeline
- Voice interface

### Phase 3 (6-10 weeks)
- Hodge/sheaf analytics
- GNN forecaster
- Hardware telemetry cohorts
- Design polish + plugins

## Metrics

- **Toil ↓**: Time-to-find (p95), time-to-owner, context switches/day
- **Quality ↑**: Duplicate-ticket rate, false-merge rate, similar-issue precision/recall
- **Persona utility**: Coverage, stability, prediction Brier score
- **Adoption**: Weekly active queries, voice usage, one-tap actions

## Privacy & Ethics

- Explicit opt-in per user/channel
- PII redaction, k-anonymity for cohorts
- Capability bands (not demographics)
- Model cards + audit logs
- "Why am I seeing this?" transparency

## License

[Your License Here]

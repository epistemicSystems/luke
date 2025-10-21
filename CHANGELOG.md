# Changelog

All notable changes to the Insight Graph project.

## [0.1.0] - 2024-01-15

### Added - Phase 1 MVP Complete

**Core Infrastructure**
- Data models (User, Message, Thread, Issue, Build, Persona, Insight, Decision)
- Git-like versioned graph storage with timeline/audit
- Vector store integration (ChromaDB + OpenAI embeddings)
- Discord ingestion bot with auto-labeling
- PII redaction (emails, IPs)
- Deduplication via semantic similarity

**RAG & Intelligence**
- Dual-index retriever (dense vector + symbolic graph)
- Interactive chat copilot
- Dev actions (create issue, tag, link, merge, triage)
- Context-aware answers with evidence citation

**Personas**
- 4 seed persona profiles (Low-VRAM Explorer, Meta-Chaser, Controller Dad, Lore Completionist)
- Interactive LLM agents for impact simulation
- In-character reactions to proposed changes
- Impact scoring by issue tags and persona weights

**Briefs & Reporting**
- Daily brief generator (Discord/Slack/text formats)
- Hot topics extraction
- Sentiment trend analysis
- Voice readouts (full + 60s summaries via OpenAI TTS)

**Analytics Foundation**
- Message clustering (K-means, spectral)
- User clustering into persona segments
- NMF-based persona basis extraction
- Sentiment analysis utilities

**Tools & Integration**
- Unified CLI tool (`insight-graph` command)
- REST API server (FastAPI)
- Stats, search, chat, issues, personas endpoints
- Demo data initialization script

**Deployment & Operations**
- Docker + docker-compose setup
- Health check scripts
- Backup/restore utilities
- Comprehensive documentation

**Testing**
- Unit tests for models, graph, actions
- Test fixtures and pytest configuration

**Documentation**
- README with architecture overview
- QUICKSTART guide (5-minute setup)
- API reference
- DEPLOYMENT guide
- ADVANCED features roadmap

### Architecture

```
Ingest → Structure → Understand → Summarize → Act

Discord/Helpdesk → Graph + Vector Store → RAG → Copilot → Actions
                                        ↓
                                    Personas → Simulation
                                        ↓
                                    Briefs → Voice
```

### Metrics Tracked
- Toil reduction: time-to-find, context switches
- Quality: duplicate-ticket rate, precision/recall
- Persona utility: coverage, stability, Brier score
- Adoption: queries, voice usage, one-tap actions

---

## [Unreleased] - Phase 2 Roadmap

### Planned
- Automatic persona extraction via spectral clustering
- GNN-based impact forecasting
- Git-style timeline with branch/merge
- Hodge decomposition for controversy detection
- Hardware telemetry cohorts (opt-in)
- JIRA/Linear integrations
- Real-time dashboard
- Voice wake-word interface

---

## Version Format

`[MAJOR.MINOR.PATCH]`
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

Release cycle: Every 2-4 weeks

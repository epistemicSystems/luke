# API Reference

Core modules and their interfaces.

## Core Models

### `insight_graph.core.models`

#### User

Represents a community member.

```python
from insight_graph.core.models import User, CapabilityBand, PlaystyleSignal

user = User(
    discord_id="123456789",
    discord_handle="PlayerName#1234",
    capability_bands={CapabilityBand.LOW_VRAM, CapabilityBand.CONTROLLER},
    playstyle_signals={PlaystyleSignal.EXPLORER},
    opted_in=True
)
```

#### Message

Represents a Discord message.

```python
from insight_graph.core.models import Message, MessageLabel

msg = Message(
    user_id=user.id,
    discord_message_id="987654321",
    channel_id="channel_123",
    text="FPS drops in swamp biome",
    labels={MessageLabel.BUG_REPORT, MessageLabel.PERFORMANCE}
)
```

#### Issue

Represents a tracked bug or feature request.

```python
from insight_graph.core.models import Issue, IssueSeverity, IssueStatus

issue = Issue(
    title="FPS drops in swamp biome",
    description="Multiple reports of FPS dropping from 60 to 25",
    severity=IssueSeverity.HIGH,
    status=IssueStatus.TRIAGED,
    linked_message_ids=[msg.id],
    tags={"performance", "swamp", "particles"}
)
```

## Graph Operations

### `insight_graph.core.graph.InsightGraph`

Main graph storage interface.

```python
from pathlib import Path
from insight_graph.core.graph import InsightGraph

graph = InsightGraph(data_dir=Path("./data/graph"))

# Save entities
graph.save_user(user)
graph.save_message(msg)
graph.save_issue(issue)

# Retrieve entities
user = graph.get_user(user_id)
issue = graph.get_issue(issue_id)

# List entities
all_users = graph.list_users()
open_issues = graph.list_issues(status="new")

# Timeline / version history
timeline = graph.get_timeline(entity_type="issue", since=datetime.now() - timedelta(days=7))
```

## Vector Store

### `insight_graph.core.vector_store.VectorStore`

Semantic search over messages.

```python
from insight_graph.core.vector_store import VectorStore

vector_store = VectorStore(
    persist_dir="./data/chroma",
    collection_name="insight_graph",
    openai_api_key="sk-..."
)

# Add message
embedding_id = vector_store.add_message(
    message_id=msg.id,
    text=msg.cleaned_text,
    metadata={"channel_id": msg.channel_id, "labels": ["bug", "performance"]}
)

# Search
results = vector_store.search(
    query="performance issues in biomes",
    top_k=10,
    filter_metadata={"channel_id": "channel_123"}
)
```

## RAG Interface

### `insight_graph.rag.retriever.DualIndexRetriever`

Combines vector search with graph queries.

```python
from insight_graph.rag.retriever import DualIndexRetriever

retriever = DualIndexRetriever(graph, vector_store, top_k=10)

# Retrieve context for a query
context = retriever.retrieve(
    query="What's blocking onboarding?",
    include_issues=True,
    include_personas=True
)

# context = {
#     "messages": [...],
#     "issues": [...],
#     "personas": [...]
# }
```

### `insight_graph.rag.chat.InsightCopilot`

Conversational interface.

```python
from insight_graph.rag.chat import InsightCopilot

copilot = InsightCopilot(graph, vector_store)

result = copilot.chat("Show me FPS issues")
print(result["answer"])  # LLM-generated answer
print(result["context"])  # Retrieved context
```

### `insight_graph.rag.actions.DevActions`

Developer actions.

```python
from insight_graph.rag.actions import DevActions
from insight_graph.core.models import IssueSeverity

actions = DevActions(graph)

# Create issue from messages
issue = actions.create_issue_from_messages(
    title="Swamp FPS drops",
    description="Multiple reports",
    message_ids=[msg1.id, msg2.id],
    severity=IssueSeverity.HIGH,
    tags={"performance", "swamp"}
)

# Tag a message
actions.tag_message(msg.id, MessageLabel.REPRO_STEPS)

# Update issue status
actions.update_issue_status(issue.id, IssueStatus.IN_PROGRESS, owner="alice")
```

## Personas

### `insight_graph.personas.agents.PersonaAgent`

Interactive persona agent.

```python
from pathlib import Path
from insight_graph.personas.agents import PersonaAgent

agent = PersonaAgent(
    profile_path=Path("./insight_graph/personas/profiles/low-vram-explorer.yaml"),
    graph=graph,
    vector_store=vector_store
)

# Simulate reaction to a change
result = agent.simulate_reaction(
    change_description="Adding volumetric fog to swamp biome",
    context_refs=[msg1.id, msg2.id]
)

print(result["reaction"])  # In-character reaction
```

### `insight_graph.personas.agents.PersonaSimulator`

Multi-persona simulation.

```python
from insight_graph.personas.agents import PersonaSimulator

simulator = PersonaSimulator(
    graph=graph,
    vector_store=vector_store,
    profiles_dir=Path("./insight_graph/personas/profiles")
)

# Run all personas
result = simulator.simulate_change("New particle system in combat")
print(result["summary"])  # Combined reactions
```

## Briefs

### `insight_graph.briefs.daily.DailyBriefGenerator`

Generate daily briefs.

```python
from insight_graph.briefs.daily import DailyBriefGenerator

generator = DailyBriefGenerator(graph, vector_store)

brief = generator.generate(lookback_hours=24, format="discord")
print(brief["formatted"])  # Ready to paste into Discord
```

### `insight_graph.briefs.voice.VoiceGenerator`

Generate voice readouts.

```python
from insight_graph.briefs.voice import VoiceGenerator

voice_gen = VoiceGenerator(output_dir=Path("./data/voice"))

# Full audio
audio_path = voice_gen.generate_from_brief(brief["formatted"])

# 60-second summary
short_audio = voice_gen.generate_60s_summary(brief["formatted"])
```

## Normalization

### `insight_graph.ingest.normalize.Normalizer`

Deduplication and cleanup.

```python
from insight_graph.ingest.normalize import Normalizer

normalizer = Normalizer(graph, vector_store)

# Find near-duplicate messages
duplicates = normalizer.find_near_duplicate_messages(msg.id, similarity_threshold=0.95)

# Find duplicate issues
dup_issues = normalizer.find_duplicate_issues(issue.id)

# Merge duplicates
normalizer.merge_issues(primary_id=issue1.id, duplicate_ids=[issue2.id, issue3.id])
```

## Events and Hooks

The graph logs all changes to a version log. You can subscribe to events:

```python
# Get recent changes
changes = graph.get_timeline(since=datetime.now() - timedelta(hours=1))

for change in changes:
    print(f"{change['action']} on {change['entity_type']} {change['entity_id']}")
    # e.g., "create on message abc-123"
```

## Next Steps

- See [QUICKSTART.md](./QUICKSTART.md) for end-to-end examples
- See [README.md](../README.md) for architecture overview

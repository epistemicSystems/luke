# Quick Start Guide

Get the Insight Graph running in 5 minutes.

## Prerequisites

- Python 3.10+
- Discord bot token ([create one here](https://discord.com/developers/applications))
- OpenAI API key ([get one here](https://platform.openai.com/api-keys))

## Installation

```bash
# Clone the repo (if not already done)
cd insight-graph

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
```

## Configuration

Edit `.env` with your credentials:

```bash
# Discord
DISCORD_TOKEN=your_bot_token_here
DISCORD_GUILD_ID=your_server_id

# OpenAI
OPENAI_API_KEY=your_openai_key

# (Other settings have sensible defaults)
```

## Usage

### 1. Start Discord Ingestion

Ingest messages from your Discord community:

```bash
python -m insight_graph.ingest.discord_bot
```

Leave this running. It will:
- Listen to all channels the bot can see
- Auto-label messages (bugs, feature requests, etc.)
- Store embeddings in ChromaDB
- Build the knowledge graph

### 2. Chat with the Copilot

In another terminal, start the interactive chat:

```bash
python -m insight_graph.rag.chat
```

Try queries like:
- "What's blocking onboarding?"
- "Show me performance issues"
- "Who's affected by the camera bug?"

### 3. Generate Daily Brief

```bash
python -m insight_graph.briefs.daily
```

This will output a formatted brief you can paste into Discord/Slack.

### 4. Run Persona Simulations

Simulate how personas react to a proposed change:

```bash
python -m insight_graph.personas.agents "We're adding volumetric fog to the Swamp biome"
```

You'll get reactions from:
- Low-VRAM Explorer (performance-sensitive)
- Meta-Chaser (competitive player)

### 5. Generate Voice Readout

```bash
# First, save a brief to a file
python -m insight_graph.briefs.daily > daily_brief.txt

# Then generate audio
python -m insight_graph.briefs.voice daily_brief.txt
```

Audio files will be in `./data/voice/`.

## Example Developer Workflow

```bash
# Morning standup
python -m insight_graph.briefs.daily > standup.txt
cat standup.txt

# Investigate a specific issue
python -m insight_graph.rag.chat
> "Show me all FPS drops in the swamp biome"
> "Create an issue for these messages"

# Before making a change, simulate impact
python -m insight_graph.personas.agents "Reducing particle count in swamp by 30%"

# Review results, proceed with change
```

## Next Steps

- **Customize personas**: Edit `insight_graph/personas/profiles/*.yaml`
- **Add helpdesk integration**: Implement `insight_graph/ingest/helpdesk.py`
- **Set up cron jobs**: Automate daily briefs at 9 AM
- **Build dashboards**: Use the graph data to create visualizations

## Troubleshooting

**Bot not seeing messages?**
- Check bot permissions in Discord (needs "Read Messages", "Read Message History")
- Ensure bot is added to your server with correct OAuth2 scopes

**ChromaDB errors?**
- Delete `./data/chroma` and restart (will re-index)

**OpenAI rate limits?**
- Reduce embedding batch sizes
- Use `gpt-3.5-turbo` instead of `gpt-4` for testing

## Architecture

```
Discord → Ingest → Graph + Vector Store
                       ↓
                   RAG Retriever
                       ↓
                   Copilot Chat
                       ↓
                   Daily Briefs → Voice
```

For detailed architecture, see [README.md](../README.md).

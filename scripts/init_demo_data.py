#!/usr/bin/env python
"""
Initialize demo data for testing the Insight Graph.

Creates sample users, messages, issues, and personas to demonstrate functionality.
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

from insight_graph.core.graph import InsightGraph
from insight_graph.core.models import (
    CapabilityBand,
    Issue,
    IssueSeverity,
    IssueStatus,
    Message,
    MessageLabel,
    Persona,
    PlaystyleSignal,
    User,
)
from insight_graph.core.vector_store import VectorStore

load_dotenv()


def create_demo_data():
    """Create demo data for testing."""
    print("Initializing Insight Graph with demo data...")

    # Initialize graph and vector store
    graph_data_dir = Path(os.getenv("GRAPH_DATA_DIR", "./data/graph"))
    chroma_persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma")

    graph = InsightGraph(data_dir=graph_data_dir)

    # Check for OpenAI key
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        print("⚠️  OPENAI_API_KEY not set. Skipping vector store initialization.")
        print("   Set it in .env to enable semantic search.")
        vector_store = None
    else:
        vector_store = VectorStore(
            persist_dir=chroma_persist_dir,
            collection_name="insight_graph",
            openai_api_key=openai_key,
        )

    # Create demo users
    print("\n📝 Creating demo users...")

    users = [
        User(
            discord_id="user_001",
            discord_handle="Ravenwood",
            capability_bands={CapabilityBand.LOW_VRAM, CapabilityBand.MID_CPU, CapabilityBand.KB_MOUSE},
            playstyle_signals={PlaystyleSignal.EXPLORER, PlaystyleSignal.COMPLETIONIST},
            opted_in=True,
        ),
        User(
            discord_id="user_002",
            discord_handle="ShadowStrike",
            capability_bands={CapabilityBand.HIGH_VRAM, CapabilityBand.HIGH_CPU, CapabilityBand.KB_MOUSE},
            playstyle_signals={PlaystyleSignal.COMPETITIVE, PlaystyleSignal.HARDCORE},
            opted_in=True,
        ),
        User(
            discord_id="user_003",
            discord_handle="CasualGamer42",
            capability_bands={CapabilityBand.MID_VRAM, CapabilityBand.CONTROLLER},
            playstyle_signals={PlaystyleSignal.CASUAL, PlaystyleSignal.SOCIAL},
            opted_in=False,
        ),
    ]

    for user in users:
        graph.save_user(user)
        print(f"  ✓ Created user: {user.discord_handle}")

    # Create demo messages
    print("\n💬 Creating demo messages...")

    messages_data = [
        (
            users[0],
            "FPS drops from 60 to 25 when entering Swamp biome with torch equipped. GPU: GTX 1050 Ti (4GB VRAM).",
            {MessageLabel.BUG_REPORT, MessageLabel.PERFORMANCE},
        ),
        (
            users[0],
            "Game crashes after ~45min in Forest area. Error: Out of memory. Can we get texture quality options?",
            {MessageLabel.BUG_REPORT, MessageLabel.CRASH},
        ),
        (
            users[1],
            "Hit registration is still broken in PvP. 23% of headshots don't count. This is unplayable.",
            {MessageLabel.BUG_REPORT, MessageLabel.COMPLAINT},
        ),
        (
            users[1],
            "New balance patch nerfed Spell X without mentioning it in notes. DPS is down 15%. Not transparent.",
            {MessageLabel.COMPLAINT},
        ),
        (
            users[2],
            "Love the new cave system! Great job on the lighting.",
            {MessageLabel.PRAISE},
        ),
        (
            users[0],
            "Tutorial camera at step 2 is really janky. Gets stuck looking at the sky.",
            {MessageLabel.BUG_REPORT, MessageLabel.UX_CONFUSION},
        ),
    ]

    messages = []
    for user, text, labels in messages_data:
        msg = Message(
            user_id=user.id,
            discord_message_id=f"msg_{uuid4().hex[:8]}",
            channel_id="channel_general",
            text=text,
            cleaned_text=text,
            labels=labels,
            created_at=datetime.utcnow() - timedelta(hours=len(messages)),
        )
        graph.save_message(msg)
        messages.append(msg)

        # Add to vector store if available
        if vector_store:
            vector_store.add_message(
                message_id=msg.id,
                text=msg.cleaned_text,
                metadata={
                    "user_id": str(user.id),
                    "channel_id": msg.channel_id,
                    "labels": [label.value for label in msg.labels],
                },
            )

        print(f"  ✓ Created message: {text[:60]}...")

    # Create demo issues
    print("\n🐛 Creating demo issues...")

    issues = [
        Issue(
            title="FPS drops in Swamp biome",
            description="Multiple reports of FPS dropping from 60 to 25 when entering Swamp with torch",
            severity=IssueSeverity.HIGH,
            status=IssueStatus.TRIAGED,
            linked_message_ids=[messages[0].id],
            tags={"performance", "swamp", "particles"},
        ),
        Issue(
            title="Out of memory crashes after 45min",
            description="Players with low VRAM experiencing crashes in Forest biome",
            severity=IssueSeverity.CRITICAL,
            status=IssueStatus.NEW,
            linked_message_ids=[messages[1].id],
            tags={"crash", "memory", "forest"},
        ),
        Issue(
            title="Tutorial camera stuck at step 2",
            description="Camera gets stuck looking at sky during tutorial step 2",
            severity=IssueSeverity.MEDIUM,
            status=IssueStatus.NEW,
            linked_message_ids=[messages[5].id],
            tags={"tutorial", "camera", "onboarding"},
        ),
    ]

    for issue in issues:
        graph.save_issue(issue)
        print(f"  ✓ Created issue: {issue.title}")

    # Create demo personas
    print("\n👥 Creating demo personas...")

    personas = [
        Persona(
            name="Low-VRAM Explorer",
            description="Performance-sensitive player who values exploration over graphics",
            pain_points=["performance.swamp", "crashes.memory", "tutorial.camera"],
            goals=["stable_60fps", "explore_all_biomes", "low_cognitive_load"],
            canonical_examples=[messages[0].id, messages[1].id],
            prompt_profile_path="./insight_graph/personas/profiles/low-vram-explorer.yaml",
        ),
        Persona(
            name="Meta-Chaser Min/Maxer",
            description="Competitive player seeking optimal builds and meta mastery",
            pain_points=["balance.stealth_nerfs", "bugs.hit_registration", "mechanics.inconsistency"],
            goals=["top_1_percent", "master_meta", "maximize_efficiency"],
            canonical_examples=[messages[2].id, messages[3].id],
            prompt_profile_path="./insight_graph/personas/profiles/meta-chaser.yaml",
        ),
    ]

    for persona in personas:
        graph.save_persona(persona)
        print(f"  ✓ Created persona: {persona.name}")

    print("\n✅ Demo data created successfully!")
    print(f"\n📊 Summary:")
    print(f"   - Users: {len(users)}")
    print(f"   - Messages: {len(messages)}")
    print(f"   - Issues: {len(issues)}")
    print(f"   - Personas: {len(personas)}")
    print(f"\n💾 Data stored in: {graph_data_dir}")
    if vector_store:
        print(f"🔍 Vector store: {chroma_persist_dir}")
    print("\n🚀 Ready to test! Try:")
    print("   python -m insight_graph.rag.chat")
    print("   python -m insight_graph.briefs.daily")


if __name__ == "__main__":
    create_demo_data()

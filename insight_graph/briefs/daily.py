"""
Daily brief generator.

Produces concise daily standup briefs with:
- Top issues (new, escalating, blocking)
- Hot threads (high activity, sentiment shifts)
- Persona shifts (new pain points, coverage changes)
- Quick wins (low-hanging fruit issues)
"""

import os
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from openai import OpenAI

from ..core.graph import InsightGraph
from ..core.models import IssueStatus
from ..core.vector_store import VectorStore


class DailyBriefGenerator:
    """Generates daily briefs for dev teams."""

    def __init__(self, graph: InsightGraph, vector_store: VectorStore):
        self.graph = graph
        self.vector_store = vector_store
        self.openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def generate(
        self,
        lookback_hours: int = 24,
        format: str = "discord",
    ) -> dict[str, Any]:
        """
        Generate a daily brief.

        Args:
            lookback_hours: How many hours to look back
            format: Output format ('discord', 'slack', or 'text')

        Returns:
            Brief dict with formatted content
        """
        since = datetime.utcnow() - timedelta(hours=lookback_hours)

        # Gather data
        data = {
            "new_messages": self._get_new_messages(since),
            "new_issues": self._get_new_issues(since),
            "updated_issues": self._get_updated_issues(since),
            "hot_topics": self._get_hot_topics(since),
            "sentiment": self._analyze_sentiment(since),
            "personas": self._get_persona_summary(),
        }

        # Generate summary with LLM
        summary = self._generate_summary(data, lookback_hours)

        # Format for target platform
        if format == "discord":
            formatted = self._format_discord(summary, data)
        elif format == "slack":
            formatted = self._format_slack(summary, data)
        else:
            formatted = self._format_text(summary, data)

        return {
            "generated_at": datetime.utcnow().isoformat(),
            "lookback_hours": lookback_hours,
            "data": data,
            "summary": summary,
            "formatted": formatted,
        }

    def _get_new_messages(self, since: datetime) -> list:
        """Get new messages since timestamp."""
        all_messages = self.graph.list_messages(limit=1000)
        return [msg for msg in all_messages if msg.created_at >= since]

    def _get_new_issues(self, since: datetime) -> list:
        """Get new issues since timestamp."""
        all_issues = self.graph.list_issues()
        return [issue for issue in all_issues if issue.created_at >= since]

    def _get_updated_issues(self, since: datetime) -> list:
        """Get recently updated issues."""
        all_issues = self.graph.list_issues()
        return [
            issue
            for issue in all_issues
            if issue.updated_at >= since and issue.created_at < since
        ]

    def _get_hot_topics(self, since: datetime) -> list[tuple[str, int]]:
        """Extract hot topics from recent messages."""
        messages = self._get_new_messages(since)

        # Count topic tags
        topic_counter = Counter()
        for msg in messages:
            topic_counter.update(msg.topic_tags)

        return topic_counter.most_common(5)

    def _analyze_sentiment(self, since: datetime) -> dict:
        """Analyze sentiment trends."""
        messages = self._get_new_messages(since)

        sentiments = [msg.sentiment_score for msg in messages if msg.sentiment_score is not None]

        if not sentiments:
            return {"avg": 0.0, "trend": "neutral"}

        avg = sum(sentiments) / len(sentiments)

        # Classify trend
        if avg > 0.3:
            trend = "positive"
        elif avg < -0.3:
            trend = "negative"
        else:
            trend = "neutral"

        return {"avg": avg, "trend": trend, "count": len(sentiments)}

    def _get_persona_summary(self) -> dict:
        """Get summary of persona coverage and activity."""
        personas = self.graph.list_personas()

        return {
            "count": len(personas),
            "names": [p.name for p in personas],
        }

    def _generate_summary(self, data: dict, lookback_hours: int) -> str:
        """Generate natural language summary with LLM."""
        # Build prompt
        prompt = f"""Generate a concise daily dev brief for a game development team.

Data from the last {lookback_hours} hours:

**New Messages**: {len(data['new_messages'])}
**New Issues**: {len(data['new_issues'])}
**Updated Issues**: {len(data['updated_issues'])}

**Hot Topics**:
{self._format_hot_topics(data['hot_topics'])}

**New Issues Summary**:
{self._format_issues_summary(data['new_issues'])}

**Sentiment**: {data['sentiment']['trend']} (avg: {data['sentiment']['avg']:.2f})

**Active Personas**: {', '.join(data['personas']['names'])}

Generate a brief 3-4 sentence summary highlighting:
1. Top blocker or trend
2. Sentiment/community mood
3. Quick win opportunities

Keep it actionable and developer-focused."""

        response = self.openai.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {
                    "role": "system",
                    "content": "You are a dev brief assistant. Be concise, actionable, and highlight what matters.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=300,
        )

        return response.choices[0].message.content

    def _format_hot_topics(self, topics: list[tuple[str, int]]) -> str:
        """Format hot topics list."""
        if not topics:
            return "- None"
        return "\n".join([f"- {topic}: {count} mentions" for topic, count in topics])

    def _format_issues_summary(self, issues: list) -> str:
        """Format issues summary."""
        if not issues:
            return "- No new issues"

        lines = []
        for issue in issues[:5]:  # Top 5
            lines.append(f"- [{issue.severity.value}] {issue.title}")

        return "\n".join(lines)

    def _format_discord(self, summary: str, data: dict) -> str:
        """Format for Discord with embeds."""
        # Discord markdown
        output = f"""**📊 Daily Dev Brief** — {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

{summary}

**📈 Stats**
• Messages: {len(data['new_messages'])}
• New Issues: {len(data['new_issues'])}
• Updated Issues: {len(data['updated_issues'])}
• Sentiment: {data['sentiment']['trend']} ({data['sentiment']['avg']:+.2f})

**🔥 Hot Topics**
{self._format_hot_topics(data['hot_topics'])}

**🐛 New Issues**
{self._format_issues_summary(data['new_issues'])}

**👥 Active Personas**
{', '.join(data['personas']['names'])}

---
_Use `/copilot` to ask questions or `/brief weekly` for a full rollup._
"""
        return output

    def _format_slack(self, summary: str, data: dict) -> str:
        """Format for Slack."""
        # Similar to Discord but with Slack-specific formatting
        output = f"""*📊 Daily Dev Brief* — {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

{summary}

*📈 Stats*
• Messages: {len(data['new_messages'])}
• New Issues: {len(data['new_issues'])}
• Updated Issues: {len(data['updated_issues'])}
• Sentiment: {data['sentiment']['trend']} ({data['sentiment']['avg']:+.2f})

*🔥 Hot Topics*
{self._format_hot_topics(data['hot_topics'])}

*🐛 New Issues*
{self._format_issues_summary(data['new_issues'])}

*👥 Active Personas*
{', '.join(data['personas']['names'])}

---
_Ask the copilot for details or run `/brief weekly` for a full rollup._
"""
        return output

    def _format_text(self, summary: str, data: dict) -> str:
        """Format as plain text."""
        output = f"""DAILY DEV BRIEF — {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

{summary}

STATS
- Messages: {len(data['new_messages'])}
- New Issues: {len(data['new_issues'])}
- Updated Issues: {len(data['updated_issues'])}
- Sentiment: {data['sentiment']['trend']} ({data['sentiment']['avg']:+.2f})

HOT TOPICS
{self._format_hot_topics(data['hot_topics'])}

NEW ISSUES
{self._format_issues_summary(data['new_issues'])}

ACTIVE PERSONAS
{', '.join(data['personas']['names'])}
"""
        return output


# CLI
def main():
    """Generate and print a daily brief."""
    import sys

    from dotenv import load_dotenv

    load_dotenv()

    # Parse args
    lookback_hours = int(sys.argv[1]) if len(sys.argv) > 1 else 24
    format = sys.argv[2] if len(sys.argv) > 2 else "discord"

    # Initialize
    graph_data_dir = Path(os.getenv("GRAPH_DATA_DIR", "./data/graph"))
    chroma_persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma")

    graph = InsightGraph(data_dir=graph_data_dir)
    vector_store = VectorStore(
        persist_dir=chroma_persist_dir,
        collection_name="insight_graph",
        openai_api_key=os.getenv("OPENAI_API_KEY"),
    )

    # Generate brief
    generator = DailyBriefGenerator(graph, vector_store)
    brief = generator.generate(lookback_hours=lookback_hours, format=format)

    # Print
    print(brief["formatted"])


if __name__ == "__main__":
    main()

"""
Sentiment analysis utilities.

Analyzes sentiment and frustration levels in messages.
"""

from typing import Optional

from ..core.graph import InsightGraph
from ..core.models import Message


class SentimentAnalyzer:
    """
    Analyze sentiment and frustration in messages.

    Uses simple heuristics initially; can be upgraded to ML models.
    """

    def __init__(self, graph: InsightGraph):
        self.graph = graph

        # Sentiment lexicons (simplified)
        self.positive_words = {
            "love",
            "great",
            "awesome",
            "amazing",
            "excellent",
            "fantastic",
            "perfect",
            "wonderful",
            "thank",
            "appreciate",
            "enjoy",
            "fun",
            "beautiful",
        }

        self.negative_words = {
            "hate",
            "terrible",
            "awful",
            "broken",
            "bug",
            "crash",
            "lag",
            "slow",
            "annoying",
            "frustrat",
            "unplayable",
            "bad",
            "worst",
            "garbage",
        }

        self.frustration_indicators = {
            "frustrat",
            "annoying",
            "hate",
            "rage",
            "unplayable",
            "broken",
            "still broken",
            "not fixed",
            "waste",
            "refund",
        }

    def analyze_message(self, message: Message) -> dict[str, float]:
        """
        Analyze sentiment and frustration in a message.

        Args:
            message: Message to analyze

        Returns:
            Dict with sentiment_score (-1 to 1) and frustration_score (0 to 1)
        """
        text = (message.cleaned_text or message.text).lower()
        words = text.split()

        # Count sentiment words
        pos_count = sum(1 for word in words if any(pw in word for pw in self.positive_words))
        neg_count = sum(1 for word in words if any(nw in word for nw in self.negative_words))

        # Sentiment score
        total = pos_count + neg_count
        if total == 0:
            sentiment_score = 0.0
        else:
            sentiment_score = (pos_count - neg_count) / total

        # Frustration score
        frustration_count = sum(
            1 for word in words if any(fw in word for fw in self.frustration_indicators)
        )

        # Boost frustration if there are exclamation marks or caps
        if "!!!" in text or text.isupper():
            frustration_count += 2

        frustration_score = min(frustration_count / 5.0, 1.0)  # Normalize to 0-1

        return {
            "sentiment_score": sentiment_score,
            "frustration_score": frustration_score,
        }

    def analyze_and_update(self, message: Message) -> Message:
        """
        Analyze message and update its sentiment fields.

        Args:
            message: Message to analyze

        Returns:
            Updated message
        """
        scores = self.analyze_message(message)
        message.sentiment_score = scores["sentiment_score"]
        message.frustration_score = scores["frustration_score"]

        self.graph.save_message(message)

        return message

    def batch_analyze(self, messages: list[Message]) -> None:
        """
        Analyze sentiment for a batch of messages.

        Args:
            messages: Messages to analyze
        """
        for msg in messages:
            self.analyze_and_update(msg)

    def get_sentiment_trend(self, messages: list[Message]) -> dict:
        """
        Calculate sentiment trend over time.

        Args:
            messages: Messages to analyze (should be time-ordered)

        Returns:
            Trend statistics
        """
        if not messages:
            return {"avg": 0.0, "trend": "neutral", "count": 0}

        sentiments = []
        frustrations = []

        for msg in messages:
            if msg.sentiment_score is not None:
                sentiments.append(msg.sentiment_score)
            if msg.frustration_score is not None:
                frustrations.append(msg.frustration_score)

        if not sentiments:
            return {"avg": 0.0, "trend": "neutral", "count": 0}

        avg_sentiment = sum(sentiments) / len(sentiments)
        avg_frustration = sum(frustrations) / len(frustrations) if frustrations else 0.0

        # Determine trend
        if avg_sentiment > 0.3:
            trend = "positive"
        elif avg_sentiment < -0.3 or avg_frustration > 0.5:
            trend = "negative"
        else:
            trend = "neutral"

        return {
            "avg_sentiment": avg_sentiment,
            "avg_frustration": avg_frustration,
            "trend": trend,
            "count": len(sentiments),
        }


# CLI for testing
def main():
    """Test sentiment analysis."""
    import os
    from pathlib import Path

    from dotenv import load_dotenv

    load_dotenv()

    graph_data_dir = Path(os.getenv("GRAPH_DATA_DIR", "./data/graph"))
    graph = InsightGraph(data_dir=graph_data_dir)

    analyzer = SentimentAnalyzer(graph)

    # Analyze all messages
    messages = graph.list_messages(limit=100)
    print(f"Analyzing {len(messages)} messages...\n")

    analyzer.batch_analyze(messages)

    # Show trend
    trend = analyzer.get_sentiment_trend(messages)
    print(f"Sentiment Trend: {trend['trend']}")
    print(f"Average Sentiment: {trend['avg_sentiment']:.2f}")
    print(f"Average Frustration: {trend['avg_frustration']:.2f}")
    print(f"Messages analyzed: {trend['count']}")

    # Show top positive and negative
    scored_messages = [msg for msg in messages if msg.sentiment_score is not None]
    scored_messages.sort(key=lambda m: m.sentiment_score or 0, reverse=True)

    print("\n=== Most Positive Messages ===")
    for msg in scored_messages[:3]:
        print(f"[{msg.sentiment_score:+.2f}] {msg.text[:80]}...")

    print("\n=== Most Negative Messages ===")
    for msg in scored_messages[-3:]:
        print(f"[{msg.sentiment_score:+.2f}] {msg.text[:80]}...")


if __name__ == "__main__":
    main()

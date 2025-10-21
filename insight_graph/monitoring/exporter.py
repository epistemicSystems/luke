"""
Prometheus metrics exporter.

Standalone server that exports Insight Graph metrics for Prometheus.
"""

import os
import time
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

from ..core.graph import InsightGraph
from ..core.vector_store import VectorStore
from ..understand.sentiment import SentimentAnalyzer
from .metrics import get_metrics

load_dotenv()


def export_metrics():
    """Export metrics from Insight Graph to Prometheus."""
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

    analyzer = SentimentAnalyzer(graph)
    metrics = get_metrics()

    # Start metrics server
    port = int(os.getenv("PROMETHEUS_PORT", "9090"))
    metrics.start_server(port)

    print(f"Metrics exporter started on port {port}")
    print("Updating metrics every 60 seconds...")

    # Update loop
    while True:
        try:
            # Update graph metrics
            metrics.update_graph_metrics(graph)

            # Update sentiment metrics (last 24 hours)
            since = datetime.utcnow() - timedelta(hours=24)
            recent_messages = [
                m for m in graph.list_messages(limit=10000)
                if m.created_at >= since
            ]
            metrics.update_sentiment_metrics(analyzer, recent_messages)

            print(f"[{datetime.utcnow().isoformat()}] Metrics updated")

        except Exception as e:
            print(f"Error updating metrics: {e}")

        time.sleep(60)


if __name__ == "__main__":
    export_metrics()

"""
Prometheus metrics for monitoring.

Exposes key metrics for Prometheus scraping.
"""

from prometheus_client import Counter, Gauge, Histogram, start_http_server


class InsightGraphMetrics:
    """
    Prometheus metrics for Insight Graph.

    Usage:
        metrics = InsightGraphMetrics()
        metrics.messages_ingested.inc()
        metrics.rag_query_duration.observe(0.5)
        metrics.start_server(port=9090)
    """

    def __init__(self):
        # Ingestion metrics
        self.messages_ingested = Counter(
            "insight_graph_messages_ingested_total",
            "Total messages ingested from Discord",
        )

        self.messages_failed = Counter(
            "insight_graph_messages_failed_total",
            "Total messages that failed to ingest",
        )

        self.embeddings_generated = Counter(
            "insight_graph_embeddings_generated_total",
            "Total embeddings generated",
        )

        # RAG metrics
        self.rag_queries = Counter(
            "insight_graph_rag_queries_total",
            "Total RAG queries",
        )

        self.rag_query_duration = Histogram(
            "insight_graph_rag_query_duration_seconds",
            "RAG query duration in seconds",
        )

        # Issue metrics
        self.issues_created = Counter(
            "insight_graph_issues_created_total",
            "Total issues created",
            ["severity"],
        )

        self.issues_resolved = Counter(
            "insight_graph_issues_resolved_total",
            "Total issues resolved",
        )

        # Graph metrics
        self.total_users = Gauge(
            "insight_graph_total_users",
            "Total number of users in graph",
        )

        self.total_messages = Gauge(
            "insight_graph_total_messages",
            "Total number of messages in graph",
        )

        self.total_issues = Gauge(
            "insight_graph_total_issues",
            "Total number of issues in graph",
        )

        self.open_issues = Gauge(
            "insight_graph_open_issues",
            "Number of open issues",
        )

        # Sentiment metrics
        self.avg_sentiment = Gauge(
            "insight_graph_avg_sentiment",
            "Average community sentiment (-1 to 1)",
        )

        self.avg_frustration = Gauge(
            "insight_graph_avg_frustration",
            "Average community frustration (0 to 1)",
        )

        # Persona metrics
        self.persona_simulations = Counter(
            "insight_graph_persona_simulations_total",
            "Total persona simulations run",
        )

        # API metrics
        self.api_requests = Counter(
            "insight_graph_api_requests_total",
            "Total API requests",
            ["endpoint", "method"],
        )

        self.api_errors = Counter(
            "insight_graph_api_errors_total",
            "Total API errors",
            ["endpoint", "status_code"],
        )

    def update_graph_metrics(self, graph):
        """
        Update graph-related metrics from the Insight Graph.

        Args:
            graph: InsightGraph instance
        """
        users = graph.list_users()
        messages = graph.list_messages(limit=100000)
        issues = graph.list_issues()

        self.total_users.set(len(users))
        self.total_messages.set(len(messages))
        self.total_issues.set(len(issues))

        open_issues = [
            i for i in issues if i.status.value in ["new", "triaged", "in_progress"]
        ]
        self.open_issues.set(len(open_issues))

    def update_sentiment_metrics(self, analyzer, messages):
        """
        Update sentiment metrics.

        Args:
            analyzer: SentimentAnalyzer instance
            messages: Recent messages to analyze
        """
        trend = analyzer.get_sentiment_trend(messages)

        self.avg_sentiment.set(trend.get("avg_sentiment", 0.0))
        self.avg_frustration.set(trend.get("avg_frustration", 0.0))

    def start_server(self, port: int = 9090):
        """
        Start Prometheus metrics server.

        Args:
            port: Port to listen on
        """
        start_http_server(port)
        print(f"Prometheus metrics server started on port {port}")


# Global instance
_metrics = None


def get_metrics() -> InsightGraphMetrics:
    """Get or create global metrics instance."""
    global _metrics
    if _metrics is None:
        _metrics = InsightGraphMetrics()
    return _metrics

"""
Dual-index retriever for RAG.

Combines dense vector search with symbolic graph queries.
"""

from typing import Any, Optional
from uuid import UUID

from ..core.graph import InsightGraph
from ..core.models import Issue, Message, Persona
from ..core.vector_store import VectorStore


class DualIndexRetriever:
    """
    Retrieves context from both vector store and graph.

    Blends:
    - Top-k semantically similar messages
    - Linked issues, builds, personas
    - Recent timeline events
    """

    def __init__(self, graph: InsightGraph, vector_store: VectorStore, top_k: int = 10):
        self.graph = graph
        self.vector_store = vector_store
        self.top_k = top_k

    def retrieve(
        self,
        query: str,
        include_issues: bool = True,
        include_personas: bool = True,
        filter_channel: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Retrieve relevant context for a query.

        Args:
            query: User query
            include_issues: Whether to include linked issues
            include_personas: Whether to include relevant personas
            filter_channel: Optional channel filter

        Returns:
            Context dict with messages, issues, personas, etc.
        """
        # 1. Semantic search over messages
        filter_metadata = {"channel_id": filter_channel} if filter_channel else None
        similar_messages = self.vector_store.search(
            query=query,
            top_k=self.top_k,
            filter_metadata=filter_metadata,
        )

        # Hydrate full message objects
        messages = []
        for result in similar_messages:
            msg = self.graph.get_message(UUID(result["message_id"]))
            if msg:
                messages.append(
                    {
                        "message": msg,
                        "similarity": 1.0 - result["distance"],
                    }
                )

        # 2. Get linked issues
        issues = []
        if include_issues:
            issue_ids = set()
            for result in messages:
                msg = result["message"]
                issue_ids.update(msg.linked_issue_ids)

            for issue_id in issue_ids:
                issue = self.graph.get_issue(issue_id)
                if issue:
                    issues.append(issue)

        # 3. Get relevant personas
        personas = []
        if include_personas:
            # For now, just get all personas (could filter by query later)
            personas = self.graph.list_personas()

        # 4. Compile context
        context = {
            "messages": messages,
            "issues": issues,
            "personas": personas,
            "query": query,
        }

        return context

    def retrieve_for_issue(self, issue_id: UUID) -> dict[str, Any]:
        """
        Retrieve full context for an issue.

        Args:
            issue_id: Issue UUID

        Returns:
            Context dict with issue, linked messages/threads, similar issues
        """
        issue = self.graph.get_issue(issue_id)
        if not issue:
            return {}

        # Get linked messages
        messages = [
            self.graph.get_message(msg_id)
            for msg_id in issue.linked_message_ids
            if self.graph.get_message(msg_id)
        ]

        # Get linked threads
        threads = [
            self.graph.get_thread(thread_id)
            for thread_id in issue.linked_thread_ids
            if self.graph.get_thread(thread_id)
        ]

        # Find similar issues via title/description
        similar = self.vector_store.search(
            query=f"{issue.title} {issue.description}",
            top_k=5,
        )

        context = {
            "issue": issue,
            "messages": messages,
            "threads": threads,
            "similar_issues": similar,
        }

        return context

    def retrieve_for_persona(self, persona_id: UUID) -> dict[str, Any]:
        """
        Retrieve full context for a persona.

        Args:
            persona_id: Persona UUID

        Returns:
            Context dict with persona, canonical examples, affected issues
        """
        persona = self.graph.get_persona(persona_id)
        if not persona:
            return {}

        # Get canonical example messages
        examples = [
            self.graph.get_message(msg_id)
            for msg_id in persona.canonical_examples
            if self.graph.get_message(msg_id)
        ]

        # Get affected issues
        issues = [
            issue
            for issue in self.graph.list_issues()
            if persona.id in issue.affected_persona_ids
        ]

        context = {
            "persona": persona,
            "examples": examples,
            "affected_issues": issues,
        }

        return context

"""
Data normalization and deduplication utilities.

Handles cleanup, near-duplicate detection, and entity resolution.
"""

import hashlib
from typing import Optional
from uuid import UUID

from ..core.graph import InsightGraph
from ..core.models import Issue, Message
from ..core.vector_store import VectorStore


class Normalizer:
    """Handles data normalization and deduplication."""

    def __init__(self, graph: InsightGraph, vector_store: VectorStore):
        self.graph = graph
        self.vector_store = vector_store

    def compute_content_hash(self, text: str) -> str:
        """
        Compute a hash of normalized content for exact duplicate detection.

        Args:
            text: Input text

        Returns:
            SHA256 hash
        """
        # Normalize: lowercase, strip whitespace, remove punctuation
        normalized = "".join(c.lower() for c in text if c.isalnum() or c.isspace())
        normalized = " ".join(normalized.split())

        return hashlib.sha256(normalized.encode()).hexdigest()

    def find_near_duplicate_messages(
        self, message_id: UUID, similarity_threshold: float = 0.95
    ) -> list[dict]:
        """
        Find near-duplicate messages using semantic similarity.

        Args:
            message_id: Message to check
            similarity_threshold: Cosine similarity threshold (0.0 to 1.0)

        Returns:
            List of similar messages
        """
        message = self.graph.get_message(message_id)
        if not message or not message.cleaned_text:
            return []

        # Search for similar messages
        results = self.vector_store.search(
            query=message.cleaned_text,
            top_k=10,
        )

        # Filter by similarity threshold
        # Note: ChromaDB returns distances, not similarities
        # Lower distance = higher similarity
        near_duplicates = []
        for result in results:
            # Skip self
            if result["message_id"] == str(message_id):
                continue

            # Convert distance to similarity (approximate)
            # For cosine distance: similarity ≈ 1 - distance
            similarity = 1.0 - result["distance"]

            if similarity >= similarity_threshold:
                near_duplicates.append(
                    {
                        "message_id": result["message_id"],
                        "similarity": similarity,
                        "text": result["text"],
                    }
                )

        return near_duplicates

    def find_duplicate_issues(self, issue_id: UUID) -> list[UUID]:
        """
        Find potential duplicate issues.

        Uses a combination of:
        - Exact title match
        - Semantic similarity of descriptions
        - Overlap in linked messages/threads

        Args:
            issue_id: Issue to check

        Returns:
            List of potentially duplicate issue IDs
        """
        issue = self.graph.get_issue(issue_id)
        if not issue:
            return []

        duplicates = []

        # Check all other issues
        for other_issue in self.graph.list_issues():
            if other_issue.id == issue_id:
                continue

            # Exact title match
            if other_issue.title.lower() == issue.title.lower():
                duplicates.append(other_issue.id)
                continue

            # Check linked threads overlap
            thread_overlap = set(issue.linked_thread_ids) & set(other_issue.linked_thread_ids)
            if len(thread_overlap) > 0:
                duplicates.append(other_issue.id)

        return duplicates

    def merge_issues(self, primary_id: UUID, duplicate_ids: list[UUID]) -> None:
        """
        Merge duplicate issues into a primary issue.

        Args:
            primary_id: Primary issue to keep
            duplicate_ids: Issues to merge into primary
        """
        primary = self.graph.get_issue(primary_id)
        if not primary:
            raise ValueError(f"Primary issue {primary_id} not found")

        # Merge data from duplicates
        for dup_id in duplicate_ids:
            duplicate = self.graph.get_issue(dup_id)
            if not duplicate:
                continue

            # Merge threads
            primary.linked_thread_ids.extend(duplicate.linked_thread_ids)
            primary.linked_thread_ids = list(set(primary.linked_thread_ids))  # Dedupe

            # Merge messages
            primary.linked_message_ids.extend(duplicate.linked_message_ids)
            primary.linked_message_ids = list(set(primary.linked_message_ids))

            # Merge tags
            primary.tags.update(duplicate.tags)

            # Mark duplicate
            duplicate.status = "duplicate"
            duplicate.duplicate_of = primary_id
            self.graph.save_issue(duplicate)

        # Save updated primary
        self.graph.save_issue(primary)

        # Log the merge
        self.graph.log_change(
            entity_type="issue",
            entity_id=primary_id,
            action="merge",
            details={"merged_from": [str(d) for d in duplicate_ids]},
        )

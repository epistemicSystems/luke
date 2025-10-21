"""
Batch processing utilities for performance optimization.

Handles batch embedding generation, bulk ingestion, etc.
"""

from typing import Any, Callable, Iterable, List, TypeVar

T = TypeVar("T")
R = TypeVar("R")


def batch_process(
    items: Iterable[T],
    process_func: Callable[[List[T]], List[R]],
    batch_size: int = 100,
) -> List[R]:
    """
    Process items in batches.

    Args:
        items: Items to process
        process_func: Function that takes a list and returns results
        batch_size: Batch size

    Returns:
        All results
    """
    results = []
    batch = []

    for item in items:
        batch.append(item)

        if len(batch) >= batch_size:
            results.extend(process_func(batch))
            batch = []

    # Process remaining
    if batch:
        results.extend(process_func(batch))

    return results


class BatchEmbedder:
    """
    Batch embedding generator with caching.

    Usage:
        embedder = BatchEmbedder(vector_store)
        embeddings = embedder.embed_texts(texts)
    """

    def __init__(self, vector_store, batch_size: int = 100):
        """
        Initialize batch embedder.

        Args:
            vector_store: VectorStore instance
            batch_size: Batch size for API calls
        """
        self.vector_store = vector_store
        self.batch_size = batch_size

    def embed_texts(self, texts: List[str]) -> List[list[float]]:
        """
        Generate embeddings for texts in batches.

        Args:
            texts: List of text strings

        Returns:
            List of embedding vectors
        """
        from ..utils.cache import get_embedding_cache

        cache = get_embedding_cache()
        embeddings = []

        # Check cache first
        uncached_texts = []
        uncached_indices = []

        for i, text in enumerate(texts):
            cached = cache.get(text)
            if cached:
                embeddings.append(cached)
            else:
                uncached_texts.append(text)
                uncached_indices.append(i)
                embeddings.append(None)  # Placeholder

        # Batch generate uncached
        if uncached_texts:

            def generate_batch(batch: List[str]) -> List[list[float]]:
                return [self.vector_store.embed_text(text) for text in batch]

            new_embeddings = batch_process(
                uncached_texts, generate_batch, self.batch_size
            )

            # Cache and insert
            for idx, text, embedding in zip(
                uncached_indices, uncached_texts, new_embeddings
            ):
                cache.set(text, embedding)
                embeddings[idx] = embedding

        return embeddings


class BulkMessageIngestor:
    """
    Bulk message ingestion with batching.

    Usage:
        ingestor = BulkMessageIngestor(graph, vector_store)
        ingestor.ingest_messages(messages)
    """

    def __init__(self, graph, vector_store, batch_size: int = 100):
        """
        Initialize bulk ingestor.

        Args:
            graph: InsightGraph instance
            vector_store: VectorStore instance
            batch_size: Batch size
        """
        self.graph = graph
        self.vector_store = vector_store
        self.batch_size = batch_size
        self.embedder = BatchEmbedder(vector_store, batch_size)

    def ingest_messages(self, messages: List[Any]) -> List[str]:
        """
        Ingest messages in bulk.

        Args:
            messages: List of Message objects

        Returns:
            List of message IDs
        """
        # Extract texts
        texts = [msg.cleaned_text or msg.text for msg in messages]

        # Generate embeddings in batch
        embeddings = self.embedder.embed_texts(texts)

        # Save to graph and vector store
        message_ids = []

        for msg, embedding in zip(messages, embeddings):
            # Save to graph
            self.graph.save_message(msg)

            # Add to vector store
            metadata = {
                "user_id": str(msg.user_id),
                "channel_id": msg.channel_id,
                "labels": [label.value for label in msg.labels],
            }

            embedding_id = self.vector_store.add_message(
                message_id=msg.id,
                text=msg.cleaned_text or msg.text,
                metadata=metadata,
                embedding=embedding,  # Use pre-generated
            )

            msg.embedding_id = embedding_id
            self.graph.save_message(msg)

            message_ids.append(str(msg.id))

        return message_ids

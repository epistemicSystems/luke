"""
Vector store for embeddings and semantic search.

Uses ChromaDB for persistent vector storage with metadata filtering.
"""

from typing import Any, Optional
from uuid import UUID

import chromadb
from chromadb.config import Settings
from openai import OpenAI


class VectorStore:
    """
    Embedding storage and retrieval using ChromaDB.

    Stores message embeddings with rich metadata for filtering.
    """

    def __init__(self, persist_dir: str, collection_name: str, openai_api_key: str):
        """
        Initialize the vector store.

        Args:
            persist_dir: Directory for ChromaDB persistence
            collection_name: Name of the collection
            openai_api_key: OpenAI API key for embeddings
        """
        self.client = chromadb.Client(
            Settings(
                persist_directory=persist_dir,
                anonymized_telemetry=False,
            )
        )

        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        self.openai = OpenAI(api_key=openai_api_key)
        self.embedding_model = "text-embedding-3-large"

    def embed_text(self, text: str) -> list[float]:
        """
        Generate embedding for text using OpenAI.

        Args:
            text: Input text

        Returns:
            Embedding vector
        """
        response = self.openai.embeddings.create(input=text, model=self.embedding_model)
        return response.data[0].embedding

    def add_message(
        self,
        message_id: UUID,
        text: str,
        metadata: dict[str, Any],
        embedding: Optional[list[float]] = None,
    ) -> str:
        """
        Add a message to the vector store.

        Args:
            message_id: Message UUID
            text: Message text content
            metadata: Metadata dict (channel_id, user_id, labels, etc.)
            embedding: Pre-computed embedding (optional, will compute if None)

        Returns:
            Embedding ID
        """
        if embedding is None:
            embedding = self.embed_text(text)

        embedding_id = f"msg_{message_id}"

        self.collection.add(
            ids=[embedding_id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata],
        )

        return embedding_id

    def search(
        self,
        query: str,
        top_k: int = 10,
        filter_metadata: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        """
        Semantic search over messages.

        Args:
            query: Search query
            top_k: Number of results to return
            filter_metadata: Optional metadata filters

        Returns:
            List of results with message IDs, text, metadata, and distances
        """
        query_embedding = self.embed_text(query)

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filter_metadata,
        )

        # Format results
        formatted = []
        for i, doc_id in enumerate(results["ids"][0]):
            formatted.append(
                {
                    "id": doc_id,
                    "message_id": doc_id.replace("msg_", ""),
                    "text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i],
                }
            )

        return formatted

    def delete_message(self, message_id: UUID) -> None:
        """
        Delete a message from the vector store.

        Args:
            message_id: Message UUID
        """
        embedding_id = f"msg_{message_id}"
        self.collection.delete(ids=[embedding_id])

    def get_stats(self) -> dict[str, Any]:
        """Get collection statistics."""
        return {
            "count": self.collection.count(),
            "name": self.collection.name,
        }

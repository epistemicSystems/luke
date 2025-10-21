"""
User and message clustering utilities.

Foundation for automatic persona extraction via spectral clustering,
NMF, and archetypal analysis.
"""

from typing import Any, Optional

import numpy as np
from sklearn.cluster import KMeans, SpectralClustering
from sklearn.decomposition import NMF
from sklearn.preprocessing import normalize

from ..core.graph import InsightGraph
from ..core.models import Message, User
from ..core.vector_store import VectorStore


class MessageClusterer:
    """
    Cluster messages by topic and sentiment.

    Uses embeddings + metadata to discover thematic groups.
    """

    def __init__(self, graph: InsightGraph, vector_store: VectorStore):
        self.graph = graph
        self.vector_store = vector_store

    def cluster_by_topic(
        self,
        messages: list[Message],
        n_clusters: int = 5,
        method: str = "kmeans",
    ) -> dict[str, Any]:
        """
        Cluster messages by semantic topic.

        Args:
            messages: Messages to cluster
            n_clusters: Number of clusters
            method: Clustering method ('kmeans' or 'spectral')

        Returns:
            Clustering results with labels and cluster info
        """
        if not messages:
            return {"labels": [], "clusters": []}

        # Get embeddings
        embeddings = []
        valid_messages = []

        for msg in messages:
            if msg.embedding_id:
                # Fetch embedding from vector store
                # (In production, you'd batch this)
                try:
                    results = self.vector_store.search(
                        query=msg.cleaned_text or msg.text,
                        top_k=1,
                        filter_metadata={"message_id": str(msg.id)},
                    )
                    if results:
                        # Note: We'd need to modify VectorStore to return embeddings
                        # For now, we'll generate fresh embeddings
                        emb = self.vector_store.embed_text(msg.cleaned_text or msg.text)
                        embeddings.append(emb)
                        valid_messages.append(msg)
                except Exception:
                    continue

        if not embeddings:
            return {"labels": [], "clusters": []}

        X = np.array(embeddings)

        # Cluster
        if method == "spectral":
            clusterer = SpectralClustering(n_clusters=n_clusters, random_state=42)
        else:  # kmeans
            clusterer = KMeans(n_clusters=n_clusters, random_state=42)

        labels = clusterer.fit_predict(X)

        # Build cluster info
        clusters = []
        for i in range(n_clusters):
            cluster_msgs = [msg for msg, label in zip(valid_messages, labels) if label == i]

            # Extract common labels
            label_counts = {}
            for msg in cluster_msgs:
                for lbl in msg.labels:
                    label_counts[lbl.value] = label_counts.get(lbl.value, 0) + 1

            top_labels = sorted(label_counts.items(), key=lambda x: x[1], reverse=True)[:3]

            clusters.append(
                {
                    "cluster_id": i,
                    "size": len(cluster_msgs),
                    "top_labels": [lbl for lbl, _ in top_labels],
                    "message_ids": [str(msg.id) for msg in cluster_msgs],
                    "sample_messages": [msg.text[:100] for msg in cluster_msgs[:3]],
                }
            )

        return {
            "method": method,
            "n_clusters": n_clusters,
            "labels": labels.tolist(),
            "clusters": clusters,
        }


class UserClusterer:
    """
    Cluster users into persona segments.

    Foundation for automatic persona discovery via spectral methods.
    """

    def __init__(self, graph: InsightGraph, vector_store: VectorStore):
        self.graph = graph
        self.vector_store = vector_store

    def build_user_feature_matrix(self, users: list[User]) -> tuple[np.ndarray, list[str]]:
        """
        Build feature matrix for users.

        Features:
        - Capability bands (one-hot)
        - Playstyle signals (one-hot)
        - Message label distribution
        - Sentiment averages

        Args:
            users: Users to featurize

        Returns:
            Feature matrix (n_users x n_features) and feature names
        """
        from ..core.models import CapabilityBand, MessageLabel, PlaystyleSignal

        feature_vectors = []
        feature_names = []

        # Build feature names
        capability_features = [f"cap_{band.value}" for band in CapabilityBand]
        playstyle_features = [f"play_{signal.value}" for signal in PlaystyleSignal]
        label_features = [f"label_{label.value}" for label in MessageLabel]

        feature_names = capability_features + playstyle_features + label_features + ["avg_sentiment"]

        # Build vectors
        for user in users:
            vector = []

            # Capability bands (one-hot)
            for band in CapabilityBand:
                vector.append(1.0 if band in user.capability_bands else 0.0)

            # Playstyle signals (one-hot)
            for signal in PlaystyleSignal:
                vector.append(1.0 if signal in user.playstyle_signals else 0.0)

            # Message label distribution
            user_messages = [
                self.graph.get_message(msg_id)
                for msg_id in user.message_ids
                if self.graph.get_message(msg_id)
            ]

            label_counts = {label: 0 for label in MessageLabel}
            sentiments = []

            for msg in user_messages:
                for label in msg.labels:
                    label_counts[label] += 1
                if msg.sentiment_score is not None:
                    sentiments.append(msg.sentiment_score)

            # Normalize label counts
            total_labels = sum(label_counts.values()) or 1
            for label in MessageLabel:
                vector.append(label_counts[label] / total_labels)

            # Average sentiment
            avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0.0
            vector.append(avg_sentiment)

            feature_vectors.append(vector)

        X = np.array(feature_vectors)

        # Normalize
        X = normalize(X, norm="l2")

        return X, feature_names

    def cluster_users(
        self,
        users: list[User],
        n_clusters: int = 4,
        method: str = "spectral",
    ) -> dict[str, Any]:
        """
        Cluster users into persona segments.

        Args:
            users: Users to cluster
            n_clusters: Number of persona clusters
            method: Clustering method

        Returns:
            Clustering results with persona segments
        """
        if len(users) < n_clusters:
            return {"labels": [], "clusters": []}

        X, feature_names = self.build_user_feature_matrix(users)

        # Cluster
        if method == "spectral":
            clusterer = SpectralClustering(n_clusters=n_clusters, random_state=42)
        else:  # kmeans
            clusterer = KMeans(n_clusters=n_clusters, random_state=42)

        labels = clusterer.fit_predict(X)

        # Build persona clusters
        clusters = []
        for i in range(n_clusters):
            cluster_users = [user for user, label in zip(users, labels) if label == i]

            # Aggregate capability bands
            capability_counts = {}
            playstyle_counts = {}

            for user in cluster_users:
                for band in user.capability_bands:
                    capability_counts[band.value] = capability_counts.get(band.value, 0) + 1
                for signal in user.playstyle_signals:
                    playstyle_counts[signal.value] = playstyle_counts.get(signal.value, 0) + 1

            top_capabilities = sorted(capability_counts.items(), key=lambda x: x[1], reverse=True)[
                :3
            ]
            top_playstyles = sorted(playstyle_counts.items(), key=lambda x: x[1], reverse=True)[:3]

            clusters.append(
                {
                    "cluster_id": i,
                    "size": len(cluster_users),
                    "top_capabilities": [cap for cap, _ in top_capabilities],
                    "top_playstyles": [style for style, _ in top_playstyles],
                    "user_ids": [str(user.id) for user in cluster_users],
                    "sample_handles": [user.discord_handle for user in cluster_users[:5]],
                }
            )

        return {
            "method": method,
            "n_clusters": n_clusters,
            "labels": labels.tolist(),
            "clusters": clusters,
        }

    def extract_persona_bases_nmf(
        self,
        users: list[User],
        n_components: int = 6,
    ) -> dict[str, Any]:
        """
        Extract persona bases using Non-negative Matrix Factorization.

        This creates sparse, interpretable persona "directions" that users
        can be expressed as weighted combinations of.

        Args:
            users: Users to analyze
            n_components: Number of persona bases

        Returns:
            NMF results with basis vectors and user weights
        """
        if len(users) < n_components:
            return {"bases": [], "user_weights": []}

        X, feature_names = self.build_user_feature_matrix(users)

        # Ensure non-negative (NMF requirement)
        X = np.abs(X)

        # Run NMF
        nmf = NMF(n_components=n_components, random_state=42, max_iter=500)
        user_weights = nmf.fit_transform(X)  # Users x Bases
        bases = nmf.components_  # Bases x Features

        # Interpret each basis
        basis_interpretations = []
        for i, basis in enumerate(bases):
            # Find top features for this basis
            top_feature_indices = np.argsort(basis)[-5:][::-1]
            top_features = [
                (feature_names[idx], basis[idx]) for idx in top_feature_indices if basis[idx] > 0.01
            ]

            basis_interpretations.append(
                {
                    "basis_id": i,
                    "top_features": top_features,
                }
            )

        return {
            "n_components": n_components,
            "bases": basis_interpretations,
            "user_weights": user_weights.tolist(),
            "reconstruction_error": nmf.reconstruction_err_,
        }


# CLI for testing
def main():
    """Test clustering on existing data."""
    import os
    import sys
    from pathlib import Path

    from dotenv import load_dotenv

    load_dotenv()

    graph_data_dir = Path(os.getenv("GRAPH_DATA_DIR", "./data/graph"))
    chroma_persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma")

    graph = InsightGraph(data_dir=graph_data_dir)
    vector_store = VectorStore(
        persist_dir=chroma_persist_dir,
        collection_name="insight_graph",
        openai_api_key=os.getenv("OPENAI_API_KEY"),
    )

    # Test message clustering
    print("=== Message Clustering ===\n")
    messages = graph.list_messages(limit=100)
    msg_clusterer = MessageClusterer(graph, vector_store)
    msg_result = msg_clusterer.cluster_by_topic(messages, n_clusters=3)

    for cluster in msg_result["clusters"]:
        print(f"Cluster {cluster['cluster_id']}: {cluster['size']} messages")
        print(f"  Top labels: {', '.join(cluster['top_labels'])}")
        print(f"  Sample: {cluster['sample_messages'][0][:80]}...")
        print()

    # Test user clustering
    print("\n=== User Clustering ===\n")
    users = graph.list_users()
    user_clusterer = UserClusterer(graph, vector_store)
    user_result = user_clusterer.cluster_users(users, n_clusters=min(4, len(users)))

    for cluster in user_result["clusters"]:
        print(f"Cluster {cluster['cluster_id']}: {cluster['size']} users")
        print(f"  Capabilities: {', '.join(cluster['top_capabilities'])}")
        print(f"  Playstyles: {', '.join(cluster['top_playstyles'])}")
        print(f"  Sample users: {', '.join(cluster['sample_handles'])}")
        print()

    # Test NMF persona extraction
    if len(users) >= 4:
        print("\n=== NMF Persona Bases ===\n")
        nmf_result = user_clusterer.extract_persona_bases_nmf(users, n_components=min(4, len(users)))

        for basis in nmf_result["bases"]:
            print(f"Basis {basis['basis_id']}:")
            for feature, weight in basis["top_features"]:
                print(f"  {feature}: {weight:.3f}")
            print()


if __name__ == "__main__":
    main()

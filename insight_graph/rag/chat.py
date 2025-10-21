"""
RAG-powered chat interface for developers.

Provides conversational access to the Insight Graph with inline actions.
"""

import os
from typing import Optional

from openai import OpenAI

from ..core.graph import InsightGraph
from ..core.vector_store import VectorStore
from .retriever import DualIndexRetriever


class InsightCopilot:
    """
    Conversational interface to the Insight Graph.

    Answers queries like:
    - "What's blocking onboarding?"
    - "Show me performance issues in the swamp biome"
    - "Who's affected by the camera bug?"
    """

    def __init__(self, graph: InsightGraph, vector_store: VectorStore, model: str = "gpt-4-turbo-preview"):
        self.graph = graph
        self.vector_store = vector_store
        self.retriever = DualIndexRetriever(graph, vector_store)

        self.openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model

        # System prompt
        self.system_prompt = """You are an Insight Copilot for a game development team.

You have access to a knowledge graph of community feedback from Discord, including:
- User messages with embeddings and labels
- Threads and conversations
- Tracked issues with severity and status
- Personas (archetypal user segments)
- Build history

Your role is to help developers:
1. Quickly find relevant feedback and repro steps
2. Understand which users/personas are affected by issues
3. Triage and prioritize bugs
4. Generate PRD-ready summaries

When answering:
- Be concise and action-oriented
- Cite specific message IDs and threads
- Suggest next actions (create ticket, tag messages, etc.)
- Quantify impact when possible (# users, % of persona)
- Surface patterns across multiple reports

If the retrieved context doesn't contain enough info, say so."""

    def chat(self, query: str, channel_filter: Optional[str] = None) -> dict:
        """
        Answer a query using RAG.

        Args:
            query: User query
            channel_filter: Optional channel ID filter

        Returns:
            Response dict with answer and context
        """
        # Retrieve context
        context = self.retriever.retrieve(
            query=query,
            include_issues=True,
            include_personas=True,
            filter_channel=channel_filter,
        )

        # Build context string for LLM
        context_str = self._format_context(context)

        # Generate response
        messages = [
            {"role": "system", "content": self.system_prompt},
            {
                "role": "user",
                "content": f"Query: {query}\n\nContext:\n{context_str}\n\nPlease answer the query based on the context.",
            },
        ]

        response = self.openai.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
            max_tokens=1000,
        )

        answer = response.choices[0].message.content

        return {
            "query": query,
            "answer": answer,
            "context": context,
        }

    def _format_context(self, context: dict) -> str:
        """Format retrieved context for LLM consumption."""
        parts = []

        # Messages
        if context["messages"]:
            parts.append("### Relevant Messages\n")
            for idx, item in enumerate(context["messages"][:5], 1):
                msg = item["message"]
                similarity = item["similarity"]
                parts.append(
                    f"{idx}. [Message {msg.id}] (similarity: {similarity:.2f})\n"
                    f"   User: {msg.user_id}\n"
                    f"   Text: {msg.cleaned_text[:200]}...\n"
                    f"   Labels: {', '.join(label.value for label in msg.labels)}\n"
                )

        # Issues
        if context["issues"]:
            parts.append("\n### Related Issues\n")
            for idx, issue in enumerate(context["issues"][:3], 1):
                parts.append(
                    f"{idx}. [Issue {issue.id}] {issue.title}\n"
                    f"   Status: {issue.status.value} | Severity: {issue.severity.value}\n"
                    f"   Description: {issue.description[:200]}...\n"
                )

        # Personas
        if context["personas"]:
            parts.append("\n### Relevant Personas\n")
            for idx, persona in enumerate(context["personas"][:3], 1):
                parts.append(
                    f"{idx}. {persona.name}\n"
                    f"   Description: {persona.description}\n"
                    f"   Pain points: {', '.join(persona.pain_points[:3])}\n"
                )

        return "\n".join(parts)


# CLI interface
def main():
    """Simple CLI for testing the copilot."""
    import sys
    from pathlib import Path

    from dotenv import load_dotenv

    load_dotenv()

    # Initialize
    graph_data_dir = os.getenv("GRAPH_DATA_DIR", "./data/graph")
    chroma_persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma")
    chroma_collection = os.getenv("CHROMA_COLLECTION", "insight_graph")

    graph = InsightGraph(data_dir=Path(graph_data_dir))
    vector_store = VectorStore(
        persist_dir=chroma_persist_dir,
        collection_name=chroma_collection,
        openai_api_key=os.getenv("OPENAI_API_KEY"),
    )

    copilot = InsightCopilot(graph, vector_store)

    print("🤖 Insight Copilot ready!")
    print("Ask me anything about community feedback.\n")

    while True:
        try:
            query = input("You: ").strip()
            if not query or query.lower() in ["exit", "quit"]:
                break

            result = copilot.chat(query)
            print(f"\nCopilot: {result['answer']}\n")

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

    print("Goodbye!")


if __name__ == "__main__":
    main()

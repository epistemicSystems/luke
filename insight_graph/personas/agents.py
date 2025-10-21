"""
Interactive persona agents.

Turn persona profiles into callable LLM agents that can simulate
reactions to changes and forecast impact.
"""

import os
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

import yaml
from openai import OpenAI

from ..core.graph import InsightGraph
from ..core.vector_store import VectorStore
from ..rag.retriever import DualIndexRetriever


class PersonaAgent:
    """
    Interactive LLM agent for a persona.

    Can simulate reactions, forecast impact, and provide in-character feedback.
    """

    def __init__(
        self,
        profile_path: Path,
        graph: InsightGraph,
        vector_store: VectorStore,
        model: str = "gpt-4-turbo-preview",
    ):
        """
        Initialize a persona agent.

        Args:
            profile_path: Path to persona YAML profile
            graph: Insight graph
            vector_store: Vector store
            model: OpenAI model to use
        """
        self.profile_path = profile_path
        self.graph = graph
        self.vector_store = vector_store
        self.retriever = DualIndexRetriever(graph, vector_store)

        # Load profile
        with open(profile_path) as f:
            self.profile = yaml.safe_load(f)

        self.openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model

        # Extract key fields
        self.persona_id = self.profile["id"]
        self.name = self.profile["name"]
        self.system_prompt = self.profile["agent_config"]["system_prompt_template"]

    def simulate_reaction(self, change_description: str, context_refs: Optional[list[UUID]] = None) -> dict[str, Any]:
        """
        Simulate persona's reaction to a proposed change.

        Args:
            change_description: Description of the change (patch notes, feature, etc.)
            context_refs: Optional message/issue IDs for additional context

        Returns:
            Simulation result with reaction, risk scores, and evidence
        """
        # Build context
        context_parts = [f"Proposed change: {change_description}"]

        # Add referenced context if provided
        if context_refs:
            for ref_id in context_refs:
                msg = self.graph.get_message(ref_id)
                if msg:
                    context_parts.append(f"Past feedback: {msg.cleaned_text}")

        # Add typical messages from profile
        if "typical_messages" in self.profile:
            context_parts.append("\nYour typical feedback style:")
            for example in self.profile["typical_messages"][:3]:
                context_parts.append(f"- {example}")

        context_str = "\n".join(context_parts)

        # Build prompt
        user_prompt = f"""
{context_str}

Please simulate your reaction to this change:

1. **First-session reaction**: How would you react when first encountering this change?
2. **7-day retention risk**: On a scale of 0.0 (no risk) to 1.0 (would quit), how much does this risk your retention?
3. **Evidence**: Cite specific examples from your past feedback (if available)
4. **Mitigations**: Suggest ways to reduce negative impact on you

Respond in-character as {self.name}.
"""

        # Call LLM
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        response = self.openai.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
            max_tokens=800,
        )

        reaction = response.choices[0].message.content

        return {
            "persona_id": self.persona_id,
            "persona_name": self.name,
            "change": change_description,
            "reaction": reaction,
            "context": context_str,
        }

    def score_impact(self, issue_tags: list[str]) -> float:
        """
        Score how much an issue affects this persona.

        Args:
            issue_tags: Issue tags (e.g., ["performance", "swamp_biome"])

        Returns:
            Impact score (0.0 to 1.0)
        """
        impact_weights = self.profile["agent_config"]["impact_scoring"]["weights"]

        # Calculate weighted score
        total_weight = 0.0
        matched_weight = 0.0

        for tag in issue_tags:
            # Normalize tag (remove underscores, lowercase)
            normalized_tag = tag.replace("_", " ").replace("-", " ")

            # Check if tag matches any weight key
            for key, weight in impact_weights.items():
                normalized_key = key.replace("_", " ").replace("-", " ")
                if normalized_key in normalized_tag or normalized_tag in normalized_key:
                    matched_weight += weight
                    total_weight += 1.0
                    break

        # If no tags matched, return low baseline
        if total_weight == 0:
            return 0.1

        # Normalize to 0-1
        return min(matched_weight / total_weight, 1.0)


class PersonaSimulator:
    """Orchestrates multiple persona agents for impact forecasting."""

    def __init__(self, graph: InsightGraph, vector_store: VectorStore, profiles_dir: Path):
        self.graph = graph
        self.vector_store = vector_store
        self.profiles_dir = profiles_dir

        # Load all persona agents
        self.agents: dict[str, PersonaAgent] = {}
        for profile_path in profiles_dir.glob("*.yaml"):
            agent = PersonaAgent(profile_path, graph, vector_store)
            self.agents[agent.persona_id] = agent

    def simulate_change(self, change_description: str, context_refs: Optional[list[UUID]] = None) -> dict[str, Any]:
        """
        Run simulation with all personas.

        Args:
            change_description: Description of change
            context_refs: Optional context references

        Returns:
            Combined simulation results from all personas
        """
        results = []

        for persona_id, agent in self.agents.items():
            result = agent.simulate_reaction(change_description, context_refs)
            results.append(result)

        return {
            "change": change_description,
            "persona_reactions": results,
            "summary": self._summarize_reactions(results),
        }

    def _summarize_reactions(self, results: list[dict]) -> str:
        """Generate a summary of persona reactions."""
        summary_parts = [f"## Persona Impact Summary\n"]

        for result in results:
            summary_parts.append(f"**{result['persona_name']}**: {result['reaction'][:200]}...\n")

        return "\n".join(summary_parts)


# CLI for testing
def main():
    """Test persona simulation."""
    import sys

    from dotenv import load_dotenv

    load_dotenv()

    if len(sys.argv) < 2:
        print("Usage: python -m insight_graph.personas.agents <change_description>")
        sys.exit(1)

    change = sys.argv[1]

    # Initialize
    graph_data_dir = Path(os.getenv("GRAPH_DATA_DIR", "./data/graph"))
    chroma_persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma")
    profiles_dir = Path(__file__).parent / "profiles"

    graph = InsightGraph(data_dir=graph_data_dir)
    vector_store = VectorStore(
        persist_dir=chroma_persist_dir,
        collection_name="insight_graph",
        openai_api_key=os.getenv("OPENAI_API_KEY"),
    )

    simulator = PersonaSimulator(graph, vector_store, profiles_dir)
    result = simulator.simulate_change(change)

    print(result["summary"])


if __name__ == "__main__":
    main()

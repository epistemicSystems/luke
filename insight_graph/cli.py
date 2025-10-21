"""
Insight Graph CLI Tool

Unified command-line interface for common operations.
"""

import os
from pathlib import Path
from typing import Optional

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from .core.graph import InsightGraph
from .core.vector_store import VectorStore

load_dotenv()

console = Console()


# Global context for shared objects
class Context:
    def __init__(self):
        graph_data_dir = Path(os.getenv("GRAPH_DATA_DIR", "./data/graph"))
        chroma_persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma")
        openai_api_key = os.getenv("OPENAI_API_KEY")

        self.graph = InsightGraph(data_dir=graph_data_dir)
        self.vector_store = None

        if openai_api_key:
            self.vector_store = VectorStore(
                persist_dir=chroma_persist_dir,
                collection_name="insight_graph",
                openai_api_key=openai_api_key,
            )


@click.group()
@click.pass_context
def cli(ctx):
    """Insight Graph CLI - Unified interface for community intelligence."""
    ctx.obj = Context()


# === Stats Commands ===


@cli.command()
@click.pass_context
def stats(ctx):
    """Show graph statistics."""
    graph = ctx.obj.graph

    users = graph.list_users()
    messages = graph.list_messages(limit=10000)
    issues = graph.list_issues()
    personas = graph.list_personas()

    table = Table(title="Insight Graph Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", style="green")

    table.add_row("Users", str(len(users)))
    table.add_row("Messages", str(len(messages)))
    table.add_row("Issues", str(len(issues)))
    table.add_row("Personas", str(len(personas)))

    if ctx.obj.vector_store:
        vec_stats = ctx.obj.vector_store.get_stats()
        table.add_row("Embeddings", str(vec_stats["count"]))

    console.print(table)


# === Issue Commands ===


@cli.group()
def issue():
    """Manage issues."""
    pass


@issue.command("list")
@click.option("--status", help="Filter by status")
@click.option("--limit", default=20, help="Max results")
@click.pass_context
def list_issues(ctx, status, limit):
    """List issues."""
    graph = ctx.obj.graph

    issues = graph.list_issues(status=status)[:limit]

    if not issues:
        console.print("[yellow]No issues found.[/yellow]")
        return

    table = Table(title=f"Issues ({len(issues)})")
    table.add_column("Title", style="cyan")
    table.add_column("Severity", style="red")
    table.add_column("Status", style="yellow")
    table.add_column("Tags", style="green")

    for issue in issues:
        table.add_row(
            issue.title[:50],
            issue.severity.value,
            issue.status.value,
            ", ".join(list(issue.tags)[:3]),
        )

    console.print(table)


@issue.command("show")
@click.argument("issue_id")
@click.pass_context
def show_issue(ctx, issue_id):
    """Show issue details."""
    from uuid import UUID

    graph = ctx.obj.graph

    try:
        issue = graph.get_issue(UUID(issue_id))
    except ValueError:
        console.print(f"[red]Invalid issue ID: {issue_id}[/red]")
        return

    if not issue:
        console.print(f"[red]Issue not found: {issue_id}[/red]")
        return

    console.print(f"\n[bold cyan]Issue: {issue.title}[/bold cyan]")
    console.print(f"[yellow]ID:[/yellow] {issue.id}")
    console.print(f"[yellow]Severity:[/yellow] {issue.severity.value}")
    console.print(f"[yellow]Status:[/yellow] {issue.status.value}")
    console.print(f"[yellow]Tags:[/yellow] {', '.join(issue.tags)}")
    console.print(f"\n[bold]Description:[/bold]\n{issue.description}")

    if issue.steps_to_repro:
        console.print(f"\n[bold]Steps to Reproduce:[/bold]")
        for i, step in enumerate(issue.steps_to_repro, 1):
            console.print(f"  {i}. {step}")

    console.print(f"\n[bold]Linked Messages:[/bold] {len(issue.linked_message_ids)}")
    console.print(f"[bold]Linked Threads:[/bold] {len(issue.linked_thread_ids)}")


# === Persona Commands ===


@cli.group()
def persona():
    """Manage personas."""
    pass


@persona.command("list")
@click.pass_context
def list_personas(ctx):
    """List personas."""
    graph = ctx.obj.graph

    personas = graph.list_personas()

    if not personas:
        console.print("[yellow]No personas found.[/yellow]")
        return

    table = Table(title=f"Personas ({len(personas)})")
    table.add_column("Name", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Pain Points", style="red")

    for p in personas:
        table.add_row(
            p.name,
            p.description[:60] + "..." if len(p.description) > 60 else p.description,
            str(len(p.pain_points)),
        )

    console.print(table)


@persona.command("simulate")
@click.argument("change_description")
@click.option("--persona-id", help="Specific persona to simulate (or all if omitted)")
@click.pass_context
def simulate_persona(ctx, change_description, persona_id):
    """Simulate persona reactions to a change."""
    from .personas.agents import PersonaAgent, PersonaSimulator

    graph = ctx.obj.graph
    vector_store = ctx.obj.vector_store

    if not vector_store:
        console.print("[red]Error: OpenAI API key required for simulation.[/red]")
        return

    profiles_dir = Path(__file__).parent / "personas" / "profiles"

    if persona_id:
        # Single persona
        console.print(f"[cyan]Simulating single persona...[/cyan]\n")
        profile_path = profiles_dir / f"{persona_id}.yaml"

        if not profile_path.exists():
            console.print(f"[red]Persona profile not found: {persona_id}[/red]")
            return

        agent = PersonaAgent(profile_path, graph, vector_store)
        result = agent.simulate_reaction(change_description)

        console.print(f"[bold cyan]{result['persona_name']}[/bold cyan]")
        console.print(result["reaction"])
    else:
        # All personas
        console.print(f"[cyan]Simulating all personas...[/cyan]\n")
        simulator = PersonaSimulator(graph, vector_store, profiles_dir)
        result = simulator.simulate_change(change_description)

        for reaction in result["persona_reactions"]:
            console.print(f"\n[bold cyan]{reaction['persona_name']}[/bold cyan]")
            console.print(reaction["reaction"])
            console.print("-" * 60)


# === Brief Commands ===


@cli.group()
def brief():
    """Generate briefs."""
    pass


@brief.command("daily")
@click.option("--hours", default=24, help="Lookback hours")
@click.option("--format", type=click.Choice(["discord", "slack", "text"]), default="discord")
@click.pass_context
def daily_brief(ctx, hours, format):
    """Generate daily brief."""
    from .briefs.daily import DailyBriefGenerator

    graph = ctx.obj.graph
    vector_store = ctx.obj.vector_store

    if not vector_store:
        console.print("[red]Error: OpenAI API key required for briefs.[/red]")
        return

    console.print(f"[cyan]Generating daily brief ({hours}h lookback)...[/cyan]\n")

    generator = DailyBriefGenerator(graph, vector_store)
    result = generator.generate(lookback_hours=hours, format=format)

    console.print(result["formatted"])


@brief.command("voice")
@click.argument("brief_file", type=click.Path(exists=True))
@click.option("--output", default="./data/voice", help="Output directory")
@click.option("--short", is_flag=True, help="Generate 60s summary only")
@click.pass_context
def voice_brief(ctx, brief_file, output, short):
    """Generate voice readout from brief file."""
    from .briefs.voice import VoiceGenerator

    console.print(f"[cyan]Generating voice readout...[/cyan]\n")

    brief_text = Path(brief_file).read_text()
    output_dir = Path(output)

    generator = VoiceGenerator(output_dir)

    if short:
        audio_path = generator.generate_60s_summary(brief_text)
        console.print(f"[green]Generated 60s audio:[/green] {audio_path}")
    else:
        audio_path = generator.generate_from_brief(brief_text)
        console.print(f"[green]Generated full audio:[/green] {audio_path}")


# === Chat Commands ===


@cli.command()
@click.argument("query", required=False)
@click.pass_context
def chat(ctx, query):
    """Interactive chat with the copilot."""
    from .rag.chat import InsightCopilot

    graph = ctx.obj.graph
    vector_store = ctx.obj.vector_store

    if not vector_store:
        console.print("[red]Error: OpenAI API key required for chat.[/red]")
        return

    copilot = InsightCopilot(graph, vector_store)

    if query:
        # Single query mode
        result = copilot.chat(query)
        console.print(f"\n[bold cyan]Query:[/bold cyan] {query}")
        console.print(f"[bold green]Answer:[/bold green]\n{result['answer']}\n")
    else:
        # Interactive mode
        console.print("[bold cyan]🤖 Insight Copilot[/bold cyan]")
        console.print("Ask me anything about community feedback. Type 'exit' to quit.\n")

        while True:
            try:
                user_query = console.input("[bold yellow]You:[/bold yellow] ").strip()

                if not user_query or user_query.lower() in ["exit", "quit"]:
                    break

                result = copilot.chat(user_query)
                console.print(f"\n[bold green]Copilot:[/bold green] {result['answer']}\n")

            except KeyboardInterrupt:
                break
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")

        console.print("\n[cyan]Goodbye![/cyan]")


# === Search Commands ===


@cli.command()
@click.argument("query")
@click.option("--limit", default=10, help="Max results")
@click.pass_context
def search(ctx, query, limit):
    """Semantic search over messages."""
    vector_store = ctx.obj.vector_store

    if not vector_store:
        console.print("[red]Error: OpenAI API key required for search.[/red]")
        return

    console.print(f"[cyan]Searching for: {query}[/cyan]\n")

    results = vector_store.search(query, top_k=limit)

    if not results:
        console.print("[yellow]No results found.[/yellow]")
        return

    table = Table(title=f"Search Results ({len(results)})")
    table.add_column("Similarity", style="green")
    table.add_column("Text", style="white")

    for result in results:
        similarity = 1.0 - result["distance"]
        text = result["text"][:80] + "..." if len(result["text"]) > 80 else result["text"]
        table.add_row(f"{similarity:.2f}", text)

    console.print(table)


# === Export Commands ===


@cli.command()
@click.option("--output", default="./export", help="Export directory")
@click.pass_context
def export(ctx, output):
    """Export graph data to JSON."""
    import json

    graph = ctx.obj.graph
    output_dir = Path(output)
    output_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"[cyan]Exporting graph to {output_dir}...[/cyan]\n")

    # Export each entity type
    entities = {
        "users": [u.model_dump(mode="json") for u in graph.list_users()],
        "messages": [m.model_dump(mode="json") for m in graph.list_messages(limit=10000)],
        "issues": [i.model_dump(mode="json") for i in graph.list_issues()],
        "personas": [p.model_dump(mode="json") for p in graph.list_personas()],
    }

    for entity_type, data in entities.items():
        output_path = output_dir / f"{entity_type}.json"
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        console.print(f"[green]✓[/green] Exported {len(data)} {entity_type} to {output_path}")

    console.print(f"\n[green]Export complete![/green]")


def main():
    """Entry point for CLI."""
    cli()


if __name__ == "__main__":
    main()

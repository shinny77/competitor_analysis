"""Click-based CLI for the Competitive Intelligence Platform."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import click
from dotenv import load_dotenv

load_dotenv()


@click.group()
@click.version_option(version="0.1.0", prog_name="competitor-analysis")
def cli():
    """Competitive Intelligence Platform - Multi-agent competitor analysis."""
    pass


@cli.command()
@click.option("--config", "-c", required=True, type=click.Path(exists=True), help="Path to project config JSON")
def init(config: str):
    """Initialise a project: validate config and create output directories."""
    from .config import load_project_config

    click.echo(f"Loading config: {config}")
    try:
        project = load_project_config(config)
    except Exception as e:
        click.echo(f"Config validation failed: {e}", err=True)
        sys.exit(1)

    click.echo(f"Project: {project.project_name}")
    click.echo(f"Target: {project.target_company} ({project.target_website})")
    click.echo(f"Industry: {project.industry}")
    click.echo(f"Competitors: {len(project.competitors)}")
    for c in project.competitors:
        click.echo(f"  - {c.name} ({c.website})")
    click.echo(f"Budget: ${project.budget.max_usd:.2f}")

    # Create output directories
    dirs = [
        "output",
        "output/logs",
        "output/enablement",
        "checkpoints",
        "research",
        "analysis",
        "analysis/profiles",
        "scoring",
    ]
    for comp in project.competitors:
        slug = comp.name.lower().replace(" ", "_").replace(".", "")
        dirs.append(f"research/{slug}")
        dirs.append(f"output/enablement/{slug}")

    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)

    click.echo(f"\nCreated {len(dirs)} directories. Project initialised.")


@cli.command("test-llm")
def test_llm():
    """Test connectivity to all 4 LLM providers."""
    providers = [
        ("claude", "ANTHROPIC_API_KEY", "claude-sonnet-4-20250514"),
        ("openai", "OPENAI_API_KEY", "gpt-4o"),
        ("gemini", "GOOGLE_API_KEY", "gemini-2.0-flash"),
        ("grok", "XAI_API_KEY", "grok-2"),
    ]

    from .llm.claude_client import ClaudeClient
    from .llm.openai_client import OpenAIClient
    from .llm.gemini_client import GeminiClient
    from .llm.grok_client import GrokClient

    client_map = {
        "claude": ClaudeClient,
        "openai": OpenAIClient,
        "gemini": GeminiClient,
        "grok": GrokClient,
    }

    results = {}
    for provider, env_var, model in providers:
        api_key = os.environ.get(env_var)
        if not api_key:
            click.echo(f"  [{provider:8s}] SKIP - {env_var} not set")
            results[provider] = "skipped"
            continue

        try:
            client = client_map[provider](api_key=api_key, model=model, max_tokens=50, temperature=0.0)
            resp = client.complete("Say 'OK' if you can hear me. One word only.")
            click.echo(
                f"  [{provider:8s}] OK - {resp.model} "
                f"({resp.total_tokens} tokens, ${resp.cost_usd:.6f})"
            )
            results[provider] = "ok"
        except Exception as e:
            click.echo(f"  [{provider:8s}] FAIL - {e}")
            results[provider] = f"error: {e}"

    ok_count = sum(1 for v in results.values() if v == "ok")
    click.echo(f"\n{ok_count}/{len(providers)} providers connected.")


@cli.command()
@click.option("--save", "action", flag_value="save", help="Save a checkpoint")
@click.option("--load", "action", flag_value="load", help="Load a checkpoint")
@click.option("--list", "action", flag_value="list", help="List all checkpoints")
@click.option("--clear", "action", flag_value="clear", help="Clear all checkpoints")
@click.option("--stage", "-s", default="test_stage", help="Stage name for save/load")
@click.option("--project", "-p", default="default", help="Project name")
@click.option("--dir", "-d", "checkpoint_dir", default="checkpoints", help="Checkpoint directory")
def checkpoint(action: str, stage: str, project: str, checkpoint_dir: str):
    """Manage pipeline checkpoints."""
    from .pipeline.checkpoint import CheckpointManager

    mgr = CheckpointManager(checkpoint_dir=checkpoint_dir)

    if action == "save":
        test_data = {"stage": stage, "status": "test", "message": "Checkpoint test"}
        path = mgr.save(stage, test_data, project)
        click.echo(f"Checkpoint saved: {path}")

    elif action == "load":
        data = mgr.load(stage, project)
        if data:
            click.echo(f"Checkpoint loaded for stage '{stage}':")
            click.echo(json.dumps(data, indent=2))
        else:
            click.echo(f"No checkpoint found for stage '{stage}' in project '{project}'")

    elif action == "list":
        checkpoints = mgr.list_checkpoints(project if project != "default" else None)
        if checkpoints:
            click.echo(f"Found {len(checkpoints)} checkpoint(s):")
            for cp in checkpoints:
                click.echo(f"  {cp['file']:40s} stage={cp['stage']:20s} {cp['timestamp']}")
        else:
            click.echo("No checkpoints found.")

    elif action == "clear":
        mgr.clear(project if project != "default" else None)
        click.echo("Checkpoints cleared.")

    else:
        click.echo("Specify --save, --load, --list, or --clear")


@cli.command()
@click.option("--config", "-c", required=True, type=click.Path(exists=True), help="Path to project config JSON")
def run(config: str):
    """Run the full competitive analysis pipeline."""
    click.echo("Pipeline execution not yet implemented (Sprint 6).")
    click.echo("Use 'init' to set up the project, 'test-llm' to verify providers.")


@cli.command()
def cost():
    """Show cost tracking summary for the current project."""
    cost_file = Path("output/cost_log.json")
    if not cost_file.exists():
        click.echo("No cost log found. Run a pipeline first.")
        return

    with open(cost_file) as f:
        data = json.load(f)

    summary = data.get("summary", {})
    click.echo(f"Total cost: ${summary.get('total_cost_usd', 0):.4f}")
    click.echo(f"Budget: ${summary.get('budget_usd', 0):.2f} ({summary.get('budget_pct_used', 0):.1f}% used)")
    click.echo(f"Total calls: {summary.get('total_calls', 0)}")
    click.echo(f"Input tokens: {summary.get('total_input_tokens', 0):,}")
    click.echo(f"Output tokens: {summary.get('total_output_tokens', 0):,}")

    by_provider = summary.get("by_provider", {})
    if by_provider:
        click.echo("\nBy provider:")
        for provider, cost_val in by_provider.items():
            click.echo(f"  {provider:10s}: ${cost_val:.4f}")


@cli.command()
def version():
    """Show version info."""
    click.echo("Competitive Intelligence Platform v0.1.0")
    click.echo("Sprint 1 - Foundation")


if __name__ == "__main__":
    cli()

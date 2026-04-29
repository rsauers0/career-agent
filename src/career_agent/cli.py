from __future__ import annotations

import typer
from rich.console import Console

from career_agent.config import get_settings

app = typer.Typer(
    no_args_is_help=True,
    help="Career Agent: local-first career workflow tooling.",
)
console = Console()


@app.callback()
def cli() -> None:
    """Career Agent command group."""


@app.command()
def doctor() -> None:
    """Confirm the v2 foundation CLI is runnable."""

    settings = get_settings()
    console.print("[bold green]Career Agent v2 foundation is ready.[/bold green]")
    console.print(f"Data directory: {settings.data_dir}")


def main() -> None:
    """Run the Career Agent CLI."""

    app()


if __name__ == "__main__":
    main()

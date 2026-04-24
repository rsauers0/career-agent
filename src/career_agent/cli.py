from __future__ import annotations

import typer
from rich.console import Console

app = typer.Typer(
    no_args_is_help=True,
    help="Career Agent: a local-first CLI for career profiles, job search, and tailored documents.",
)
profile_app = typer.Typer(help="Manage the career profile.")
console = Console()


@app.callback()
def cli() -> None:
    """CLI entrypoint for grouped commands."""


@app.command()
def doctor() -> None:
    """Confirm the CLI scaffold is wired correctly."""
    console.print(
        "[bold green]Career Agent[/bold green] is installed and ready for step-by-step development."
    )


@profile_app.callback()
def profile_cli() -> None:
    """Commands for working with the career profile."""


app.add_typer(profile_app, name="profile")


def main() -> None:
    app()

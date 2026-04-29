# Career Agent

Career Agent is a local-first Python application for managing structured career data and building AI-assisted job search workflows.

This branch, `v2-foundation`, is rebuilding the application foundation around smaller, CLI-first workflows before reintroducing TUI and LLM-assisted features.

## Current Branch Status

`v2-foundation` is a foundation rebuild branch.

Current scope:

- keep the project runnable through a minimal Typer CLI
- keep configuration loading through `pydantic-settings`
- rebuild one component at a time
- maintain component boundaries for User Preferences, Experience Roles, Role Sources, and Experience Bullets
- use JSON persistence first
- defer TUI and LLM workflow integration until the underlying services are clear and tested

See [docs/v2-foundation-plan.md](docs/v2-foundation-plan.md) for the rebuild plan.
See [docs/component-architecture.md](docs/component-architecture.md) for the current component architecture.
See [docs/diagrams.md](docs/diagrams.md) for Mermaid diagrams of the current architecture and guardrail model.
See [docs/cli-reference.md](docs/cli-reference.md) for current CLI examples.
See [docs/storage.md](docs/storage.md) for the current local JSON storage shape.

## Install

Prerequisites:

- Python 3.13
- `uv`

Install dependencies:

```bash
uv sync
```

## Run

Run the current CLI health check:

```bash
uv run career-agent doctor
```

Show saved user preferences:

```bash
uv run career-agent preferences show
```

List saved experience roles:

```bash
uv run career-agent roles list
```

List saved role sources:

```bash
uv run career-agent sources list
```

List saved experience bullets:

```bash
uv run career-agent bullets list
```

Run tests:

```bash
uv run pytest
```

Run linting:

```bash
uv run ruff check .
```

## Configuration

Career Agent reads configuration from environment variables or a local `.env` file.

Common setting:

```dotenv
CAREER_AGENT_DATA_DIR=~/.career-agent
```

If `CAREER_AGENT_DATA_DIR` is unset, the app uses:

```text
<home-directory>/.career-agent
```

## Development Direction

The rebuild sequence is:

1. User Preferences model, JSON repository, service, CLI, and tests.
2. Experience Role model, JSON repository, service, CLI, and tests.
3. Role Source model, JSON repository, service, CLI, and tests.
4. Experience Bullet model, JSON repository, service, CLI, and tests.
5. Experience AI workflow harness through CLI/dev commands.
6. TUI presentation once the workflow is stable.
7. Optional FastAPI interface later, using the same application services.

The intended architecture remains:

```text
CLI / TUI / FastAPI
        -> application services
        -> repositories
        -> local JSON files
```

AI outputs should be treated as structured proposals. Application services should validate and apply those proposals deterministically.

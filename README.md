# Career Agent

Career Agent is a local-first Python application for managing structured career data and building AI-assisted job search workflows.

This branch, `v2-foundation`, is rebuilding the application foundation around smaller, CLI-first workflows before expanding TUI and LLM-assisted features.

## Current Branch Status

`v2-foundation` is a foundation rebuild branch.

Current scope:

- keep the project runnable through a minimal Typer CLI
- keep configuration loading through `pydantic-settings`
- rebuild one component at a time
- maintain component boundaries for User Preferences, Experience Roles, Role Sources, Experience Facts, Scoped Constraints, Source Analysis, and Fact Review
- use JSON persistence first
- keep TUI deferred while validating workflow behavior through the CLI
- support opt-in LLM-backed source question and source finding generation through an OpenAI-compatible endpoint

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

List saved experience facts:

```bash
uv run career-agent facts list
```

List saved source analysis runs:

```bash
uv run career-agent source-analysis runs list
```

Add a global hard-rule constraint:

```bash
uv run career-agent constraints add \
  --scope-type global \
  --constraint-type hard_rule \
  --rule-text "Do not use em dashes."
```

Start a fact review thread:

```bash
uv run career-agent fact-review threads start --fact-id <fact-id>
```

Add and apply a structured fact review action:

```bash
uv run career-agent fact-review actions add \
  --thread-id <thread-id> \
  --action-type revise_fact \
  --revised-text "Revised grounded fact text."
uv run career-agent fact-review actions apply <action-id>
```

Run source analysis for unanalyzed role sources:

```bash
uv run career-agent experience-workflow analyze-sources --role-id <role-id>
```

Generate source findings after clarification questions are resolved or skipped:

```bash
uv run career-agent experience-workflow generate-findings --run-id <run-id>
```

Apply accepted source findings through deterministic fact workflows:

```bash
uv run career-agent experience-workflow apply-findings --run-id <run-id>
```

Run tests:

```bash
uv run pytest
```

Run linting:

```bash
uv run ruff check .
```

Run type checking:

```bash
uv run mypy
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

Optional LLM settings:

```dotenv
CAREER_AGENT_LLM_BASE_URL=http://localhost:1234/v1
CAREER_AGENT_LLM_MODEL=<model-name>
CAREER_AGENT_LLM_API_KEY=
```

If no LLM base URL is configured, supported workflows use deterministic local behavior.

## Development Direction

The rebuild sequence is:

1. User Preferences model, JSON repository, service, CLI, and tests.
2. Experience Role model, JSON repository, service, CLI, and tests.
3. Role Source model, JSON repository, service, CLI, and tests.
4. Experience Fact model, JSON repository, service, CLI, and tests.
5. Source Analysis model, JSON repository, service, CLI, and tests.
6. Fact Review threads, messages, actions, JSON repository, service, CLI, and tests.
7. Scoped Constraints model, JSON repository, service, CLI, and tests.
8. Experience Workflow service, CLI/dev command, and tests.
9. TUI presentation once the workflow is stable.
10. Optional FastAPI interface later, using the same application services.

The intended architecture remains:

```text
CLI / TUI / FastAPI
        -> application services
        -> repositories
        -> local JSON files
```

AI outputs should be treated as structured proposals. Application services should validate and apply those proposals deterministically.

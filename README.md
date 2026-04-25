# Career Agent

Career Agent is a local-first Python application for managing structured career data, analyzing jobs, and generating tailored application materials.

A core design goal is to use local LLMs through OpenAI-compatible APIs wherever practical. Instead of assuming a single large hosted model, the project is being built around structured workflows, intermediate validation, and evaluation-driven iteration so smaller/local models can produce high-quality results with lower cost and better privacy.

## Current Status

Implemented:
- Typer/Rich CLI scaffold
- initial Textual TUI dashboard
- read-only Textual user preferences screen
- Pydantic domain models
- local file-based persistence with snapshot-on-overwrite
- profile service layer
- component status evaluation
- `profile init` (storage scaffolding only)
- `profile show`
- `preferences show`
- `preferences status`
- `preferences wizard`
- `tui`

Planned next:
- Textual preferences authoring screen
- `profile wizard` or profile authoring screen for high-level `CareerProfile` fields
- separate experience-entry workflows
- AI-assisted job normalization and fit matching
- tailored document generation

## Design Direction

Career Agent is being built around:
- local-first structured data
- modular domain / application / infrastructure separation
- AI workflows grounded in canonical data
- reusable workflows that can move from CLI to TUI cleanly
- component-first development: implement behavior, validate/status it, then expose it in the interface
- Textual as the planned primary local interface, with Typer remaining useful for scripting and development
- LLM assistance only where it adds value, not as a requirement for simple data entry

See [docs/architecture.md](docs/architecture.md) for the current layer map and file responsibilities.

## Storage Model

Canonical data is stored locally as structured JSON for transparency, portability, and privacy-focused use.

Profile writes use snapshot-on-overwrite behavior so earlier states can be preserved during iterative editing.

Current storage shape:

```text
<data_dir>/
  profile/
    user_preferences.json
    career_profile.json
  snapshots/
    profile/
```

## Development

Install dependencies:

```bash
uv sync
```

Run the CLI:

```bash
uv run career-agent --help
```

Launch the local TUI:

```bash
uv run career-agent tui
```

From the TUI dashboard, press `p` to open User Preferences and `b` or `Esc` to return.

Initialize storage scaffolding:

```bash
uv run career-agent profile init
```

Create or update user preferences:

```bash
uv run career-agent preferences wizard
```

Show current stored data:

```bash
uv run career-agent preferences show
uv run career-agent preferences status
uv run career-agent profile show
```

## Configuration

Configuration is loaded from environment variables or a local `.env` file via `pydantic-settings`.

Create a local config file if needed:

```bash
cp .env.example .env
```

Currently supported:
- `CAREER_AGENT_DATA_DIR`
  Overrides the default local data directory. If unset, the app uses `~/.career-agent`.

Run tests:

```bash
uv run pytest -q
```

Run linting:

```bash
uv run ruff check .
uv run ruff format --check .
```

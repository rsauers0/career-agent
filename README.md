# Career Agent

Career Agent is a local-first Python application for managing structured career data, analyzing jobs, and generating tailored application materials.

A core design goal is to use local LLMs through OpenAI-compatible APIs wherever practical. Instead of assuming a single large hosted model, the project is being built around structured workflows, intermediate validation, and evaluation-driven iteration so smaller/local models can produce high-quality results with lower cost and better privacy.

## Current Status

Implemented:
- Typer/Rich CLI scaffold
- initial Textual TUI dashboard
- editable Textual user preferences screen
- Textual Career Profile overview screen
- Textual Experience list/detail screens and Add Experience form
- Pydantic domain models
- local file-based persistence with snapshot-on-overwrite
- profile service layer
- component status evaluation
- `profile init` (storage scaffolding only)
- `profile show`
- `preferences show`
- `preferences status`
- `preferences wizard`
- `experience create`
- `experience list`
- `experience show`
- `experience details`
- `experience source`
- `experience questions`
- `experience answer`
- `experience draft`
- `experience accept`
- `tui`

Planned next:
- refine Textual preferences validation and keyboard navigation
- `profile wizard` or profile authoring screen for high-level `CareerProfile` fields
- refine experience intake review and editing
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
See [docs/security.md](docs/security.md) for the current security and privacy posture.

## Install And Run The TUI

The primary local interface is the Textual TUI.

Prerequisites:
- Git
- uv

Install Git:
- Linux: use your distribution package manager, such as `sudo apt install git` on Debian/Ubuntu.
- Windows: install Git for Windows from <https://git-scm.com/install/windows>, or use `winget install --id Git.Git -e --source winget`.

Install uv:
- Linux/macOS:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

- Windows PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Clone and run on Linux/macOS:

```bash
git clone https://github.com/rsauers0/career-agent.git
cd career-agent
uv sync
uv run career-agent tui
```

Clone and run on Windows PowerShell:

```powershell
git clone https://github.com/rsauers0/career-agent.git
Set-Location career-agent
uv sync
uv run career-agent tui
```

The first `uv sync` creates the local virtual environment and installs dependencies from `uv.lock`. The `uv run career-agent tui` command launches the TUI.

## Storage Model

Canonical data is stored locally as structured JSON for transparency, portability, and privacy-focused use.

Profile writes use snapshot-on-overwrite behavior so earlier states can be preserved during iterative editing.

Current storage shape:

```text
<data_dir>/
  profile/
    user_preferences.json
    career_profile.json
  intake/
    experience/
      <session_id>.json
  snapshots/
    profile/
    intake/
      experience/
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

From the TUI dashboard:
- press `p` to open User Preferences, save edits from the form, and press `b` or `Esc` to return
- press `c` to open Career Profile, then choose Manage Experience to add or review experience intake sessions

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

Create an experience intake session, capture source text, and generate follow-up questions:

```bash
uv run career-agent experience create \
  --employer-name "Acme Analytics" \
  --job-title "Senior Data Engineer" \
  --location "Chicago, IL" \
  --employment-type full-time \
  --start-date "05/2021" \
  --end-date "06/2024"
uv run career-agent experience details <session-id> \
  --employer-name "Acme Analytics" \
  --job-title "Senior Data Engineer" \
  --start-date "05/2021" \
  --current-role
uv run career-agent experience source <session-id> --text "- Built reporting pipeline"
uv run career-agent experience source <session-id> --from-file bullets.md
uv run career-agent experience source <session-id> --text "- Added alerting" --append
uv run career-agent experience questions <session-id>
uv run career-agent experience answer <session-id>
uv run career-agent experience draft <session-id>
uv run career-agent experience accept <session-id>
uv run career-agent experience show <session-id>
```

The `experience accept` command copies the draft `ExperienceEntry` into the canonical `CareerProfile`.
By default, `experience source` replaces source text. Use `--append` to add to existing source text.

The `experience questions` and `experience draft` commands call the configured OpenAI-compatible LLM endpoint. Use a local endpoint if you want this workflow to remain local-first.

## Configuration

Configuration is loaded from environment variables or a local `.env` file via `pydantic-settings`.

Create a local config file if needed:

```bash
cp .env.example .env
```

On Windows PowerShell, use:

```powershell
Copy-Item .env.example .env
```

Currently supported:
- `CAREER_AGENT_DATA_DIR`
  Overrides the default local data directory.
- `CAREER_AGENT_LLM_BASE_URL`
  Optional OpenAI-compatible LLM API base URL for LLM-assisted workflows.
- `CAREER_AGENT_LLM_API_KEY`
  Optional API key for the configured LLM endpoint.
- `CAREER_AGENT_LLM_MODEL`
  Optional default model name for LLM-assisted workflows.
- `CAREER_AGENT_LLM_EXTRACTION_BASE_URL`
  Optional OpenAI-compatible LLM API base URL for extraction workflows. Defaults to `CAREER_AGENT_LLM_BASE_URL` if unset.
- `CAREER_AGENT_LLM_EXTRACTION_API_KEY`
  Optional API key for the extraction endpoint. Defaults to `CAREER_AGENT_LLM_API_KEY` if unset.
- `CAREER_AGENT_LLM_EXTRACTION_MODEL`
  Optional model name for extraction workflows. Defaults to `CAREER_AGENT_LLM_MODEL` if unset.
- `CAREER_AGENT_LLM_EVAL_BASE_URL`
  Optional OpenAI-compatible LLM API base URL for evaluation workflows. Defaults to `CAREER_AGENT_LLM_BASE_URL` if unset.
- `CAREER_AGENT_LLM_EVAL_API_KEY`
  Optional API key for the evaluation endpoint. Defaults to `CAREER_AGENT_LLM_API_KEY` if unset.
- `CAREER_AGENT_LLM_EVAL_MODEL`
  Optional model name for evaluation workflows. Defaults to `CAREER_AGENT_LLM_MODEL` if unset.

If `CAREER_AGENT_DATA_DIR` is unset, the app creates a `.career-agent` directory under the current user's home directory using Python's `Path.home()`. This keeps the default portable across Linux, macOS, and Windows.

Example `.env` values:

```dotenv
# Portable user-home path
CAREER_AGENT_DATA_DIR=~/.career-agent

# Windows absolute path
CAREER_AGENT_DATA_DIR=C:/Users/ExampleUser/.career-agent
```

The `~/.career-agent` value is the recommended cross-platform option because the app expands `~` through Python's `Path.expanduser()`. Forward slashes are recommended in `.env` paths because Python handles them correctly on Windows and they avoid backslash escaping confusion.

Example LLM `.env` values:

```dotenv
# Local OpenAI-compatible endpoint
CAREER_AGENT_LLM_BASE_URL=http://localhost:1234/v1
CAREER_AGENT_LLM_API_KEY=not-needed-for-local
CAREER_AGENT_LLM_MODEL=qwen36

# Optional role-specific model/endpoint overrides
CAREER_AGENT_LLM_EXTRACTION_MODEL=gemma4-doc
CAREER_AGENT_LLM_EVAL_MODEL=mistral-small-4-review

# Hosted OpenAI-compatible endpoint
CAREER_AGENT_LLM_BASE_URL=https://api.openai.com/v1
CAREER_AGENT_LLM_API_KEY=replace-with-your-api-key
CAREER_AGENT_LLM_MODEL=gpt-4.1-mini
```

Role-specific extraction and evaluation settings can point to different OpenAI-compatible endpoints if your local or hosted model router separates those workloads.

LLM configuration is optional. Profile and preference workflows do not require an LLM connection. The `experience questions` and `experience draft` commands require a configured OpenAI-compatible endpoint because they send captured experience intake data to the configured model provider.

The project is currently developed and tested on Linux. The storage and configuration code is written with `pathlib` for cross-platform path handling, but Windows should be validated before claiming full Windows support.

Run tests:

```bash
uv run pytest -q
```

Run linting:

```bash
uv run ruff check .
uv run ruff format --check .
```

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).

Career Agent depends on third-party packages that are distributed under their own licenses. Before publishing packaged releases, Docker images, or binaries, generate a dependency license report and preserve any required third-party notices.

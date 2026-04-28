# Career Agent

Career Agent is a local-first Python TUI application for building structured career data, refining experience entries, and preparing for future job analysis and tailored document generation.

The project is designed around structured workflows and local-first AI assistance. Instead of assuming one large hosted model, Career Agent breaks work into smaller reviewable steps that can run against local or OpenAI-compatible model endpoints.

## Current Status

Implemented:
- Textual TUI dashboard
- editable User Preferences screen
- Career Profile overview screen
- Experience list, detail, add, edit, and delete screens
- Pydantic domain models for preferences, career profile, experience intake, source entries, and candidate bullets
- local JSON persistence with snapshot-on-overwrite and snapshot-on-delete behavior
- Typer/Rich CLI for scripting, debugging, and development workflows
- OpenAI-compatible LLM adapter for current experience question/draft commands

Planned next:
- migrate the Experience TUI from one source text field to append-only source entries
- add candidate bullet review controls in the TUI
- analyze new source entries against existing candidate bullets
- generate final experience entries only after active candidate bullets are reviewed
- expand Career Profile readiness and job analysis workflows

## Install And Run The TUI

The primary local interface is the Textual TUI.

Prerequisites:
- Git
- uv

Install Git:
- Linux: use your distribution package manager, such as `sudo apt install git` on Debian/Ubuntu.
- Windows: install Git for Windows from <https://git-scm.com/install/windows>, or use `winget install --id Git.Git -e --source winget`.

Install uv:

Linux/macOS:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Windows PowerShell:

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

## Using The TUI

From the dashboard:
- Press `p` or choose `Open Preferences` to review and update User Preferences.
- Press `c` or choose `Open Career Profile` to open the Career Profile overview.
- From Career Profile, choose `Manage Experience` to create, edit, view, or delete experience intake sessions.

Current Experience workflow:
- Add role facts such as employer, title, location, employment type, and dates.
- Add source notes or bullets for the role.
- Save the intake session locally.
- Review, edit, or delete unlocked intake sessions.

The Experience workflow is being refactored toward append-only source entries and reviewed candidate bullets. Until that TUI migration is complete, some lower-level workflow steps remain available through the CLI.

## CLI Reference

The CLI remains useful for scripting, debugging, and validating application workflows. See [docs/cli-reference.md](docs/cli-reference.md) for command examples.

## Design Direction

Career Agent is being built around:
- local-first structured data
- a primary Textual TUI interface
- modular domain / application / infrastructure separation
- AI workflows grounded in retained evidence and reviewed structured outputs
- reviewable workflow states before data becomes canonical
- Typer CLI support for development, scripting, and workflow validation

See [docs/architecture.md](docs/architecture.md) for the current layer map and file responsibilities.
See [docs/implementation-plan.md](docs/implementation-plan.md) for the living roadmap.
See [docs/security.md](docs/security.md) for the current security and privacy posture.

## Storage Model

Canonical data is stored locally as structured JSON for transparency, portability, and privacy-focused use.

Profile writes use snapshot-on-overwrite behavior so earlier states can be preserved during iterative editing. Experience intake files are also snapshotted before overwrite or delete operations.

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

## Configuration

Configuration is loaded from environment variables or a local `.env` file via `pydantic-settings`.

Create a local config file if needed:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Supported settings:
- `CAREER_AGENT_DATA_DIR`
- `CAREER_AGENT_LLM_BASE_URL`
- `CAREER_AGENT_LLM_API_KEY`
- `CAREER_AGENT_LLM_MODEL`
- `CAREER_AGENT_LLM_EXTRACTION_BASE_URL`
- `CAREER_AGENT_LLM_EXTRACTION_API_KEY`
- `CAREER_AGENT_LLM_EXTRACTION_MODEL`
- `CAREER_AGENT_LLM_EVAL_BASE_URL`
- `CAREER_AGENT_LLM_EVAL_API_KEY`
- `CAREER_AGENT_LLM_EVAL_MODEL`

If `CAREER_AGENT_DATA_DIR` is unset, the app creates a `.career-agent` directory under the current user's home directory using Python's `Path.home()`.

Example `.env` values:

```dotenv
# Portable user-home path
CAREER_AGENT_DATA_DIR=~/.career-agent

# Windows absolute path
CAREER_AGENT_DATA_DIR=C:/Users/ExampleUser/.career-agent
```

The `~/.career-agent` value is the recommended cross-platform option because the app expands `~` through Python's `Path.expanduser()`. Forward slashes are recommended in `.env` paths because Python handles them correctly on Windows and avoid backslash escaping confusion.

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

LLM configuration is optional for basic profile and preference workflows. Any workflow that calls a configured LLM endpoint sends the relevant local workflow data to that configured provider.

## Development

Install dependencies:

```bash
uv sync
```

Run tests:

```bash
uv run pytest -q
```

Run linting:

```bash
uv run ruff check .
uv run ruff format --check .
```

The project is currently developed and tested on Linux. The storage and configuration code is written with `pathlib` for cross-platform path handling, but Windows should be validated before claiming full Windows support.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).

Career Agent depends on third-party packages that are distributed under their own licenses. Before publishing packaged releases, Docker images, or binaries, generate a dependency license report and preserve any required third-party notices.

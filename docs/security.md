# Security And Privacy Posture

Career Agent is designed as a local-first application. Current profile and
preference workflows store data locally as JSON files. LLM-assisted workflows
are intended to be opt-in and user-configured.

This document describes the current security posture and intended privacy
expectations. It is not a formal third-party security audit.

## Current Behavior

- Career profile and preference data is stored under the configured local data directory.
- The default data directory is a `.career-agent` directory under the current user's home directory.
- No telemetry is implemented.
- No account system is implemented.
- No hosted application service is required to use the current CLI or TUI workflows.
- Current profile and preference workflows do not send career data to external services.
- OpenAI-compatible LLM adapter calls can be triggered through the `experience questions` and `experience draft` CLI commands.
- Optional LLM endpoint settings may be configured for LLM-assisted workflows, but they are not used by profile or preference workflows.
- No telemetry or background network calls are implemented.

## Future Networked Features

Current or future workflows may make outbound network calls only for explicitly
configured or user-triggered features, such as:

- fetching job postings from user-provided URLs
- calling a user-configured local or remote OpenAI-compatible LLM endpoint

Future networked features should be opt-in, configurable, and documented before
use. Career data should not be sent to external services unless the user has
enabled and triggered a workflow that requires it.

## Local Data

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

Profile and experience intake writes use snapshot-on-overwrite behavior. When an
existing JSON file is replaced, the previous version is copied into the relevant
`snapshots/` directory.

## Verification Commands

The following commands are useful for reviewing the current project state:

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
```

The following repository search can help identify newly introduced network-related code:

```bash
rg -n "httpx|requests|urllib|socket|websocket|openai|anthropic|api_key|token|secret" src tests
```

## Planned Security Checks

Potential future checks:

- `bandit` for Python static security linting
- `pip-audit` for known dependency vulnerability scanning
- `pytest-socket` to fail tests that make unexpected network calls
- GitHub Actions to run tests and security checks on Linux and Windows

These checks are useful guardrails, but they do not replace code review or a
formal security audit.

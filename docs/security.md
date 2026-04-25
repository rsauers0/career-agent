# Security And Privacy Posture

Career Agent is designed as a local-first application. Current profile and
preference workflows store data locally as JSON files and do not send career
data to external services.

This document describes the current security posture and intended privacy
expectations. It is not a formal third-party security audit.

## Current Behavior

- Career profile and preference data is stored under the configured local data directory.
- The default data directory is a `.career-agent` directory under the current user's home directory.
- No telemetry is implemented.
- No account system is implemented.
- No hosted application service is required to use the current CLI or TUI workflows.
- No LLM integration is currently active.
- No outbound application network calls are currently implemented in `src/`.

## Future Networked Features

Future workflows may make outbound network calls for explicitly configured or
user-triggered features, such as:

- fetching job postings from user-provided URLs
- calling a user-configured local or remote OpenAI-compatible LLM endpoint

Future networked features should be opt-in, configurable, and documented before
use. Career data should not be sent to external services unless the user has
enabled a workflow that requires it.

## Local Data

Current storage shape:

```text
<data_dir>/
  profile/
    user_preferences.json
    career_profile.json
  snapshots/
    profile/
```

Profile writes use snapshot-on-overwrite behavior. When an existing profile JSON
file is replaced, the previous version is copied into `snapshots/profile/`.

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

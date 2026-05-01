# Security And Privacy Posture

Career Agent is designed as a local-first application. The `v2-foundation`
branch is rebuilding the application foundation before reintroducing broader
TUI, workflow, and LLM-assisted features.

This document describes the current security posture and intended privacy
expectations. It is not a formal third-party security audit.

## Current Behavior

- The current v2 foundation CLI reads configuration and writes local JSON career data.
- The default data directory is a `.career-agent` directory under the current user's home directory.
- No telemetry is implemented.
- No account system is implemented.
- No hosted application service is required to use the current CLI.
- Current workflows do not send career data to external services.
- No workflow sends career data to an LLM endpoint unless an LLM base URL is configured.
- If no LLM base URL is configured, supported workflows use deterministic local behavior.
- The OpenAI-compatible LLM client is opt-in through configuration.
- LLM-backed generators validate structured output before workflow data is saved.
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

The v2 foundation branch will use local JSON persistence first. The intended
storage shape is:

```text
<data_dir>/
  user_preferences/
    user_preferences.json
  experience_roles/
    experience_roles.json
  role_sources/
    role_sources.json
  experience_facts/
    experience_facts.json
  source_analysis/
    analysis_runs.json
    clarification_questions.json
    clarification_messages.json
  snapshots/
    user_preferences/
    experience_roles/
    role_sources/
    experience_facts/
    source_analysis/
```

Snapshot-on-overwrite behavior is implemented for local JSON writes. When an
existing JSON file is replaced, the previous version is copied into the relevant
`snapshots/` directory.

Source Analysis data is workflow evidence. It may include clarification
questions and message history entered during analysis, so it should be treated
as career-sensitive local data.

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

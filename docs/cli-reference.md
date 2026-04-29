# CLI Reference

This page shows common `v2-foundation` CLI workflows.

For complete option details, use Typer's built-in help:

```bash
uv run career-agent --help
uv run career-agent preferences --help
uv run career-agent preferences save --help
```

## Health Check

Confirm the CLI is installed and configuration can be loaded:

```bash
uv run career-agent doctor
```

## User Preferences

Show saved user preferences:

```bash
uv run career-agent preferences show
```

If no preferences have been saved, the command reports that no preferences exist yet.

Save minimum required user preferences:

```bash
uv run career-agent preferences save \
  --full-name "John Doe" \
  --base-location "Aurora, IL 60504" \
  --work-arrangement remote \
  --work-authorization \
  --no-requires-work-sponsorship
```

Save preferences with optional search and commute details:

```bash
uv run career-agent preferences save \
  --full-name "John Doe" \
  --base-location "Aurora, IL 60504" \
  --time-zone "America/Chicago" \
  --target-job-title "Senior Systems Analyst" \
  --target-job-title "Platform Engineer" \
  --preferred-location "Chicago, IL" \
  --work-arrangement remote \
  --work-arrangement hybrid \
  --desired-salary-min 150000 \
  --salary-currency USD \
  --max-commute-distance 35 \
  --commute-distance-unit miles \
  --max-commute-time 45 \
  --work-authorization \
  --no-requires-work-sponsorship
```

## Configuration

Use `CAREER_AGENT_DATA_DIR` to direct local JSON data to a specific directory:

```bash
CAREER_AGENT_DATA_DIR=/tmp/career-agent-dev uv run career-agent preferences show
```

If `CAREER_AGENT_DATA_DIR` is unset, Career Agent stores data under:

```text
<home-directory>/.career-agent
```

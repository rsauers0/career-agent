# CLI Reference

This page shows common `v2-foundation` CLI workflows.

For complete option details, use Typer's built-in help:

```bash
uv run career-agent --help
uv run career-agent preferences --help
uv run career-agent preferences save --help
uv run career-agent roles --help
uv run career-agent roles save --help
uv run career-agent sources --help
uv run career-agent sources add --help
uv run career-agent bullets --help
uv run career-agent bullets add --help
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

## Experience Roles

List saved experience roles:

```bash
uv run career-agent roles list
```

Show one saved experience role:

```bash
uv run career-agent roles show <role-id>
```

Save a past experience role:

```bash
uv run career-agent roles save \
  --employer-name "Acme Analytics" \
  --job-title "Senior Systems Analyst" \
  --start-date "05/2021" \
  --end-date "06/2024" \
  --location "Chicago, IL" \
  --employment-type full-time \
  --role-focus "Led internal reporting and automation improvements."
```

Save a current experience role:

```bash
uv run career-agent roles save \
  --employer-name "Current Co" \
  --job-title "Platform Engineer" \
  --start-date "02/2024" \
  --current \
  --role-focus "Focused on platform reliability, automation, and team enablement."
```

Update an existing role by passing its id:

```bash
uv run career-agent roles save \
  --role-id "<role-id>" \
  --employer-name "Acme Analytics" \
  --job-title "Senior Systems Analyst" \
  --start-date "05/2021" \
  --end-date "07/2025" \
  --status review_required
```

Delete one saved experience role:

```bash
uv run career-agent roles delete <role-id>
```

## Role Sources

List all saved role sources:

```bash
uv run career-agent sources list
```

List sources for one role:

```bash
uv run career-agent sources list --role-id <role-id>
```

Show one saved source entry:

```bash
uv run career-agent sources show <source-id>
```

Add source material directly from the command line:

```bash
uv run career-agent sources add \
  --role-id <role-id> \
  --source-text "- Led a reporting automation project."
```

Add multiline source material from a text file:

```bash
uv run career-agent sources add \
  --role-id <role-id> \
  --from-file source-notes.txt
```

`sources add` requires exactly one source input: either `--source-text` or `--from-file`.

Delete one saved source entry:

```bash
uv run career-agent sources delete <source-id>
```

## Experience Bullets

List all saved experience bullets:

```bash
uv run career-agent bullets list
```

List bullets for one role:

```bash
uv run career-agent bullets list --role-id <role-id>
```

Show one saved bullet:

```bash
uv run career-agent bullets show <bullet-id>
```

Add a draft canonical bullet:

```bash
uv run career-agent bullets add \
  --role-id <role-id> \
  --text "Automated reporting workflows, reducing manual reconciliation time."
```

Add a draft bullet with source traceability:

```bash
uv run career-agent bullets add \
  --role-id <role-id> \
  --text "Automated reporting workflows, reducing manual reconciliation time." \
  --source-id <source-id>
```

Delete one saved bullet:

```bash
uv run career-agent bullets delete <bullet-id>
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

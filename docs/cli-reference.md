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
uv run career-agent facts --help
uv run career-agent facts add --help
uv run career-agent facts events --help
uv run career-agent facts revise --help
uv run career-agent source-analysis --help
uv run career-agent source-analysis runs start --help
uv run career-agent source-analysis questions add --help
uv run career-agent source-analysis messages add --help
uv run career-agent experience-workflow --help
uv run career-agent experience-workflow analyze-sources --help
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

## Experience Facts

List all saved experience facts:

```bash
uv run career-agent facts list
```

List facts for one role:

```bash
uv run career-agent facts list --role-id <role-id>
```

Show one saved fact:

```bash
uv run career-agent facts show <fact-id>
```

Add a draft canonical fact:

```bash
uv run career-agent facts add \
  --role-id <role-id> \
  --text "Automated reporting workflows, reducing manual reconciliation time."
```

Add a draft fact with source traceability:

```bash
uv run career-agent facts add \
  --role-id <role-id> \
  --text "Automated reporting workflows, reducing manual reconciliation time." \
  --source-id <source-id>
```

Add a draft fact with richer evidence and reference lists:

```bash
uv run career-agent facts add \
  --role-id <role-id> \
  --text "Automated reporting workflows, reducing manual reconciliation time." \
  --source-id <source-id> \
  --question-id <question-id> \
  --message-id <message-id> \
  --detail "Reduced recurring manual reconciliation effort." \
  --system "Power Platform" \
  --skill "Power Automate" \
  --function "workflow automation"
```

Add a revised fact that supersedes an earlier fact:

```bash
uv run career-agent facts add \
  --role-id <role-id> \
  --text "Automated monthly reporting workflows, reducing manual reconciliation time." \
  --supersedes-fact-id <fact-id>
```

Manage fact lifecycle:

```bash
uv run career-agent facts activate <fact-id> --actor user
uv run career-agent facts needs-clarification <fact-id> \
  --actor llm \
  --reason "Metric needs supporting evidence." \
  --source-message-id <message-id>
uv run career-agent facts draft <fact-id> --actor user
uv run career-agent facts reject <fact-id> --actor user --reason "Unsupported scope expansion."
uv run career-agent facts archive <fact-id> --actor user
uv run career-agent facts revise <fact-id> \
  --text "Revised grounded fact text." \
  --actor user \
  --source-message-id <message-id>
```

The `--actor` option is CLI/dev workflow metadata. It defaults to `user` and
accepts `user`, `llm`, or `system`. Later TUI or web flows should set actor from
the workflow context rather than exposing it as an end-user control.

List fact change events:

```bash
uv run career-agent facts events
uv run career-agent facts events --fact-id <fact-id>
uv run career-agent facts events --role-id <role-id>
```

Delete one saved fact:

```bash
uv run career-agent facts delete <fact-id>
```

## Source Analysis

Start a source analysis run for one role and one or more source entries:

```bash
uv run career-agent source-analysis runs start \
  --role-id <role-id> \
  --source-id <source-id>
```

Only one active source analysis run can exist for a single role at a time. Complete
or archive the active run before starting another run for that same role.

List source analysis runs:

```bash
uv run career-agent source-analysis runs list
```

List source analysis runs for one role:

```bash
uv run career-agent source-analysis runs list --role-id <role-id>
```

Add a clarification question:

```bash
uv run career-agent source-analysis questions add \
  --run-id <run-id> \
  --text "What measurable impact did this work have?" \
  --relevant-source-id <source-id>
```

Add a clarification question from a UTF-8 text file:

```bash
uv run career-agent source-analysis questions add \
  --run-id <run-id> \
  --from-file question.txt
```

List clarification questions for a run:

```bash
uv run career-agent source-analysis questions list --run-id <run-id>
```

Resolve or skip a clarification question:

```bash
uv run career-agent source-analysis questions resolve <question-id>
uv run career-agent source-analysis questions skip <question-id>
```

Append one clarification message:

```bash
uv run career-agent source-analysis messages add \
  --question-id <question-id> \
  --author user \
  --text "It reduced weekly reporting time from 6 hours to 2."
```

Append one clarification message from a UTF-8 text file:

```bash
uv run career-agent source-analysis messages add \
  --question-id <question-id> \
  --author user \
  --from-file answer.txt
```

List clarification messages for a question:

```bash
uv run career-agent source-analysis messages list --question-id <question-id>
```

`questions add` and `messages add` require exactly one text input: either `--text` or `--from-file`.

Clarification messages are appended one message at a time. Adding a message does
not resolve a question automatically; use `questions resolve` or
`questions skip` for explicit status transitions.

## Experience Workflow

Start source analysis for one experience role's unanalyzed sources:

```bash
uv run career-agent experience-workflow analyze-sources --role-id <role-id>
```

This command creates clarification questions through the source question
generator boundary, then starts a Source Analysis run after the generated
questions are valid. It only includes role sources with `not_analyzed` status and
does not mark those sources as analyzed.

If `CAREER_AGENT_LLM_BASE_URL` is configured, this command uses the LLM-backed
source question generator. If it is unset, it uses deterministic local question
generation. The command prints the selected question generator before analysis
starts.

## Configuration

Use `CAREER_AGENT_DATA_DIR` to direct local JSON data to a specific directory:

```bash
CAREER_AGENT_DATA_DIR=/tmp/career-agent-dev uv run career-agent preferences show
```

If `CAREER_AGENT_DATA_DIR` is unset, Career Agent stores data under:

```text
<home-directory>/.career-agent
```

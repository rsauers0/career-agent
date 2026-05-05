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
uv run career-agent constraints --help
uv run career-agent constraints add --help
uv run career-agent constraints applicable --help
uv run career-agent fact-review --help
uv run career-agent fact-review threads start --help
uv run career-agent fact-review messages add --help
uv run career-agent fact-review actions add --help
uv run career-agent fact-review actions apply --help
uv run career-agent source-analysis --help
uv run career-agent source-analysis runs start --help
uv run career-agent source-analysis questions add --help
uv run career-agent source-analysis messages add --help
uv run career-agent source-analysis findings --help
uv run career-agent source-analysis findings add --help
uv run career-agent experience-workflow --help
uv run career-agent experience-workflow analyze-sources --help
uv run career-agent experience-workflow generate-findings --help
uv run career-agent experience-workflow apply-findings --help
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

## Scoped Constraints

Add a global constraint:

```bash
uv run career-agent constraints add \
  --scope-type global \
  --constraint-type hard_rule \
  --rule-text "Do not use em dashes."
```

Add a role or fact constraint:

```bash
uv run career-agent constraints add \
  --scope-type role \
  --scope-id <role-id> \
  --constraint-type hard_rule \
  --rule-text "Do not describe this role as enterprise-level."

uv run career-agent constraints add \
  --scope-type fact \
  --scope-id <fact-id> \
  --constraint-type preference \
  --rule-text "Prefer generic technology support terminology."
```

Initial scope types are `global`, `role`, and `fact`. `global` constraints must
not include `--scope-id`; `role` and `fact` constraints require it. Constraint
types are `hard_rule` and `preference`.

List constraints:

```bash
uv run career-agent constraints list
uv run career-agent constraints list --scope-type role --scope-id <role-id>
uv run career-agent constraints list --status active
```

List active constraints that apply to a workflow context:

```bash
uv run career-agent constraints applicable --role-id <role-id>
uv run career-agent constraints applicable --fact-id <fact-id>
```

Activate, reject, or archive constraints:

```bash
uv run career-agent constraints activate <constraint-id>
uv run career-agent constraints reject <constraint-id>
uv run career-agent constraints archive <constraint-id>
```

## Fact Review

Start a fact review thread for an existing fact:

```bash
uv run career-agent fact-review threads start --fact-id <fact-id>
```

Only one open review thread can exist for a fact at a time. Resolve or archive
the open thread before starting another review thread for the same fact.

List review threads:

```bash
uv run career-agent fact-review threads list
uv run career-agent fact-review threads list --fact-id <fact-id>
uv run career-agent fact-review threads list --role-id <role-id>
```

Append one review message:

```bash
uv run career-agent fact-review messages add \
  --thread-id <thread-id> \
  --author user \
  --text "Please split this into two facts." \
  --recommended-action split_fact
```

Append one review message from a UTF-8 text file:

```bash
uv run career-agent fact-review messages add \
  --thread-id <thread-id> \
  --author user \
  --from-file review-note.txt
```

List review messages:

```bash
uv run career-agent fact-review messages list --thread-id <thread-id>
```

Add a structured review action:

```bash
uv run career-agent fact-review actions add \
  --thread-id <thread-id> \
  --action-type revise_fact \
  --rationale "User clarified the wording." \
  --source-message-id <review-message-id> \
  --revised-text "Revised grounded fact text."
```

The first action types are `activate_fact`, `reject_fact`, `revise_fact`, and
`add_evidence`. `revise_fact` requires `--revised-text`. `add_evidence` requires
at least one `--source-id`, `--question-id`, or `--message-id`.

List and apply review actions:

```bash
uv run career-agent fact-review actions list --thread-id <thread-id>
uv run career-agent fact-review actions apply <action-id>
uv run career-agent fact-review actions apply <action-id> --actor llm
```

Reject or archive review actions:

```bash
uv run career-agent fact-review actions reject <action-id>
uv run career-agent fact-review actions archive <action-id>
```

Resolve or archive a review thread:

```bash
uv run career-agent fact-review threads resolve <thread-id>
uv run career-agent fact-review threads archive <thread-id>
```

Fact review messages are append-only workflow artifacts. Recommended actions on
messages are metadata. Structured review actions are separate records that can be
applied through deterministic Experience Fact services. Applying an action
records the resulting `applied_fact_id` and any canonical mutation is captured in
Fact Change Events.

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

Add a structured source finding:

```bash
uv run career-agent source-analysis findings add \
  --run-id <run-id> \
  --source-id <source-id> \
  --finding-type new_fact \
  --proposed-fact-text "Normalized draft fact candidate." \
  --rationale "Why the source appears to support this finding."
```

Add a finding that compares a source to an existing fact:

```bash
uv run career-agent source-analysis findings add \
  --run-id <run-id> \
  --source-id <source-id> \
  --finding-type supports_fact \
  --fact-id <fact-id> \
  --rationale "The source describes the same work as the existing fact."
```

List and transition source findings:

```bash
uv run career-agent source-analysis findings list --run-id <run-id>
uv run career-agent source-analysis findings accept <finding-id>
uv run career-agent source-analysis findings reject <finding-id>
uv run career-agent source-analysis findings archive <finding-id>
```

Source findings are workflow artifacts. Accepting a finding records review
approval but does not directly create or revise an experience fact. Canonical
fact changes are applied later through deterministic fact workflows.

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

Generate source findings for a source analysis run:

```bash
uv run career-agent experience-workflow generate-findings --run-id <run-id>
```

Finding generation requires all clarification questions for the run to be
resolved or skipped. Runs with zero questions are allowed. If any source findings
already exist for the run, the command exits instead of creating a second
finding batch.

The deterministic finding generator is only a local validation harness and emits
placeholder `unclear` findings. If `CAREER_AGENT_LLM_BASE_URL` or
`CAREER_AGENT_LLM_EXTRACTION_BASE_URL` is configured, this command uses the
LLM-backed extraction generator and prints the selected finding generator before
generation starts.

Apply accepted source findings through deterministic fact workflows:

```bash
uv run career-agent experience-workflow apply-findings --run-id <run-id>
```

Only findings in `accepted` status are processed. Applied findings move to
`applied` status and record `applied_fact_id`, which makes the command safe to
run again without duplicating draft facts.

Application behavior is intentionally conservative:

- `new_fact` creates a draft experience fact.
- `revises_fact` revises the referenced fact through `ExperienceFactService`.
  Active facts become draft revisions; draft and needs-clarification facts may
  be revised in place according to fact lifecycle rules.
- `supports_fact` appends source/question/message evidence through an explicit
  fact service method and records a fact change event when new evidence is
  added.
- `contradicts_fact`, `duplicates_fact`, `unclear`, and `unrelated` remain
  accepted analysis artifacts and are not automatically applied.

## Configuration

Use `CAREER_AGENT_DATA_DIR` to direct local JSON data to a specific directory:

```bash
CAREER_AGENT_DATA_DIR=/tmp/career-agent-dev uv run career-agent preferences show
```

If `CAREER_AGENT_DATA_DIR` is unset, Career Agent stores data under:

```text
<home-directory>/.career-agent
```

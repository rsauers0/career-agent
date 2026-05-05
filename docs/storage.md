# Storage

Career Agent uses local JSON persistence in the `v2-foundation` branch.

The storage root is controlled by:

```text
CAREER_AGENT_DATA_DIR
```

If unset, the default is:

```text
<home-directory>/.career-agent
```

## Current Storage Shape

User Preferences are stored as:

```text
<data_dir>/
  user_preferences/
    user_preferences.json
  snapshots/
    user_preferences/
      <timestamp>-user_preferences.json
```

Experience Roles are stored as:

```text
<data_dir>/
  experience_roles/
    experience_roles.json
  snapshots/
    experience_roles/
      <timestamp>-experience_roles.json
```

Role Sources are stored as:

```text
<data_dir>/
  role_sources/
    role_sources.json
  snapshots/
    role_sources/
      <timestamp>-role_sources.json
```

Experience Facts are stored as:

```text
<data_dir>/
  experience_facts/
    experience_facts.json
    fact_change_events.json
  snapshots/
    experience_facts/
      <timestamp>-experience_facts.json
      <timestamp>-fact_change_events.json
```

Experience fact records include the fact text, optional second-level details,
append-only evidence ids for sources/questions/messages, grounded reference
lists for systems/skills/functions, revision links, lifecycle status, and
timestamps.

Fact change events record semantic history for experience facts, including the
event type, actor, summary, workflow message ids, status transition, related fact
id, and timestamp.

Fact Review artifacts are stored as table-like JSON files:

```text
<data_dir>/
  fact_review/
    fact_review_threads.json
    fact_review_messages.json
    fact_review_actions.json
  snapshots/
    fact_review/
      <timestamp>-fact_review_threads.json
      <timestamp>-fact_review_messages.json
      <timestamp>-fact_review_actions.json
```

Fact review threads and messages preserve collaborative review history for draft
and revised facts. Review actions are structured proposals from that history.
Applying a review action calls deterministic Experience Fact services and records
the returned `applied_fact_id`; canonical mutations remain in experience facts
and fact change events.

Source Analysis artifacts are stored as table-like JSON files:

```text
<data_dir>/
  source_analysis/
    analysis_runs.json
    clarification_questions.json
    clarification_messages.json
    source_findings.json
  snapshots/
    source_analysis/
      <timestamp>-analysis_runs.json
      <timestamp>-clarification_questions.json
      <timestamp>-clarification_messages.json
      <timestamp>-source_findings.json
```

Source findings are structured analysis notes about what a source appears to
mean. They can record support, revision, contradiction, duplication, possible new
fact, unclear, or unrelated findings. They are workflow artifacts, not canonical
fact support by themselves. Applied findings store `applied_fact_id` so the
workflow can trace which fact was created or updated and avoid duplicate
application.

## Snapshot Behavior

When a managed JSON file already exists, saving creates a snapshot before overwriting the current file.

Snapshots preserve the previous JSON file for traceability during iterative editing.

The current repository behavior is:

1. Load existing data if present.
2. Before overwrite, copy the existing JSON file to that component's snapshot directory.
3. Write the new JSON file.

Repository code owns this behavior. CLI commands and services do not directly manage file paths or snapshots.

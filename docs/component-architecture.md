# Component Architecture

Career Agent's `v2-foundation` branch is organized around small workflow components.

Each component owns one concept and follows the same implementation shape:

```text
model
  -> repository
  -> service
  -> CLI
```

This keeps data definitions, storage, workflow rules, and command-line interaction separated.

## Layer Responsibilities

### Model

Models define what the data is.

They use Pydantic for validation and JSON serialization. Examples include required fields, enum values, date rules, and timestamp requirements.

### Repository

Repositories define how data is saved and loaded.

Current repositories use local JSON files under `CAREER_AGENT_DATA_DIR`. They also own snapshot-on-overwrite behavior so previous JSON files are retained before updates.

Repositories should not own workflow rules that require coordinating multiple components.

### Service

Services define what the application can do with the data.

This is where workflow rules belong. For example, `RoleSourceService` checks that an experience role exists before source material can be added for that role.

### CLI

The CLI is an interface adapter.

It parses command-line input, calls services, and renders output. It should not own storage details or business rules.

Future interfaces such as a TUI or FastAPI API should call the same services rather than duplicating workflow logic.

## Current Components

### User Preferences

Purpose: stores user-specific preferences used by future search and matching workflows.

Current files:

```text
src/career_agent/user_preferences/
  models.py
  repository.py
  service.py
```

Current CLI group:

```bash
career-agent preferences
```

Examples of owned data:

- full name
- base location
- preferred work arrangements
- target job titles
- preferred locations
- salary and commute preferences
- work authorization and sponsorship flags

### Experience Roles

Purpose: stores structured facts for jobs or positions in the user's career history.

Current files:

```text
src/career_agent/experience_roles/
  models.py
  repository.py
  service.py
```

Current CLI group:

```bash
career-agent roles
```

Examples of owned data:

- employer name
- job title
- location
- employment type
- role focus
- start and end month/year
- current role flag
- role status

Experience roles intentionally do not own source material. They are the structured role container. `role_focus` is user-authored context for the role's primary focus; it is not intended to be a polished resume summary.

### Role Sources

Purpose: stores submitted source material linked to an experience role.

Current files:

```text
src/career_agent/role_sources/
  models.py
  repository.py
  service.py
```

Current CLI group:

```bash
career-agent sources
```

Examples of owned data:

- role id
- submitted source text
- source analysis status
- creation timestamp

Role sources preserve submitted text exactly for traceability. They are separate from experience roles so the application can retain source evidence without mixing raw input into structured role facts.

### Experience Bullets

Purpose: stores durable resume-style bullets linked to an experience role.

Current files:

```text
src/career_agent/experience_bullets/
  models.py
  repository.py
  service.py
```

Current CLI group:

```bash
career-agent bullets
```

Examples of owned data:

- role id
- source ids used to support or derive the bullet
- bullet text
- lifecycle status
- creation and update timestamps

Experience bullets are canonical career data. Draft bullets are canonical bullet records that are not active yet. LLM-generated candidates that fail evals should be retained later as analysis artifacts, not as canonical bullets. Role-level review remains on Experience Roles. Bullets do not currently include tags or inferred classifications.

### Source Analysis

Purpose: stores workflow artifacts created while analyzing submitted role source material.

Current files:

```text
src/career_agent/source_analysis/
  models.py
  repository.py
  service.py
```

Current CLI group:

```bash
career-agent source-analysis
```

Examples of owned data:

- source analysis runs linked to an experience role
- source ids included in each analysis run
- clarification questions generated during analysis
- clarification message threads attached to a question
- question and analysis lifecycle statuses
- table-like JSON files for runs, questions, and messages

Source Analysis is not canonical career data. It is workflow evidence that supports future LLM-guided clarification, evals, and bullet proposal generation. Canonical data changes should still be applied through deterministic services.

Clarification messages are append-only conversation turns. They do not resolve questions by themselves; question closure requires an explicit `resolve` or `skip` transition.

Only one active Source Analysis run may exist for a single experience role at a time. Separate roles may have active analysis runs simultaneously.

### Experience Workflow

Purpose: orchestrates experience-related workflow steps across existing components.

Current files:

```text
src/career_agent/experience_workflow/
  question_generator.py
  service.py
```

Current CLI group:

```bash
career-agent experience-workflow
```

Examples of coordinated behavior:

- select role sources with `not_analyzed` status
- start Source Analysis runs through `SourceAnalysisService`
- generate structured clarification question proposals
- save generated question proposals through `SourceAnalysisService`

Experience Workflow does not own persistence. It coordinates component services and should not write directly to JSON files.

Question generation is behind a small `SourceQuestionGenerator` protocol. The current implementation is deterministic and used for dev validation; a future LLM generator should plug into the same structured proposal contract.

`LLMSourceQuestionGenerator` is available as the first LLM-backed implementation of that protocol. It uses `LLMClient`, expects JSON output, and validates that generated questions match the `GeneratedSourceQuestion` contract before returning them to the workflow.

### LLM Boundary

Purpose: defines a provider-neutral completion boundary for future AI features.

Current files:

```text
src/career_agent/llm/
  models.py
  client.py
```

Current CLI group:

```text
not applicable
```

Examples of owned data:

- `LLMRequest`
- `LLMResponse`
- `LLMClient` protocol
- `FakeLLMClient` for deterministic tests and dev validation
- `OpenAICompatibleLLMClient` for opt-in chat completions integrations

The LLM boundary is synchronous. The OpenAI-compatible client exists, but it is not wired into configuration or default workflows yet.

## Current Data Flow

```text
User runs CLI command
  -> CLI builds service
  -> service applies workflow rule
  -> repository loads or writes JSON
  -> Pydantic model validates data
```

Example: adding role source material.

```text
career-agent sources add --role-id role-1 --from-file notes.txt
  -> RoleSourceService.add_source()
  -> ExperienceRoleRepository.get("role-1")
  -> RoleSourceEntry(...)
  -> RoleSourceRepository.save(...)
  -> role_sources/role_sources.json
```

## Design Direction

The current foundation is intentionally CLI-first.

The next layers should follow the same rule:

```text
CLI / TUI / FastAPI / LLM workflow
        -> service
        -> repository
        -> local JSON files
```

LLM behavior should produce structured proposals. Services should validate and apply those proposals deterministically.

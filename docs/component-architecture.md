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

### Experience Facts

Purpose: stores durable normalized experience facts linked to an experience role.

Current files:

```text
src/career_agent/experience_facts/
  models.py
  repository.py
  service.py
```

Current CLI group:

```bash
career-agent facts
```

Examples of owned data:

- role id
- source, clarification question, and clarification message ids used to support or derive the fact
- fact text
- optional second-level details
- referenced systems, skills, and functions
- superseded/supersedes fact ids for revisions
- lifecycle status
- creation and update timestamps

Experience facts are the current canonical career data component. Draft facts are canonical fact records that are not active yet. LLM-generated candidates that fail evals should be retained later as analysis artifacts, not as canonical facts. Role-level review remains on Experience Roles. Fact records may carry lightweight reference lists for systems, skills, and functions when those references are grounded in the fact evidence; broad inferred classifications should still wait for later derived-evidence workflows.

Experience facts should be distinguished from persuasive resume bullets. Experience facts should document duties, functions, achievements, scope, systems, tools, and metrics in plain professional language. They are source-of-truth career evidence for later job-fit analysis, resumes, and cover letters; they should not bridge gaps, inflate scope, or use creative resume wording.

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

Source Analysis is not canonical career data. It is workflow evidence that supports future LLM-guided clarification, evals, and experience fact proposal generation. Canonical data changes should still be applied through deterministic services.

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
- generate structured clarification question proposals
- start Source Analysis runs through `SourceAnalysisService`
- save generated question proposals through `SourceAnalysisService`

Experience Workflow does not own persistence. It coordinates component services and should not write directly to JSON files.

Question generation is behind a small `SourceQuestionGenerator` protocol. The deterministic generator is used for local dev validation and fallback behavior. The LLM-backed generator plugs into the same structured proposal contract.

`LLMSourceQuestionGenerator` is available as the first LLM-backed implementation of that protocol. It uses `LLMClient`, expects JSON output, and validates that generated questions match the `GeneratedSourceQuestion` contract before returning them to the workflow.

Experience Workflow checks for an existing active run before question generation. It then generates and validates question proposals before creating a Source Analysis run, so malformed LLM output does not leave behind an active run with no usable questions.

Factory wiring selects the deterministic generator when no LLM base URL is configured. If an LLM base URL is configured, it selects the LLM-backed generator and requires an LLM model.

### LLM Boundary

Purpose: defines a provider-neutral completion boundary for AI-assisted workflows.

Current files:

```text
src/career_agent/llm/
  models.py
  client.py
  openai_compatible_client.py
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

The LLM boundary is synchronous. The OpenAI-compatible client is opt-in through configuration; deterministic local behavior remains the fallback when no LLM base URL is configured.

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

### Grounded Experience Evidence

The next experience workflow layer should normalize analyzed source material into grounded experience facts before any resume-specific writing occurs.

Expected flow:

```text
raw role source material
  -> source analysis questions and messages
  -> experience fact proposals
  -> user/assistant revision thread
  -> approved experience facts
  -> fact-level reference lists for skills, systems, tools, technologies, and functions
  -> derived cross-role evidence indexes and capabilities
  -> job-fit analysis and tailored documents
```

Experience fact proposals should be grounded in referenced material. Each proposed fact should point back to supporting source ids, question ids, and message ids. Those ids should be append-only evidence references; later revisions can add additional support, but should not erase the original trail. Missing evidence should produce either a missing-evidence note or another clarification question, not an invented fact.

This is still the data normalization phase. The goal is a detailed, reusable accounting of the user's actual duties, functions, achievements, systems, tools, scope, and metrics. Persuasive tailoring belongs to later job-specific document generation.

Writing standards for normalized facts:

- prefer generic, reusable terminology over persuasive resume language
- document role functions, duties, achievements, scope, tools, systems, and metrics
- preserve exact metrics and technologies only when supported by evidence
- compile systems, skills, and functions as grounded reference lists, not broad inferred classifications
- avoid artificial scope expansion, inflated verbs, and target-job tailoring
- keep similar-but-not-proven-same work items separate

Merge behavior should be conservative. Similar wording, similar metrics, or shared tools are not enough to combine facts. A generated fact should merge evidence only when it is clearly the same work, same project or process, same metric context, and same outcome.

Fact history should stay separate from the canonical fact record. Messages capture the conversational why; snapshots provide file-level backup; a lightweight `FactChangeEvent` table should capture semantic system changes such as created, revised, accepted, archived, or constraint-created. Change events should use `actor` for the responsible party and link back to source message ids when a user or assistant exchange caused the change.

### Scoped Constraints

User corrections and hard preferences should become durable constraints when appropriate. Constraints may be global writing preferences or scoped evidence rules tied to a role, source, analysis run, proposal, fact, project, or message.

Examples:

- global: never use em dashes
- global: avoid specific disliked words
- role-scoped: do not describe this role as enterprise-level without explicit evidence
- proposal-scoped: do not say the user deployed the system; describe the involvement as support oversight
- project-scoped: do not merge two similarly measured automations unless they are confirmed to be the same project

The first constraint scope types should be `global` and `role`; additional scopes such as cover letter, resume, proposal, fact, and project can be added when those components exist. Constraints should be represented as separate rule records rather than a single record containing multiple unrelated rules. A single user response may yield multiple constraints, all linked back to the source message for traceability.

Constraints should distinguish `preference` from `hard_rule`. The LLM may propose severity during constraint extraction, but deterministic workflow and user approval should decide what becomes active.

### LLM Orchestration Direction

Future LLM behavior should be orchestrated as small structured steps, not one large prompt that performs every task. Each model call should have a narrow responsibility and a validated output contract. Application services remain responsible for persistence and state transitions.

Candidate orchestration steps:

- classify a user response as answer, correction, preference, constraint, rejection, or question
- extract scoped constraints from user corrections and preferences
- propose or revise normalized experience facts
- check proposed facts for drift beyond cited evidence
- check whether similar facts are safe to merge or must remain separate
- plan follow-up clarification questions when evidence is missing
- recommend explicit status transitions, while deterministic services apply them

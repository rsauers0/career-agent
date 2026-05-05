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

## Shared Workflow Boundaries

### Workflow Approval

Purpose: provides a replaceable approval/eval boundary for workflow decisions
that should not be applied directly from an LLM proposal.

Current files:

```text
src/career_agent/
  workflow_approval.py
```

The current implementation has one approval request type, `fact_activation`,
and a `DummyWorkflowApprovalService` that always approves for local workflow
validation. This is intentionally small and replaceable. A future approval
router can route requests by approval type and persist eval artifacts without
changing the deterministic fact mutation services.

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

Fact-related source additions should still remain role-owned source evidence. Raw role sources do not store semantic source-to-fact conclusions. Structured Source Analysis findings can later record whether a source appears to support, revise, contradict, duplicate, or create a fact. Canonical fact support is recorded only when an `ExperienceFact` references source ids through its evidence fields.

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
- semantic fact change events stored in `fact_change_events.json`

Experience facts are the current canonical career data component. Draft facts are canonical fact records that are visible for review but not active yet. Proposed facts should be represented as `ExperienceFact` records in `draft` status, not as a parallel proposal component. LLM-generated candidates that fail evals should be retained later as analysis artifacts, not as canonical facts. Role-level review remains on Experience Roles. Fact records may carry lightweight reference lists for systems, skills, and functions when those references are grounded in the fact evidence; broad inferred classifications should still wait for later derived-evidence workflows.

Experience fact lifecycle statuses should be:

- `draft`: proposed or user-entered fact visible for review
- `needs_clarification`: evidence is insufficient or conflicting
- `active`: accepted source-of-truth fact
- `rejected`: reviewed and not accepted
- `superseded`: replaced by a newer fact
- `archived`: removed from active use without necessarily being wrong

The service should enforce lifecycle transitions strictly:

- `draft` -> `active`
- `draft` -> `needs_clarification`
- `draft` -> `rejected`
- `needs_clarification` -> `draft`
- `needs_clarification` -> `rejected`
- `active` -> `superseded`
- `active` -> `archived`
- `rejected` -> `archived`
- `superseded` -> `archived`

Draft and needs-clarification facts can be edited in place. Active facts should not be edited in place; revisions should create a new draft fact that references the active fact through `supersedes_fact_id`. When that draft revision becomes active, the prior active fact should move to `superseded` and reference the new fact through `superseded_by_fact_id`. Rejected, superseded, and archived facts should not be revised in place.

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
- structured source findings produced by analysis
- question and analysis lifecycle statuses
- table-like JSON files for runs, questions, messages, and findings

Source Analysis is not canonical career data. It is workflow evidence that supports future LLM-guided clarification, evals, source findings, and draft experience fact generation. Canonical data changes should still be applied through deterministic services.

Clarification messages are append-only conversation turns. They do not resolve questions by themselves; question closure requires an explicit `resolve` or `skip` transition.

Source findings are structured analysis notes. They can indicate that a source appears to support, revise, contradict, duplicate, create, be unclear, or be unrelated to a fact. Accepting a finding records review approval but does not directly mutate canonical facts. The Experience Workflow applies accepted findings through deterministic Experience Fact services and records `applied_fact_id` when a finding creates or updates a fact.

Only one active Source Analysis run may exist for a single experience role at a time. Separate roles may have active analysis runs simultaneously.

Analysis run completion is an explicit lifecycle transition. A run can move from
`active` to `completed` only when all clarification questions are resolved or
skipped and no accepted source findings remain unapplied. Completing the run
marks each included `RoleSourceEntry` as `analyzed`, which allows future
`experience-workflow analyze-sources` calls to focus only on newly added source
material.

Analysis runs may also be archived. Archiving an active run closes the run
without marking its sources analyzed. Archiving a completed run leaves source
status unchanged.

### Scoped Constraints

Purpose: stores durable user rules and preferences that constrain later analysis,
fact normalization, and document generation workflows.

Current files:

```text
src/career_agent/scoped_constraints/
  models.py
  repository.py
  service.py
```

Current CLI group:

```bash
career-agent constraints
```

Examples of owned data:

- global, role, and fact scoped constraints
- constraint type: hard rule or preference
- proposed, active, rejected, and archived lifecycle statuses
- workflow message ids that explain or support the constraint

Scoped Constraints are shared workflow guardrails. They are not owned by Fact
Review, resumes, cover letters, or any single downstream feature. Fact Review
may propose constraints, but activated constraints live in this shared component
so future workflows can ask for the active constraints that apply to a role or
fact context.

`global` constraints do not have `scope_id`. `role` and `fact` constraints must
have `scope_id`, and services validate that the referenced role or fact exists.
The first implementation intentionally avoids future scope types such as resume
or cover letter until those persistent components exist.

### Fact Review

Purpose: stores collaborative review artifacts for draft or revised experience facts.

Current files:

```text
src/career_agent/fact_review/
  action_generator.py
  models.py
  repository.py
  service.py
```

Current CLI group:

```bash
career-agent fact-review
```

Examples of owned data:

- fact review threads linked to one experience fact and role
- append-only review messages
- message authors: assistant, user, or system
- optional recommended action metadata
- structured review actions proposed from a thread
- thread lifecycle status: open, resolved, archived
- action lifecycle status: proposed, applied, rejected, archived

Fact Review is workflow evidence, not canonical career data. It preserves the
user/assistant collaboration history around draft facts without allowing review
messages to mutate canonical fact text. Recommended actions such as
`revise_fact`, `add_evidence`, `split_fact`, `reject_fact`, `activate_fact`, and
`propose_constraint` remain message metadata. Structured review actions can apply
the first deterministic action types: `revise_fact`, `add_evidence`,
`reject_fact`, `activate_fact`, and `propose_constraint`. Fact actions call
Experience Fact services and record the returned `applied_fact_id`; Fact Change
Events still record canonical fact mutations. Constraint actions call Scoped
Constraint services, create proposed constraints, and record
`applied_constraint_id` without activating the constraint.

Fact Review action generation uses a `FactReviewActionGenerator` boundary.
Generated actions are proposal models that become saved `FactReviewAction` rows
only after the service validates the review thread, target fact, owning role,
active applicable constraints, existing action state, and source review message
references. Generation is blocked while any proposed action already exists for a
thread. The current deterministic generator is for local workflow validation and
only proposes actions from explicit message recommendation metadata.

LLM-backed Fact Review action generation should use the default conversational
LLM configuration (`CAREER_AGENT_LLM_MODEL`) instead of extraction-specific
configuration. The LLM generator uses the same proposal boundary: strict JSON
output is parsed into `GeneratedFactReviewAction` values, zero actions are valid,
multiple actions are valid when supported, and every action must reference
review message ids from the thread. It operates on a small review context for
one fact and should stay in fact-normalization mode, not resume-writing mode.
When no action is returned, no action rows are saved, the thread remains `open`,
and the fact is unchanged.

Generated `activate_fact` actions are still proposals. A future approval/eval
flow should evaluate LLM-generated activation recommendations before they are
applied. The current service already routes `activate_fact` application through
the workflow approval boundary. If approval rejects activation, the
`FactReviewAction` moves to `rejected`, the approval rationale is recorded on the
action, and the `ExperienceFact` remains unchanged. `split_fact` should remain
message recommendation metadata until a deterministic split action exists.

Only one open Fact Review thread may exist for a single fact at a time. Messages
are append-only. Resolving or archiving a thread is an explicit status
transition. An open thread can mean active review or a paused conversation that
the user will resume later. Fact activation remains owned by Experience Facts
even when started from a review action.

### Experience Workflow

Purpose: orchestrates experience-related workflow steps across existing components.

Current files:

```text
src/career_agent/experience_workflow/
  factory.py
  finding_generator.py
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
- generate structured source finding proposals after clarification questions close
- manage structured source findings through `SourceAnalysisService`
- apply accepted source findings through `ExperienceFactService`

Experience Workflow does not own persistence. It coordinates component services and should not write directly to JSON files.

Question generation is behind a small `SourceQuestionGenerator` protocol. The deterministic generator is used for local dev validation and fallback behavior. The LLM-backed generator plugs into the same structured proposal contract.

`LLMSourceQuestionGenerator` is available as the first LLM-backed implementation of that protocol. It uses `LLMClient`, expects JSON output, and validates that generated questions match the `GeneratedSourceQuestion` contract before returning them to the workflow.

Experience Workflow checks for an existing active run before question generation. It then generates and validates question proposals before creating a Source Analysis run, so malformed LLM output does not leave behind an active run with no usable questions.

Finding generation is behind a `SourceFindingGenerator` protocol. The deterministic finder is only for local plumbing validation and emits placeholder `unclear` findings. The LLM-backed finder is the real semantic implementation; it uses the extraction LLM configuration, expects JSON output, validates source and fact references, rejects duplicate generated findings, and never mutates canonical facts directly.

Experience Workflow only generates findings for an existing analysis run when all clarification questions are resolved or skipped. Runs with zero questions are allowed. If findings already exist for the run, generation is blocked so the workflow does not create duplicate finding batches.

Experience Workflow applies only accepted findings. `new_fact` creates draft facts, `revises_fact` uses fact revision rules, and `supports_fact` adds evidence through an explicit fact service method. Contradiction, duplicate, unclear, and unrelated findings remain accepted analysis artifacts until a future review workflow handles them.

Factory wiring selects deterministic generators when no LLM base URL is configured. If an LLM base URL is configured, it selects the LLM-backed generators and requires an LLM model. Extraction workflow settings can override the default LLM settings.

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
  -> source analysis questions, messages, and findings
  -> draft experience facts
  -> fact review threads and messages
  -> active experience facts
  -> fact-level reference lists for skills, systems, tools, technologies, and functions
  -> derived cross-role evidence indexes and capabilities
  -> job-fit analysis and tailored documents
```

Experience fact drafts should be grounded in referenced material. Each draft fact should point back to supporting source ids, question ids, and message ids. Those ids should be append-only evidence references; later revisions can add additional support, but should not erase the original trail. Missing evidence should produce either a missing-evidence note or another clarification question, not an invented fact.

This is still the data normalization phase. The goal is a detailed, reusable accounting of the user's actual duties, functions, achievements, systems, tools, scope, and metrics. Persuasive tailoring belongs to later job-specific document generation.

Writing standards for normalized facts:

- prefer generic, reusable terminology over persuasive resume language
- document role functions, duties, achievements, scope, tools, systems, and metrics
- preserve exact metrics and technologies only when supported by evidence
- compile systems, skills, and functions as grounded reference lists, not broad inferred classifications
- avoid artificial scope expansion, inflated verbs, and target-job tailoring
- keep similar-but-not-proven-same work items separate

Merge behavior should be conservative. Similar wording, similar metrics, or shared tools are not enough to combine facts. A generated fact should merge evidence only when it is clearly the same work, same project or process, same metric context, and same outcome.

Fact history should stay separate from the canonical fact record. Messages capture the conversational why; snapshots provide file-level backup; a lightweight `FactChangeEvent` table captures semantic changes such as created, revised, activated, needs-clarification, returned-to-draft, rejected, archived, superseded, and evidence-added. Change events use `actor` for the responsible party with values `user`, `llm`, or `system`, and link back to workflow message ids when a user or LLM exchange caused the change. CLI exposes actor as developer/workflow harness metadata; later TUI or web interfaces should derive actor from workflow context rather than exposing it as an end-user choice.

### Scoped Constraints

User corrections and hard preferences should become durable constraints when appropriate. Constraints may be global writing preferences or scoped evidence rules tied to a role or fact. Later components may add additional scopes when they have persistent records to attach constraints to.

Examples:

- global: never use em dashes
- global: avoid specific disliked words
- role-scoped: do not describe this role as enterprise-level without explicit evidence
- fact-scoped: do not say the user deployed the system; describe the involvement as support oversight

The current constraint scope types are `global`, `role`, and `fact`; additional scopes such as cover letter, resume, proposal, and project can be added when those components exist. Constraints should be represented as separate rule records rather than a single record containing multiple unrelated rules. A single user response may yield multiple constraints, all linked back to workflow messages for traceability.

Constraints should distinguish `preference` from `hard_rule`. The LLM may propose severity during constraint extraction, but deterministic workflow and user approval should decide what becomes active.

### LLM Orchestration Direction

Future LLM behavior should be orchestrated as small structured steps, not one large prompt that performs every task. Each model call should have a narrow responsibility and a validated output contract. Application services remain responsible for persistence and state transitions.

Candidate orchestration steps:

- classify a user response as answer, correction, preference, constraint, rejection, or question
- extract scoped constraints from user corrections and preferences
- propose or revise normalized experience facts
- check draft facts for drift beyond cited evidence
- check whether similar facts are safe to merge or must remain separate
- plan follow-up clarification questions when evidence is missing
- recommend explicit status transitions, while deterministic services apply them

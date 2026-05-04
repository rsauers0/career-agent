# Career Agent V2 Foundation Plan

## Purpose

`v2-foundation` is an intentional rebuild of Career Agent's application foundation.

The initial implementation validated the product direction and core architecture. This branch rebuilds the foundation around smaller, well-defined workflows so the codebase is easier to maintain, test, document, and extend.

The goal is not to discard the existing work. The current implementation remains the reference design while this branch rebuilds the foundation with clearer component boundaries and a more deliberate development sequence.

## Engineering Principles

- Build one concept at a time.
- Prefer small, reviewable changes.
- Keep each step manually runnable.
- Keep each step testable before adding the next layer.
- Use JSON persistence first.
- Use CLI/dev commands before TUI.
- Do not add TUI screens until the underlying workflow is understandable without a UI.
- Do not add LLM workflow behavior until the non-LLM state model is understandable.
- Keep business rules out of CLI, TUI, and future API layers.

## Development Sequence

Each major component should be built in this order:

1. Model
   Define what the data is.
2. Repository
   Define how the data is saved and loaded.
3. Service
   Define what the app can do with the data.
4. CLI
   Provide a low-abstraction way to run the service manually.
5. Tests
   Prove the behavior before adding another concept.
6. TUI
   Present workflows only after the service and CLI behavior are clear.
7. LLM workflow
   Add AI behavior as structured proposals applied by deterministic services.

The LLM boundary is introduced before broader AI workflows. The first slice is a synchronous, provider-neutral `LLMClient` protocol with request/response models, a fake client for tests, and an opt-in OpenAI-compatible HTTP client.

The OpenAI-compatible client remains opt-in through configuration. Tests should use mocked HTTP transport and should not make real network calls.

Workflow wiring should default to deterministic local behavior when no LLM base URL is configured. Setting an LLM base URL opts supported workflows into the OpenAI-compatible client and requires a model.

## Initial Component Order

### 1. User Preferences

Build the smallest complete loop:

- `UserPreferences` model
- save/load one JSON file
- service methods for get/save
- CLI command to show preferences
- CLI command to save/update preferences
- tests for model validation, repository round trip, service behavior, and CLI output

This establishes the project pattern without introducing TUI or LLM complexity too early.

### 2. Experience Role

Build the role container before AI behavior:

- role facts: employer, job title, location, employment type, role focus, start/end month-year, current-role flag
- role status: input required, review required, reviewed, archived
- tests for role date validation, repository ordering, service behavior, and CLI output

### 3. Role Sources

Build source material as a separate component:

- source entries linked to experience roles by `role_id`
- source text preserved exactly as submitted
- source status: not analyzed, analyzed, archived
- repository filtering by role id
- service rule that source material can only be added for an existing role
- CLI support for direct text input and UTF-8 file input

Role Sources are related to Experience Roles, but they are not owned by the Experience Role repository. Keeping them separate preserves traceability and prevents raw source material from being mixed into structured role facts.

### 4. Experience Facts

Build durable normalized experience fact records as a separate component:

- facts linked to experience roles by `role_id`
- append-only source, clarification question, and clarification message id traceability
- fact text
- optional second-level details
- grounded reference lists for systems, skills, and functions
- revision links for superseded and superseding facts
- fact lifecycle status: draft, needs_clarification, active, rejected, superseded, archived
- no broad inferred classifications in the first pass

Experience Facts are canonical career data. Draft facts are canonical fact records that are visible for review but not active yet. Proposed facts should be represented as draft `ExperienceFact` records, not as a separate proposal component. LLM-generated candidates that fail evals should be retained later as analysis artifacts, not as canonical facts. Role-level review remains on Experience Roles.

Experience fact services should strictly enforce status transitions:

- `draft` -> `active`, `needs_clarification`, or `rejected`
- `needs_clarification` -> `draft` or `rejected`
- `active` -> `superseded` or `archived`
- `rejected` -> `archived`
- `superseded` -> `archived`

Draft and needs-clarification facts can be edited in place. Active facts should be revised by creating a new draft fact with `supersedes_fact_id`; activation of that revision should supersede the prior active fact. Rejected, superseded, and archived facts should not be revised in place.

### 5. Source Analysis

Build analysis artifacts before the full AI workflow harness:

- analysis runs linked to one experience role by `role_id`
- each analysis run must include at least one `source_id`
- clarification questions linked to an analysis run
- optional relevant source ids for question traceability
- message threads linked to clarification questions
- analysis and question lifecycle statuses

Source Analysis is workflow evidence, not canonical career data. It gives the future LLM harness a deterministic place to store questions, user responses, and traceability without mixing that material into roles, sources, or facts.

Only one active Source Analysis run should exist per experience role. This prevents a user from starting a second analysis session for the same role before the existing one has been completed or archived.

### 6. Experience AI Workflow Harness

Build as CLI/dev workflow first:

- start or resume an experience role workflow
- capture assistant/user transcript
- use Source Analysis to create clarification questions
- capture clarification messages
- resolve or skip questions when enough evidence exists
- generate structured source findings after clarification questions close
- generate normalized draft experience facts
- preserve user/assistant revision threads for draft facts
- activate accepted experience facts through service methods
- compile grounded systems, skills, and functions on active facts
- derive cross-role evidence indexes and capabilities from active facts later
- mark role reviewed only when validation passes

The TUI should not drive this design. The CLI/dev harness should make every state transition visible, repeatable, and inspectable.

Question resolution should remain explicit. A future LLM workflow may recommend that a clarification thread is complete, but the workflow should call a deterministic transition that can later include eval approval.

The initial deterministic harness starts source analysis for `not_analyzed` role sources only. Previously analyzed sources should not be re-ingested as raw source material; later workflow passes can use existing facts as structured context instead.

Source question generation should use a structured proposal boundary. The deterministic generator returns `GeneratedSourceQuestion` values with question text and relevant source ids. The LLM-backed generator replaces the generator implementation, not the workflow orchestration.

The first LLM-backed source question generator uses the same boundary. It calls `LLMClient`, parses JSON, tolerates fenced JSON blocks, and rejects malformed or ungrounded output before questions are saved.

The workflow should check for an existing active run before question generation, then generate valid question proposals before creating the Source Analysis run. A failed generator should not leave an active run behind.

The next output layer should be draft experience facts, not final resume bullets. Experience facts should normalize source material into grounded, generic, reusable career evidence. They should document duties, functions, achievements, scope, systems, tools, and metrics without adding unsupported complexity or persuasive resume language.

Each draft fact should reference supporting sources, questions, and messages. Those references should be append-only so later revisions preserve the original evidence trail while adding new support. If the evidence is missing, unclear, or conflicting, the workflow should ask another question or record missing evidence instead of fabricating a fact.

User review should be collaborative. A draft fact may have a revision thread where the user corrects wording, supplies additional evidence, asks for a split, or rejects unsupported phrasing. Those messages should remain part of the historical chain for future analysis.

When a user supplies new information during fact review, the durable evidence should be stored as role source material. Even fact-specific source additions should remain role-owned and should be analyzed against the role's existing facts for duplication, contradiction, support, revision needs, and merge risk.

Source Analysis owns structured source findings for that analysis layer. A finding can record that a source appears to support, revise, contradict, duplicate, create, clarify, or be unrelated to a fact. Findings are analysis artifacts, not canonical proof. A source becomes canonical fact support only when accepted fact text references it through `ExperienceFact.source_ids`.

Finding generation should run only after a Source Analysis run exists and all clarification questions for that run are resolved or skipped. A run with zero questions may proceed to findings. If findings already exist for the run, generation should be blocked until an explicit future rerun/archive workflow exists. The deterministic finding generator exists only for local validation; the LLM-backed finder is the real source extraction and classification implementation.

User corrections may create scoped constraints. A single correction can produce multiple durable rules, such as global writing preferences or role/project/proposal-specific hard rules. The first implementation should start with global and role scopes, then add more specific scopes as new components need them. Constraints should be linked to the source message and loaded by later LLM workflows that operate within the same scope.

Constraint extraction should separate preferences from hard rules. The LLM may propose severity, but deterministic workflow and user approval decide what becomes active.

Historical traceability should not be stored directly on the canonical fact. Messages preserve conversational rationale, snapshots preserve file-level backups, and fact change event records preserve semantic changes with an `actor`, event type, summary, source message ids, status transition, related fact id, and timestamp. Actor values are `user`, `llm`, and `system`; UI workflows should set actor from context rather than exposing it as an end-user control.

Future LLM workflows should be orchestrated as a checklist of small structured tasks rather than one large prompt. Candidate steps include response classification, constraint extraction, draft fact generation, drift checking, merge checking, clarification planning, and deterministic service transitions.

### 7. TUI

Add the TUI only after the workflow works from CLI/dev commands.

The TUI should present the already-working workflow. It should not own workflow logic.

### 8. Future API Option

FastAPI can be added later as another interface adapter.

The API should call the same services as CLI and TUI:

```text
CLI / TUI / FastAPI
        -> application service
        -> repository
        -> JSON files
```

FastAPI is not required for the local-first app, but the architecture should not block it.

## Portfolio Framing

This branch should be documented as a deliberate foundation rebuild:

> Rebuilt the project foundation around smaller CLI-first workflows after validating the initial architecture. The rebuild improves readability, testability, and future AI workflow integration.

Strong portfolio signals:

- clear plan
- small commits
- passing tests
- readable module boundaries
- explicit state transitions
- local-first persistence
- deterministic services around AI proposals

## Current Foundation Status

```text
User Preferences
  -> model
  -> repository
  -> service
  -> CLI
  -> tests

Experience Roles
  -> model
  -> repository
  -> service
  -> CLI
  -> tests

Role Sources
  -> model
  -> repository
  -> service
  -> CLI
  -> tests

Experience Facts
  -> model
  -> repository
  -> service
  -> CLI
  -> tests

Source Analysis
  -> model
  -> repository
  -> service
  -> CLI
  -> tests

Experience Workflow
  -> question generator
  -> finding generator
  -> factory wiring
  -> service
  -> CLI
  -> tests

LLM Boundary
  -> request/response models
  -> client protocol
  -> fake client
  -> OpenAI-compatible client
  -> tests
```

The immediate next foundation step is applying accepted Source Findings through deterministic Experience Fact workflows. That step should create or revise draft facts, preserve fact change events, and keep accepted analysis artifacts separate from canonical fact support until the resulting fact text explicitly references its evidence.

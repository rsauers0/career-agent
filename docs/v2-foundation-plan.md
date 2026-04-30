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

### 4. Experience Bullets

Build durable resume-style bullet records as a separate component:

- bullets linked to experience roles by `role_id`
- optional source id traceability
- bullet text
- bullet lifecycle status: draft, active, archived
- no tags or inferred classifications in the first pass

Experience Bullets are canonical career data. Draft bullets are canonical bullet records that are not active yet. LLM-generated candidates that fail evals should be retained later as analysis artifacts, not as canonical bullets. Role-level review remains on Experience Roles.

### 5. Source Analysis

Build analysis artifacts before the full AI workflow harness:

- analysis runs linked to one experience role by `role_id`
- each analysis run must include at least one `source_id`
- clarification questions linked to an analysis run
- optional relevant source ids for question traceability
- message threads linked to clarification questions
- analysis and question lifecycle statuses

Source Analysis is workflow evidence, not canonical career data. It gives the future LLM harness a deterministic place to store questions, user responses, and traceability without mixing that material into roles, sources, or bullets.

Only one active Source Analysis run should exist per experience role. This prevents a user from starting a second analysis session for the same role before the existing one has been completed or archived.

### 6. Experience AI Workflow Harness

Build as CLI/dev workflow first:

- start or resume an experience role workflow
- capture assistant/user transcript
- use Source Analysis to create clarification questions
- capture clarification messages
- resolve or skip questions when enough evidence exists
- generate candidate bullet proposals
- apply bullet proposals through service methods
- mark role reviewed only when validation passes

The TUI should not drive this design. The CLI/dev harness should make every state transition visible, repeatable, and inspectable.

Question resolution should remain explicit. A future LLM workflow may recommend that a clarification thread is complete, but the workflow should call a deterministic transition that can later include eval approval.

The initial deterministic harness starts source analysis for `not_analyzed` role sources only. Previously analyzed sources should not be re-ingested as raw source material; later workflow passes can use existing bullets as structured context instead.

Source question generation should use a structured proposal boundary. The current deterministic generator returns `GeneratedSourceQuestion` values with question text and relevant source ids. A future LLM implementation should replace the generator, not the workflow orchestration.

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

Experience Bullets
  -> model
  -> repository
  -> service
  -> tests

Source Analysis
  -> model
  -> repository
  -> service
  -> CLI
  -> tests

Experience Workflow
  -> service
  -> CLI
  -> tests
```

The immediate next foundation step is the Experience AI workflow harness. It should remain CLI/dev-first and should use the existing services instead of writing directly to JSON files.

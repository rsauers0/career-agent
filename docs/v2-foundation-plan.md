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

### 4. Experience AI Workflow Harness

Build as CLI/dev workflow first:

- start or resume an experience role workflow
- capture assistant/user transcript
- capture role focus through assistant interaction
- add source material
- generate clarification questions
- capture answers
- generate candidate bullet proposals
- apply bullet proposals through service methods
- mark role reviewed only when validation passes

The TUI should not drive this design. The CLI/dev harness should make every state transition visible, repeatable, and inspectable.

### 5. TUI

Add the TUI only after the workflow works from CLI/dev commands.

The TUI should present the already-working workflow. It should not own workflow logic.

### 6. Future API Option

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
```

The immediate next foundation step is the Experience AI workflow harness. It should remain CLI/dev-first and should use the existing services instead of writing directly to JSON files.

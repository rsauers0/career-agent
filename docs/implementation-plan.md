# Career Agent Implementation Plan

## Project Goal

Build `Career Agent` as a local-first Python CLI/TUI application that helps a user:

- manage career preferences
- maintain a structured digital resume
- refine experience entries
- ingest and normalize job postings
- perform AI-assisted job analysis and fit matching
- generate tailored resumes and cover letters

The project is designed to work with local LLMs through OpenAI-compatible APIs wherever practical. A core goal is to reduce API cost and preserve privacy by breaking larger tasks into smaller, evaluable workflow steps that local models can handle reliably.

This document is a living plan. It tracks completed work, current focus, and upcoming milestones.

## Architecture

Use four layers:

1. `domain`
   Pydantic models only. No file I/O, HTTP, or CLI logic.
2. `application`
   Use cases, normalization helpers, and orchestration.
3. `infrastructure`
   File repositories, HTTP/model adapters, and rendering adapters.
4. `interfaces`
   CLI plus a near-term `Textual` TUI, both reusing the same application layer.

Design rule:

`CLI/TUI -> application services/helpers -> repository/model interfaces -> infrastructure adapters`

## AI Strategy

The AI layer is intended to be:

- local-first where practical
- compatible with OpenAI-style APIs for portability across local and hosted providers
- grounded in canonical structured data
- organized into smaller workflow steps so local models can be used reliably

Quality should come from workflow design, structured intermediate outputs, and eval-driven iteration rather than assuming a single large commercial model is always required.

## Completed

### Foundation
- `src/` package layout established
- `uv` project setup with lockfile and local `.venv`
- CLI scaffold built with `Typer` and `Rich`
- Ruff and pytest configured
- basic repo hygiene and ignore rules added

### Domain Models
- `UserPreferences`
- `YearMonth`
- `ExperienceEntry`
- `CareerProfile`

Completed validation includes:
- timezone validation
- commute unit validation
- experience date consistency
- unique `experience_id` values inside `CareerProfile`

### Configuration
- `config.py` implemented with `pydantic-settings`
- configurable `CAREER_AGENT_DATA_DIR`
- cached settings access via `get_settings()`

### Persistence
- repository protocol added
- file-backed profile repository implemented
- JSON persistence for `UserPreferences` and `CareerProfile`
- snapshot-on-overwrite behavior implemented
- storage scaffolding initialization implemented

### Application Layer
- `ProfileService` implemented
- reusable preferences normalization/builder logic added

### CLI Flows
- `doctor`
- `profile init`
  Creates storage scaffolding only
- `profile show`
- `preferences show`
- `preferences wizard`

### Tests
- model round-trip and validation tests
- config tests
- repository tests
- profile service tests
- CLI tests for current commands

## In Progress

### Component Workflow Pattern
Current focus is establishing a repeatable pattern for each major workflow before expanding the application surface area.

Goals:
- implement deterministic application behavior first
- add validation and status evaluation that can be reused by any interface
- expose the workflow through CLI commands and then through the Textual TUI
- keep interface code thin so it does not own business rules
- keep save behavior as one logical write at the end of an authoring flow

Open refinement opportunities:
- define component status contracts such as `not_started`, `incomplete`, `partial`, and `complete`
- separate Pydantic data validity from product-level workflow completeness
- add clearer user-facing validation messaging
- add richer display formatting for existing show commands

## Next

### Component Status And Textual Foundation
Add reusable status evaluation and a local `Textual` foundation before expanding into more profile data.

Planned sequence:
- define application-layer status evaluators for workflow components
- start with `UserPreferences` as the first complete status evaluation target
- add `Textual` as the primary local application interface
- create a landing/dashboard screen that reads component status from the application layer
- reserve space for an assistant panel with a clear "LLM assistant not configured yet" state
- keep Typer commands as development, scripting, and utility entry points

Initial scope:
- show configured data directory and storage status
- show component cards for preferences, career profile, experience, jobs, and documents
- show required and recommended missing fields for components that have status evaluators
- provide navigation into the first implemented component workflow
- avoid mixing preferences, career profile, and experience into one monolithic wizard

Design intent:
- prove the UI architecture with a small but reusable dashboard and one complete workflow
- keep the app local-first without introducing a web service
- make future TUI screens reuse the same service and validation patterns
- keep LLM assistance optional and workflow-specific instead of forcing it into simple data entry

### Preferences Authoring
Complete `UserPreferences` as the first full component using the new pattern.

Planned scope:
- status evaluator for required and recommended preference fields
- Textual preferences form or screen
- field-level validation feedback using the same parsing/model logic as the CLI
- save valid preferences to the existing file-backed repository

### Career Profile Authoring
Add a separate `profile` authoring flow for high-level `CareerProfile` data, distinct from preferences and experience entries.

Planned commands:
- `profile wizard`

Initial scope:
- `core_narrative_notes`
- `skills`
- `tools_and_technologies`
- `domains`
- `notable_achievements`
- `additional_notes`

### Experience Management
Treat experience entries as a separate workflow, not part of the general profile wizard.

Planned commands:
- `experience list`
- `experience add`
- `experience show`
- `experience edit`

Initial scope:
- deterministic create/edit flows for canonical `ExperienceEntry`
- no LLM dependency yet

## Later

### Experience Intake And Refinement
Introduce a draft/intake workflow for messy pasted experience input before canonicalization.

Likely additions:
- `ExperienceIntake` model
- separate repository/service flow
- optional AI-assisted extraction and follow-up questions

### AI-Assisted Job Normalization
Planned additions:
- ingest raw job postings from URL or pasted text
- extract structured fields into `JobPosting`
- normalize title, company, location, compensation, requirements, and constraints

### AI-Assisted Fit Matching
Planned additions:
- compare normalized job postings against `UserPreferences` and `CareerProfile`
- identify strengths, gaps, missing signals, and likely alignment
- produce structured fit-analysis output

### AI-Assisted Document Generation
Planned additions:
- generate tailored resume variants
- generate tailored cover letters
- support collaborative revision loops where the user can request changes and refinements
- use canonical structured profile data as the grounding layer
- output Markdown and HTML first
- add PDF later as a rendering concern

### AI Quality And Iteration
Planned additions may include:
- evaluator or "LLM judge" style checks for output quality and grounding
- future feedback-driven optimization based on user corrections and interaction history
- possible experimentation with frameworks such as DSPy if they fit the workflow

### Observability And Logging
Planned additions:
- structured application logging
- consistent context fields for tracing workflow steps
- file/function/line visibility for debugging
- correlation or operation IDs for end-to-end traceability
- logging design that can later integrate with log aggregation or SIEM tooling

### TUI
Expand the `Textual` interface after the dashboard and first component workflow prove the pattern.

The TUI should reuse:
- services
- builders and normalizers
- repositories
- domain validation
- status evaluators

Planned expansion order:
- landing/dashboard screen
- preferences status and authoring screen
- high-level career profile screen
- experience management screens
- job and document workflows

## Storage Model

The application currently uses a local file-backed persistence model for canonical data.

Design intent:
- single-user, local-first operation
- structured JSON for transparency and portability
- snapshot-on-overwrite for safety and iterative editing

SQLite may be considered later only if query complexity or workflow state justifies it.

Current shape:

```text
<data_dir>/
  profile/
    user_preferences.json
    career_profile.json
  snapshots/
    profile/
```

## Current Principles

- `profile init` only bootstraps storage
- preferences, profile, and experience are separate workflows
- each workflow should follow the pattern: implement component behavior, validate/status it, then expose it in the TUI
- status evaluation belongs in the application layer, not inside CLI or TUI rendering code
- Pydantic validation answers "is this data structurally valid"; status evaluation answers "is this workflow useful or complete enough"
- canonical structured data comes before AI-assisted refinement
- AI features should operate on normalized canonical data whenever possible
- save once per wizard run; do not snapshot every section
- use `.env` or environment variables for local configuration, with `.env.example` as the committed template
- prefer local Textual UI expansion over introducing a service-based web or Slack interface until core workflows require it

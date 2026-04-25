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
- reusable component status model and user preferences status evaluation added
- dashboard status aggregation added

### CLI Flows
- `doctor`
- `profile init`
  Creates storage scaffolding only
- `profile show`
- `preferences show`
- `preferences status`
- `preferences wizard`
- `tui`

### TUI Foundation
- Textual added as the local TUI framework
- initial landing/dashboard screen added
- dashboard shows data directory, profile readiness, job workflow state, and assistant placeholder
- editable User Preferences screen added
- User Preferences form includes required-field markers, dropdown/select inputs, checkbox work arrangements, and add/clear controls for list-style fields
- User Preferences status is backed by application-layer status evaluation
- Career Profile is shown as a profile readiness placeholder until its status evaluator exists
- Jobs is shown as an idle runtime workflow placeholder until job queueing exists

### Tests
- model round-trip and validation tests
- config tests
- repository tests
- profile service tests
- CLI tests for current commands
- dashboard status tests
- TUI factory and formatting tests

## In Progress

### Preferences Editing In The TUI
Current focus is validating and refining the editable `UserPreferences` screen before moving to `CareerProfile`.

Goals:
- reuse the existing preferences builder and domain validation
- keep Textual form code thin so it does not own business rules
- provide field-level validation feedback
- preserve save behavior as one logical write when the user submits the form
- update the dashboard status after preferences are saved

Open refinement opportunities:
- separate Pydantic data validity from product-level workflow completeness
- add clearer user-facing validation messaging
- add richer display formatting for existing show commands

## Next

### Textual Preferences Refinement
Polish `UserPreferences` as the first full component using the new pattern.

Planned scope:
- improve field-level validation feedback
- improve keyboard navigation through the form
- confirm dashboard refresh behavior after saving
- consider moving larger TUI screen classes into dedicated interface modules

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
Expand the `Textual` interface after the preferences authoring screen proves the full view/edit/save pattern.

The TUI should reuse:
- services
- builders and normalizers
- repositories
- domain validation
- status evaluators

Long-term dashboard model:
- profile readiness and job processing should use different status concepts
- `UserPreferences` and `CareerProfile` should use completeness states such as `not_started`, `incomplete`, `partial`, and `complete`
- `Experience` should be part of `CareerProfile` completeness, not a separate top-level dashboard workflow
- `Jobs` should focus on URL/text submission, queueing, processing, analysis, and saved job results
- job workflow state should use runtime concepts such as `idle`, `queued`, `processing`, `completed`, and `failed`
- generated resumes and cover letters should belong to a specific job workflow rather than a standalone dashboard component
- dashboard cards should carry display/action metadata, such as title, detail text, shortcut key, and target screen, instead of forcing the TUI to derive all copy from raw status objects

Planned expansion order:
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
- experience entries are part of `CareerProfile` completeness even if they have their own authoring workflow
- generated documents are outputs of job workflows, not standalone canonical profile data
- each workflow should follow the pattern: implement component behavior, validate/status it, then expose it in the TUI
- status evaluation belongs in the application layer, not inside CLI or TUI rendering code
- profile completeness statuses and job processing statuses should remain separate concepts
- Pydantic validation answers "is this data structurally valid"; status evaluation answers "is this workflow useful or complete enough"
- canonical structured data comes before AI-assisted refinement
- AI features should operate on normalized canonical data whenever possible
- save once per wizard run; do not snapshot every section
- use `.env` or environment variables for local configuration, with `.env.example` as the committed template
- prefer local Textual UI expansion over introducing a service-based web interface until core workflows require it

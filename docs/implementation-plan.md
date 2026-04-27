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

Career Agent should use small, explicit LLM-assisted workflow steps rather than large one-shot generation.

Design goals:
- support local-first and lower-cost model usage
- keep prompts small enough for limited context windows
- reduce drift and hallucination through structured intermediate outputs
- allow user review before data becomes canonical
- preserve inputs, outputs, prompt versions, model metadata, transcripts, and evaluation results for debugging and improvement
- support future DSPy-style prompt optimization from retained workflow and evaluation data

Experience intake should be built as a sequence of narrow transitions:
- source text for one role -> follow-up questions
- source text + answers -> structured facts
- structured facts -> draft `ExperienceEntry`
- draft `ExperienceEntry` -> quality/completeness evaluation
- accepted draft -> canonical `CareerProfile`

The experience workflow should specifically help users reframe duty-list resume bullets into accomplishment-focused entries. Strong outputs should emphasize business impact, measurable outcomes where available, and defensible subjective accomplishments when hard metrics are unavailable. The guided process should teach better resume and cover-letter writing rather than simply accepting vague or noisy source text.

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
- `ExperienceIntakeSession`
- `CareerProfile`

Completed validation includes:
- timezone validation
- commute unit validation
- experience date consistency
- unique `ExperienceEntry.id` values inside `CareerProfile`
- recoverable experience intake status transitions and accepted-entry consistency

### Configuration
- `config.py` implemented with `pydantic-settings`
- configurable `CAREER_AGENT_DATA_DIR`
- cached settings access via `get_settings()`

### Persistence
- repository protocol added
- file-backed profile repository implemented
- file-backed experience intake repository implemented
- JSON persistence for `UserPreferences` and `CareerProfile`
- JSON persistence for recoverable experience intake sessions
- snapshot-on-overwrite behavior implemented
- storage scaffolding initialization implemented

### Application Layer
- `ProfileService` implemented
- `ExperienceIntakeService` implemented for creating, listing, loading, and capturing source text for intake sessions
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
- experience intake service tests
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
- continue refining validation, keyboard flow, and dashboard refresh behavior as issues are found
- keep the preferences screen as the reference implementation for later TUI forms
- keep larger TUI screen classes split into dedicated interface modules

### Experience Intake Foundation
Build the first role-specific, resumable intake workflow before building a broad Career Profile form.

Completed scope:
- stable IDs added to `ExperienceEntry`
- `ExperienceIntakeSession` model added and scoped to one future `ExperienceEntry`
- intake statuses added: `draft`, `source_captured`, `questions_generated`, `answers_captured`, `draft_generated`, `accepted`, and `abandoned`
- local JSON persistence added for intake sessions under `intake/experience`
- snapshot-on-overwrite behavior added for intake sessions
- application service added for creating, listing, loading, and capturing source text for sessions
- assistant protocol added for the first narrow LLM step: source text -> follow-up questions
- service workflow added and tested with a fake assistant for generating follow-up questions
- initial prompt content and structured JSON response parsing added for follow-up questions
- OpenAI-compatible experience intake assistant adapter added behind the assistant protocol

Remaining initial scope:
- store prompt/model metadata and evaluation results as workflow steps are added
- keep accepted sessions archived for development traceability and future eval/prompt improvement
- compose the OpenAI-compatible assistant into a CLI or TUI workflow

### Career Profile Authoring
Treat `CareerProfile` as the accepted, structured result of guided workflows rather than a large manual data-entry form.

Initial direction:
- accepted `ExperienceEntry` records become the foundation of `CareerProfile`
- skills, tools, technologies, achievements, and career themes should be derived or refined from accepted experience data where possible
- users should review and accept derived profile components before they become canonical
- high-level profile screens should focus on review, correction, and narrative direction rather than asking the user to manually brain-dump everything

### Experience Management
Treat experience entries as a role-specific workflow, not part of a general profile wizard.

Planned commands:
- `experience list`
- `experience intake`
- `experience show`
- `experience edit`

Initial scope:
- create and resume intake sessions for one role at a time
- capture raw bullets or notes for a specific job/role, not an entire resume dump
- use guided LLM-assisted steps to clarify missing details and frame work as accomplishments
- accept reviewed draft entries into canonical `CareerProfile`

## Later

### Experience Intake Refinement
Expand the first intake workflow into a full collaborative authoring loop.

Likely additions:
- transcript summarization or cleanup to reduce local storage footprint
- retained eval datasets from accepted/rejected drafts
- prompt version tracking and evaluation history
- optional DSPy experiments once enough workflow examples exist

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
- `Jobs` should remain visible but inaccessible until required profile setup is complete
- job workflow state should use runtime concepts such as `idle`, `queued`, `processing`, `completed`, and `failed`
- generated resumes and cover letters should belong to a specific job workflow rather than a standalone dashboard component
- dashboard cards should carry display/action metadata, such as title, detail text, shortcut key, and target screen, instead of forcing the TUI to derive all copy from raw status objects

Job workflow access rules should be implemented after `CareerProfile` has a real status evaluator:
- `UserPreferences` must have all required fields complete
- `CareerProfile` must have all required fields complete
- `partial` status should be allowed because recommended fields improve quality but should not block workflow access
- inaccessible job actions should explain what setup is still required rather than hiding the workflow entirely

Career Profile access rules should be implemented before the Career Profile authoring screen:
- `UserPreferences` must have all required fields complete before `CareerProfile` authoring is enabled
- `partial` or `complete` `UserPreferences` status should allow access
- if blocked, the dashboard should keep Career Profile visible and explain that required User Preferences must be completed first

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

# Career Agent Implementation Plan

## Goal

Build `Career Agent` as a local-first Python CLI that helps a user:

- manage career preferences
- maintain a structured "digital resume"
- ingest job postings
- analyze job fit
- generate tailored resumes and cover letters

The project should be understandable as it grows. The code should teach application structure, not just produce output.

## Architectural Direction

Use four layers from the start:

1. `domain`
   Holds Pydantic models only. No file I/O, no HTTP calls, no CLI logic.
2. `application`
   Holds use cases and orchestration. This is where "what the app does" lives.
3. `infrastructure`
   Holds adapters for files, HTTP, model providers, and template rendering.
4. `interfaces`
   Holds the user-facing CLI. Later, a `Textual` UI can sit here too.

The design rule is simple:

`CLI -> application services -> repository/model interfaces -> infrastructure adapters`

That rule prevents reengineering later. If we add `Textual`, it should call the same application services the CLI already uses.

## Recommended Stack

- `pydantic`: domain models and validation
- `pydantic-settings`: config from environment variables
- `typer`: command-oriented CLI
- `rich`: better terminal output and prompts
- `httpx`: HTTP for model endpoints and job page fetching
- `jinja2`: document templating
- `trafilatura`: pull useful text from job posting pages
- `pytest`: tests

## Step-By-Step Build Order

### Step 1: Package and CLI scaffold

Files:

- `src/career_agent/cli.py`
- `main.py`
- `pyproject.toml`

Why:

- establishes the `src/` layout early
- gives you a real executable app surface
- keeps the first checkpoint very small

Checkpoint:

```bash
uv run career-agent doctor
```

### Step 2: Define the domain model

Create:

- `src/career_agent/domain/models.py`

Add Pydantic models for:

- `UserPreferences`
- `CareerProfile`
- `ExperienceEntry`
- `EducationEntry`
- `CertificationEntry`
- `JobPosting`
- `JobAnalysis`
- `GeneratedDocument`

Why this step comes early:

- every later service depends on the data shape
- Pydantic gives validation and JSON serialization immediately
- your app logic becomes easier to reason about because it works with typed objects instead of loose dictionaries

Checkpoint:

- create a model instance in a small test
- serialize it to JSON
- load it back and confirm round-trip stability

### Step 3: Add configuration and filesystem layout

Create:

- `src/career_agent/config.py`
- `src/career_agent/infrastructure/filesystem.py`

Responsibilities:

- define the app data directory
- define expected folders such as `profile/`, `jobs/`, and `applications/`
- provide helpers to create directories safely

Recommended default:

- store data under `~/.career-agent`
- allow override with `CAREER_AGENT_DATA_DIR`

Checkpoint:

- run a command that prints the resolved data directory
- verify the folders are created correctly

### Step 4: Add repositories

Create:

- `src/career_agent/application/ports.py`
- `src/career_agent/infrastructure/repositories.py`

Repository interfaces should describe what the app needs:

- load and save preferences
- load and save the career profile
- load and save jobs
- load and save analyses
- list generated documents

The file-based implementation should:

- use JSON for canonical data
- create timestamped snapshots before overwriting profile data

Why this matters:

- your application layer should depend on interfaces, not file paths
- later you can switch some persistence to SQLite without rewriting the CLI or service layer

Checkpoint:

- write repository tests with a temporary directory

### Step 5: Add application services

Create:

- `src/career_agent/application/profile_service.py`
- `src/career_agent/application/job_service.py`
- `src/career_agent/application/document_service.py`

Responsibilities:

- `ProfileService`
  - update preferences
  - update profile data
  - validate weak/missing sections
- `JobService`
  - ingest job text or a URL
  - normalize and store postings
  - request AI-based analysis
- `DocumentService`
  - generate tailored resume and cover-letter variants
  - persist outputs and metadata

Rule:

- services accept and return domain models
- services do not print to the terminal

Checkpoint:

- unit test each service with fake repositories and a fake model client

### Step 6: Add AI provider abstraction

Create:

- `src/career_agent/infrastructure/model_client.py`
- `src/career_agent/prompts/`

Use an OpenAI-compatible API shape so local inference servers can work with the same adapter.

Configuration should include:

- base URL
- API key
- model name
- timeout

Split the AI work into two categories:

1. structured analysis
   Expect JSON back and validate it into `JobAnalysis`
2. document generation
   Expect Markdown back for resumes and cover letters

Why this split is useful:

- analysis should be machine-readable
- generated documents should stay human-editable

Checkpoint:

- mock the HTTP client in tests
- validate that malformed JSON fails loudly and clearly

### Step 7: Add job ingestion adapter

Create:

- `src/career_agent/infrastructure/job_fetcher.py`

Responsibilities:

- fetch HTML from a URL
- extract readable text with `trafilatura`
- normalize whitespace
- preserve raw source content when useful

The first version should support:

- `job add --url <url>`
- `job add --text-file <path>`

Do not add scraping orchestration or job-board automation yet.

Checkpoint:

- test text-file ingestion locally
- mock network calls for URL ingestion tests

### Step 8: Add document rendering

Create:

- `src/career_agent/infrastructure/document_renderer.py`
- `src/career_agent/templates/`

Outputs:

- Markdown for editing and inspection
- HTML for nicer presentation

Keep PDF generation out of the first pass. Once the Markdown and HTML pipeline is stable, PDF becomes a rendering concern rather than a core architecture concern.

Checkpoint:

- verify file output paths and metadata
- open generated HTML in a browser to inspect formatting

### Step 9: Expand the CLI

Add Typer command groups for:

- `profile wizard`
- `profile show`
- `profile validate`
- `job add`
- `job show`
- `job analyze`
- `doc resume generate`
- `doc cover-letter generate`
- `doc list`

Use `Rich` for:

- interactive prompts
- tables and panels
- validation feedback

Rule:

- the CLI collects input and renders output
- the CLI should not contain persistence or model logic

Checkpoint:

- smoke-test the commands with `typer.testing.CliRunner`

### Step 10: Add tests as you go

Create:

- `tests/test_models.py`
- `tests/test_repositories.py`
- `tests/test_services.py`
- `tests/test_cli.py`

Test for:

- model validation
- JSON round-trips
- repository save/load behavior
- snapshot creation
- job analysis flow
- document generation flow
- CLI command wiring
- bad config / bad endpoint failures

## Suggested First Coding Session

For the next coding step, do only this:

1. create `src/career_agent/domain/models.py`
2. define `UserPreferences`
3. define `ExperienceEntry`
4. define `CareerProfile`
5. write one test that round-trips a profile through JSON

That is the smallest useful slice. It will teach:

- Pydantic model design
- typed nested models
- serialization
- test setup

## What I Will Optimize For While Helping

When we code this together, I will prefer:

- small vertical slices
- explicit interfaces
- tests close to each new concept
- explaining why each file exists before adding it

That should help you shift from "Python scripting" to "application design" without losing momentum.

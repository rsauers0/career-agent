# Career Agent

`Career Agent` is a local-first Python CLI for managing a structured career profile, ingesting job postings, and generating tailored resumes and cover letters.

The repo is intentionally starting small. The current scaffold gives you:

- a `src/`-based package layout
- a `Typer` CLI entrypoint
- a small `doctor` command to verify the app wiring
- a written implementation plan in `docs/implementation-plan.md`

## Quick Start

```bash
uv sync
uv run career-agent doctor
```

## Current Goal

Build this in guided steps so the architecture stays understandable:

1. Define the Pydantic domain models
2. Add local file repositories
3. Add application services
4. Add job ingestion and model adapters
5. Add resume and cover-letter generation flows
6. Keep the CLI thin so a future Textual UI can reuse the same core

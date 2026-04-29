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
- start and end month/year
- current role flag
- role status

Experience roles intentionally do not own source material. They are the structured role container.

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

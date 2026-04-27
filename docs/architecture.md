# Career Agent Architecture

Career Agent is organized as a local-first Python application with a command-line interface and an initial Textual TUI. The architecture keeps domain models and application workflows separate from storage and interface concerns so each workflow can be tested and reused.

## Repository Map

This map reflects the files currently tracked in Git.

```text
.
  .env.example                         # template for local environment configuration
  .gitignore                           # ignored local, generated, and environment files
  .python-version                      # Python version used by the project
  README.md                            # project overview and development commands
  main.py                              # simple module entry script
  pyproject.toml                       # project metadata, dependencies, and tool config
  uv.lock                              # locked dependency versions

  docs/
    architecture.md                    # architecture overview and file responsibilities
    implementation-plan.md             # living implementation plan and roadmap

  src/career_agent/
    __init__.py                        # package marker
    cli.py                             # Typer/Rich command-line interface
    config.py                          # pydantic-settings configuration

    application/
      __init__.py                      # application package marker
      dashboard.py                     # dashboard section and status aggregation
      experience_intake_service.py     # application service for recoverable experience intake
      ports.py                         # repository protocols used by application services
      preferences_builder.py           # converts raw preference input into validated models
      profile_service.py               # application service for profile-related workflows
      status.py                        # workflow completeness/status evaluation

    domain/
      __init__.py                      # domain package marker
      models.py                        # Pydantic models and domain validation

    infrastructure/
      __init__.py                      # infrastructure package marker
      llm.py                           # OpenAI-compatible LLM assistant adapters
      repositories.py                  # file-backed JSON persistence and snapshots

    interfaces/
      __init__.py                      # interfaces package marker
      tui.py                           # Textual TUI application shell and runtime factory
      tui_dashboard.py                 # Textual dashboard widgets and status display helpers
      tui_preferences.py               # Textual User Preferences form and form helpers

  tests/
    test_cli.py                        # CLI behavior tests
    test_config.py                     # settings/configuration tests
    test_dashboard.py                  # dashboard status aggregation tests
    test_experience_intake_service.py  # experience intake service tests
    test_llm.py                        # OpenAI-compatible LLM adapter tests
    test_models.py                     # domain model validation and round-trip tests
    test_preferences_builder.py        # preference input normalization tests
    test_profile_service.py            # application service tests
    test_repositories.py               # file repository persistence tests
    test_status.py                     # workflow status evaluation tests
    test_tui.py                        # TUI factory and formatting tests
```

## Layer Responsibilities

### Domain

The domain layer defines the application's core data structures and validation rules.

Current file:

- `src/career_agent/domain/models.py`

This layer should not perform file I/O, call APIs, prompt users, or render output.

### Application

The application layer coordinates use cases and reusable workflow behavior.

Current files:

- `src/career_agent/application/ports.py`
- `src/career_agent/application/dashboard.py`
- `src/career_agent/application/experience_intake_service.py`
- `src/career_agent/application/preferences_builder.py`
- `src/career_agent/application/profile_service.py`
- `src/career_agent/application/status.py`

This layer should contain logic that must be shared by multiple interfaces, such as CLI commands and TUI screens.

### Infrastructure

The infrastructure layer implements technical adapters for storage or external systems.

Current file:

- `src/career_agent/infrastructure/llm.py`
- `src/career_agent/infrastructure/repositories.py`

This layer handles local filesystem persistence and OpenAI-compatible LLM adapters. Future examples may include renderers, database implementations, or additional provider adapters.

### Interfaces

The interface layer is how a user interacts with the application.

Current files:

- `src/career_agent/cli.py`
- `src/career_agent/interfaces/tui.py`
- `src/career_agent/interfaces/tui_dashboard.py`
- `src/career_agent/interfaces/tui_preferences.py`

The CLI uses Typer and Rich to collect input and display output. The Textual TUI provides a local dashboard and preferences form, split into focused interface modules. Interface code should continue to reuse the same application services rather than duplicating workflow logic.

### Configuration

Configuration is intentionally small and local-first.

Current file:

- `src/career_agent/config.py`

Configuration is loaded from environment variables or `.env` using `pydantic-settings`.

## Dependency Guidelines

The intended dependency shape is:

```text
interfaces
  call application services

application
  uses domain models and repository protocols

infrastructure
  implements application protocols

domain
  remains independent of interfaces, infrastructure, and application services
```

The CLI currently acts as the command interface and a composition point: it loads settings, creates the file-backed repository, creates the application service, and renders command output. The TUI has its own composition function for creating the Textual app. Business rules should still live in the application or domain layers.

For example, workflow status rules belong in `application/status.py`:

```python
status = profile_service.get_user_preferences_status()
```

The CLI and Textual TUI should render that status; they should not independently decide which fields make preferences complete.

## Feature Development Pattern

When adding a new workflow, prefer this sequence:

1. Define or update domain models when the data shape changes.
2. Add application-layer behavior for the workflow.
3. Add validation, normalization, status evaluation, or other reusable helpers.
4. Add infrastructure only when storage, files, APIs, or external systems are involved.
5. Add CLI or TUI code as a thin interface over the application behavior.

This keeps the project testable while allowing the interface to evolve from CLI commands to a richer local TUI.

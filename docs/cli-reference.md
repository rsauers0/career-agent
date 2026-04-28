# Career Agent CLI Reference

The CLI is primarily used for scripting, debugging, and validating workflows that are also exposed through the Textual TUI.

For normal interactive use, start with the TUI:

```bash
uv run career-agent tui
```

## Help

Show top-level commands:

```bash
uv run career-agent --help
```

Show help for a command group:

```bash
uv run career-agent profile --help
uv run career-agent preferences --help
uv run career-agent experience --help
```

## Profile Commands

Initialize local storage scaffolding:

```bash
uv run career-agent profile init
```

Show stored profile data:

```bash
uv run career-agent profile show
```

## Preferences Commands

Show user preferences:

```bash
uv run career-agent preferences show
```

Show preferences workflow status:

```bash
uv run career-agent preferences status
```

Run the CLI preferences wizard:

```bash
uv run career-agent preferences wizard
```

## Experience Commands

Create an intake session with role details:

```bash
uv run career-agent experience create \
  --employer-name "Acme Analytics" \
  --job-title "Senior Data Engineer" \
  --location "Chicago, IL" \
  --employment-type full-time \
  --start-date "05/2021" \
  --end-date "06/2024"
```

List intake sessions:

```bash
uv run career-agent experience list
```

Show a stored intake session:

```bash
uv run career-agent experience show <session-id>
```

Update role details for an intake session:

```bash
uv run career-agent experience details <session-id> \
  --employer-name "Acme Analytics" \
  --job-title "Senior Data Engineer" \
  --start-date "05/2021" \
  --current-role
```

Capture source text:

```bash
uv run career-agent experience source <session-id> --text "- Built reporting pipeline"
```

Capture source text from a file:

```bash
uv run career-agent experience source <session-id> --from-file bullets.md
```

Append source text to existing legacy source text:

```bash
uv run career-agent experience source <session-id> --text "- Added alerting" --append
```

Generate follow-up questions using the configured OpenAI-compatible LLM endpoint:

```bash
uv run career-agent experience questions <session-id>
```

Capture answers to generated questions:

```bash
uv run career-agent experience answer <session-id>
```

Generate a draft experience entry:

```bash
uv run career-agent experience draft <session-id>
```

Lock the draft experience entry into the canonical Career Profile:

```bash
uv run career-agent experience lock <session-id>
```

The older `experience accept` command remains as a compatibility alias for `experience lock`.

## LLM Configuration

The `experience questions` and `experience draft` commands call the configured OpenAI-compatible LLM endpoint. Use a local endpoint if you want those workflows to remain local-first.

See the README configuration section for supported LLM environment variables.

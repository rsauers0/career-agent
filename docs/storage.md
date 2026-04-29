# Storage

Career Agent uses local JSON persistence in the `v2-foundation` branch.

The storage root is controlled by:

```text
CAREER_AGENT_DATA_DIR
```

If unset, the default is:

```text
<home-directory>/.career-agent
```

## Current Storage Shape

User Preferences are stored as:

```text
<data_dir>/
  user_preferences/
    user_preferences.json
  snapshots/
    user_preferences/
      <timestamp>-user_preferences.json
```

Experience Roles are stored as:

```text
<data_dir>/
  experience_roles/
    experience_roles.json
  snapshots/
    experience_roles/
      <timestamp>-experience_roles.json
```

## Snapshot Behavior

When a managed JSON file already exists, saving creates a snapshot before overwriting the current file.

Snapshots preserve the previous JSON file for traceability during iterative editing.

The current repository behavior is:

1. Load existing data if present.
2. Before overwrite, copy the existing JSON file to that component's snapshot directory.
3. Write the new JSON file.

Repository code owns this behavior. CLI commands and services do not directly manage file paths or snapshots.

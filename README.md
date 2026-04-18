# google-workspace-multi-account

A standalone Hermes skill project for multi-account Google Workspace access.

This project provides a custom Hermes skill that lets one Hermes profile/session work with multiple named Google accounts for:
- Gmail
- Google Drive
- Google Calendar
- Google Sheets
- Google Docs
- Google Contacts

This repository is the development/source copy used to build, test, version, and publish the skill before deploying it into a running Hermes instance.

Runtime install location:
- `~/.hermes/skills/productivity/google-workspace-multi-account/`

## Status

Current state: working v0.1.0 implementation.

Implemented:
- named Google account storage under `~/.hermes/google_accounts/`
- per-account OAuth setup flow with PKCE
- account-aware Google Workspace API wrapper
- repo-to-runtime deploy script
- basic test coverage for account storage and deployment behavior

## Project layout

```text
google-workspace-multi-account/
  SKILL.md
  README.md
  LICENSE
  .gitignore
  pyproject.toml
  references/
    migration.md
    usage.md
  scripts/
    account_store.py
    deploy_skill.py
    google_api_multi.py
    setup_multi.py
  tests/
    test_account_store.py
    test_deploy_skill.py
```

## Runtime data layout

The skill stores account data outside the skill directory, under the active `HERMES_HOME`:

```text
~/.hermes/google_accounts/
  default_account.json
  work/
    token.json
    client_secret.json
    oauth_pending.json
    metadata.json
  personal/
    token.json
    client_secret.json
    oauth_pending.json
    metadata.json
```

## Required Google APIs

Enable the APIs you plan to use in the Google Cloud project that owns your OAuth client.

Recommended:
- Gmail API
- Google Calendar API
- Google Drive API
- Google Sheets API
- Google Docs API
- People API

Note:
- `drive.googleapis.com` is required for normal Drive access in this project.
- `drivemcp.googleapis.com` is a separate Google MCP service and is not required for this implementation.

## Setup examples

These examples use generic placeholder aliases and paths. They do not correspond to any real user accounts.

### Connect an account

```bash
PY="$HOME/.hermes/hermes-agent/venv/bin/python"
SKILL="$HOME/.hermes/skills/productivity/google-workspace-multi-account/scripts"

"$PY" "$SKILL/setup_multi.py" --account work --client-secret /path/to/client_secret.json
"$PY" "$SKILL/setup_multi.py" --account work --auth-url
```

Open the returned URL, authorize the Google account, then paste the full localhost redirect URL back into:

```bash
"$PY" "$SKILL/setup_multi.py" --account work --auth-code "http://localhost:1/?code=...&state=..."
```

Verify:

```bash
"$PY" "$SKILL/setup_multi.py" --account work --check
```

### Connect a second account

```bash
"$PY" "$SKILL/setup_multi.py" --account personal --client-secret /path/to/client_secret.json
"$PY" "$SKILL/setup_multi.py" --account personal --auth-url
"$PY" "$SKILL/setup_multi.py" --account personal --auth-code "http://localhost:1/?code=...&state=..."
```

### Set a default account

```bash
"$PY" "$SKILL/setup_multi.py" --default-account personal
```

## Usage examples

### Search Drive in a specific account

```bash
"$PY" "$SKILL/google_api_multi.py" --account work drive search "quarterly report"
"$PY" "$SKILL/google_api_multi.py" --account personal drive search "tax documents"
```

### Search Gmail in a specific account

```bash
"$PY" "$SKILL/google_api_multi.py" --account work gmail search "is:unread"
```

### List upcoming calendar events

```bash
"$PY" "$SKILL/google_api_multi.py" --account personal calendar list
```

### Use the default account

If a default account is configured, you can omit `--account`:

```bash
"$PY" "$SKILL/google_api_multi.py" drive search "notes"
```

## Development workflow

1. Develop in this repository.
2. Run tests locally.
3. Deploy/sync the finished skill into the runtime location.
4. Use the deployed runtime copy from Hermes.

Deploy to runtime:

```bash
PY="$HOME/.hermes/hermes-agent/venv/bin/python"
"$PY" scripts/deploy_skill.py
```

## Testing

Run the test suite with the Hermes venv Python:

```bash
PY="$HOME/.hermes/hermes-agent/venv/bin/python"
"$PY" -m unittest discover -s tests -v
```

## Security notes

Do not commit:
- OAuth client secrets
- tokens
- account metadata from real users
- real Gmail/Drive output

Use placeholder aliases and placeholder email addresses in public documentation.

## License

MIT

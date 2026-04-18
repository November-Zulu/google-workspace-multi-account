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
- install and deploy scripts for Hermes runtime installation
- basic test coverage for account storage and deployment behavior

## Quickstart for Hermes users

If you already have Hermes installed locally, the fastest way to use this skill is:

1. Clone this repository:

```bash
git clone https://github.com/November-Zulu/google-workspace-multi-account.git
cd google-workspace-multi-account
```

2. Install the skill into your Hermes runtime:

```bash
python3 scripts/install_skill.py
```

3. Define helper variables:

```bash
PY="$HOME/.hermes/hermes-agent/venv/bin/python"
SKILL="$HOME/.hermes/skills/productivity/google-workspace-multi-account/scripts"
```

4. Save a Google OAuth client secret for a named account:

```bash
"$PY" "$SKILL/setup_multi.py" --account work --client-secret /path/to/client_secret.json
```

5. Generate the auth URL:

```bash
"$PY" "$SKILL/setup_multi.py" --account work --auth-url
```

6. Open the URL, authorize the account, then paste the localhost redirect URL back into:

```bash
"$PY" "$SKILL/setup_multi.py" --account work --auth-code "http://localhost:1/?code=...&state=..."
```

7. Verify auth:

```bash
"$PY" "$SKILL/setup_multi.py" --account work --check
```

8. Use the account:

```bash
"$PY" "$SKILL/google_api_multi.py" --account work drive search "project plan"
```

## Project layout

```text
google-workspace-multi-account/
  SKILL.md
  README.md
  LICENSE
  .gitignore
  pyproject.toml
  references/
    fresh-machine-setup.md
    migration.md
    usage.md
  scripts/
    account_store.py
    deploy_skill.py
    google_api_multi.py
    install_skill.py
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

## Fresh machine setup

If you are starting from a machine with Hermes but without this custom skill installed yet, see:
- `references/fresh-machine-setup.md`

That guide covers:
- cloning the repo
- installing into `~/.hermes/skills/`
- using the Hermes venv Python
- connecting the first account
- setting a default account

## Testing

Run the test suite with the Hermes venv Python:

```bash
PY="$HOME/.hermes/hermes-agent/venv/bin/python"
"$PY" -m unittest discover -s tests -v
```

## License

MIT

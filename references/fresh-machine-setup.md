# Fresh machine setup

This guide explains how to install and use `google-workspace-multi-account` on a machine that already has Hermes installed, but does not yet have this custom skill deployed.

All examples below use placeholder aliases and placeholder paths.

## Assumptions

- Hermes is installed under `~/.hermes/`
- Hermes has a Python virtual environment at:
  - `~/.hermes/hermes-agent/venv/bin/python`
- You have a local copy of this repository

## 1. Get the source repo

Either clone the repository:

```bash
git clone https://github.com/November-Zulu/google-workspace-multi-account.git
cd google-workspace-multi-account
```

Or copy the project directory onto the machine by your preferred method.

## 2. Deploy the runtime skill

Use the Hermes venv Python to deploy the repo contents into the runtime skills directory:

```bash
PY="$HOME/.hermes/hermes-agent/venv/bin/python"
"$PY" scripts/deploy_skill.py
```

This installs the runtime skill under:

```text
~/.hermes/skills/productivity/google-workspace-multi-account/
```

## 3. Define helper variables

```bash
PY="$HOME/.hermes/hermes-agent/venv/bin/python"
SKILL="$HOME/.hermes/skills/productivity/google-workspace-multi-account/scripts"
```

## 4. Create a Google OAuth client

For each Google account you want to connect:

1. Go to:
   - https://console.cloud.google.com/apis/credentials
2. Create a project or select an existing one
3. Enable the APIs you plan to use:
   - Gmail API
   - Google Calendar API
   - Google Drive API
   - Google Sheets API
   - Google Docs API
   - People API
4. Create an OAuth 2.0 Client ID
5. Choose application type:
   - Desktop app
6. Download the client secret JSON file

## 5. Connect the first account

Save the client secret under a named alias:

```bash
"$PY" "$SKILL/setup_multi.py" --account work --client-secret /path/to/client_secret.json
```

Generate the authorization URL:

```bash
"$PY" "$SKILL/setup_multi.py" --account work --auth-url
```

Open the URL in a browser, authorize access, then paste the full localhost redirect URL back into:

```bash
"$PY" "$SKILL/setup_multi.py" --account work --auth-code "http://localhost:1/?code=...&state=..."
```

Verify:

```bash
"$PY" "$SKILL/setup_multi.py" --account work --check
```

## 6. Connect a second account

Repeat the same process with another alias:

```bash
"$PY" "$SKILL/setup_multi.py" --account personal --client-secret /path/to/client_secret.json
"$PY" "$SKILL/setup_multi.py" --account personal --auth-url
"$PY" "$SKILL/setup_multi.py" --account personal --auth-code "http://localhost:1/?code=...&state=..."
```

## 7. Set a default account

If you want commands without `--account` to use one account by default:

```bash
"$PY" "$SKILL/setup_multi.py" --default-account personal
```

## 8. Test usage

Drive search:

```bash
"$PY" "$SKILL/google_api_multi.py" --account work drive search "project plan"
"$PY" "$SKILL/google_api_multi.py" --account personal drive search "tax docs"
```

Gmail search:

```bash
"$PY" "$SKILL/google_api_multi.py" --account work gmail search "is:unread"
```

Calendar list:

```bash
"$PY" "$SKILL/google_api_multi.py" --account personal calendar list
```

## 9. Inspect configured accounts

```bash
"$PY" "$SKILL/setup_multi.py" --list-accounts
"$PY" "$SKILL/setup_multi.py" --show-account --account work
```

## 10. Optional: migrate a legacy single-account token

If this Hermes profile has old single-account files like `~/.hermes/google_token.json`, migrate them into a named account:

```bash
"$PY" "$SKILL/setup_multi.py" --migrate-legacy legacy
```

## Notes

- Account state is stored under `~/.hermes/google_accounts/`
- This project uses the standard Google product APIs, not the Google MCP service endpoints
- Do not commit real client secret files, tokens, or account metadata into git

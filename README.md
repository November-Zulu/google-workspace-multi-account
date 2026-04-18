# google-workspace-multi-account

A standalone Hermes skill project for multi-account Google Workspace access.

This project is the development/source repository for a custom Hermes skill that allows one Hermes profile/session to work with multiple named Google accounts for:
- Gmail
- Google Drive
- Google Calendar
- Google Sheets
- Google Docs
- Google Contacts

The runtime-installed skill is intended to live at:
- `~/.hermes/skills/productivity/google-workspace-multi-account/`

This repository is the clean development copy used to build, test, version, and publish the skill before deploying it into the running Hermes instance.

## Status

Current state: scaffold / architecture bootstrap.

What exists now:
- skill definition (`SKILL.md`)
- account storage helpers
- setup CLI scaffold
- API CLI scaffold
- migration and usage notes

What is still pending:
- full OAuth PKCE flow in `scripts/setup_multi.py`
- account-aware Google API handlers in `scripts/google_api_multi.py`
- testing and deployment workflow

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
    setup_multi.py
    google_api_multi.py
```

## Runtime data layout

The skill should store account data outside the skill directory, under the active `HERMES_HOME`:

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

## Development workflow

1. Develop here in this repository.
2. Test the scripts locally.
3. When ready, deploy/sync the finished skill into:
   - `~/.hermes/skills/productivity/google-workspace-multi-account/`
4. Then use the deployed runtime copy from Hermes.

## Suggested next phase

- Port OAuth flow from the bundled `google-workspace` skill into `scripts/setup_multi.py`
- Port Google API service handlers into `scripts/google_api_multi.py`
- Add account selection, metadata identity capture, and safety confirmations
- Add tests and deployment documentation

## License

MIT

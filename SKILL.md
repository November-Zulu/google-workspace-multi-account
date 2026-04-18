---
name: google-workspace-multi-account
description: Multi-account Google Workspace integration for Gmail, Drive, Calendar, Sheets, Docs, and Contacts using named Google accounts stored under ~/.hermes/google_accounts/.
version: 0.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [Google, Gmail, Calendar, Drive, Sheets, Docs, Contacts, OAuth, multi-account]
    related_skills: [google-workspace]
---

# Google Workspace Multi-Account

Use this skill when the user wants one Hermes profile/session to access more than one Google account by name.

## Goal

Provide a custom, update-resistant Google Workspace integration that keeps:
- skill code under `~/.hermes/skills/productivity/google-workspace-multi-account/`
- account data under `~/.hermes/google_accounts/`

Do **not** modify the bundled `google-workspace` skill for this workflow.

## Account model

Each named Google account lives under:

```text
~/.hermes/google_accounts/<alias>/
  token.json
  client_secret.json
  oauth_pending.json
  metadata.json
```

Default-account pointer:

```text
~/.hermes/google_accounts/default_account.json
```

## Files in this skill

- `scripts/account_store.py` — account path resolution, alias validation, metadata helpers
- `scripts/setup_multi.py` — OAuth setup and account-management CLI
- `scripts/google_api_multi.py` — account-aware Google API wrapper CLI
- `references/usage.md` — user-facing command examples
- `references/migration.md` — legacy migration notes
- `references/fresh-machine-setup.md` — clean install/deploy/setup guide for a new machine

## Rules

1. Keep all Google account state under `~/.hermes/google_accounts/`.
2. Prefer explicit `--account <alias>` for side-effecting actions.
3. Show the selected account identity in confirmations for send/create/delete actions.
4. Preserve compatibility with legacy single-account files when practical.
5. Do not silently guess between multiple configured accounts unless a default is set.

## Recommended CLI surface

Setup examples:

```bash
python scripts/setup_multi.py --list-accounts
python scripts/setup_multi.py --account work --client-secret /path/to/client_secret.json
python scripts/setup_multi.py --account work --auth-url
python scripts/setup_multi.py --account work --auth-code "http://localhost:1/?code=..."
python scripts/setup_multi.py --default-account work
```

Usage examples:

```bash
python scripts/google_api_multi.py --account work drive search "quarterly report"
python scripts/google_api_multi.py --account personal gmail search "is:unread"
python scripts/google_api_multi.py --account work calendar list
```

## Implementation notes

- Additive flags are preferred over breaking CLI changes.
- Account aliases should be filesystem-safe.
- If there is exactly one configured account, auto-selecting it is acceptable.
- If there are multiple accounts and no default, fail clearly and require `--account`.

## Current status

This skill is scaffolded locally as a user-owned customization so it is resilient to bundled skill updates. Complete the Python script implementations before relying on it for live Google access.

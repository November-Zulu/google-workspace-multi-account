# Migration from legacy single-account Google Workspace skill

Legacy single-account files may exist directly under `~/.hermes/`:

```text
~/.hermes/google_token.json
~/.hermes/google_client_secret.json
~/.hermes/google_oauth_pending.json
```

## Recommended migration behavior

Add a command like:

```bash
python scripts/setup_multi.py --migrate-legacy default
```

This should:
- create `~/.hermes/google_accounts/default/`
- copy legacy files into that directory as:
  - `token.json`
  - `client_secret.json`
  - `oauth_pending.json`
- create/update `metadata.json`
- optionally set `default` as the default account

## Safety rules

- Prefer copy over move during first migration.
- Leave legacy files untouched unless the user explicitly asks to remove them.
- Report exactly what was copied.
- If the target alias already exists, refuse unless an explicit overwrite flag is added.

## Compatibility policy

The multi-account skill should be able to coexist with the bundled `google-workspace` skill during migration. Avoid changing bundled-skill code just to support migration.

# Usage

This skill is intended to let one Hermes session use multiple Google accounts by explicit alias.

## Data layout

All account data should live under:

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

## Setup flow

1. Save a client secret for a named account:

```bash
python scripts/setup_multi.py --account work --client-secret /path/to/client_secret.json
```

2. Generate an auth URL:

```bash
python scripts/setup_multi.py --account work --auth-url
```

3. Open the URL, authorize in the browser, then paste the redirect URL or code:

```bash
python scripts/setup_multi.py --account work --auth-code "http://localhost:1/?code=..."
```

4. Verify:

```bash
python scripts/setup_multi.py --account work --check
```

## Account management

```bash
python scripts/setup_multi.py --list-accounts
python scripts/setup_multi.py --show-account work
python scripts/setup_multi.py --default-account work
python scripts/setup_multi.py --revoke --account work
```

## API usage

```bash
python scripts/google_api_multi.py --account work drive search "quarterly report"
python scripts/google_api_multi.py --account personal gmail search "is:unread"
python scripts/google_api_multi.py --account work calendar list
python scripts/google_api_multi.py --account personal sheets get SHEET_ID "Sheet1!A1:D10"
```

## Account resolution rules

- If `--account` is provided, use it.
- If omitted and exactly one account exists, use it.
- If omitted and a default account exists, use it.
- If omitted and multiple accounts exist with no default, fail clearly.

## Safety guidance

For sending email or creating/deleting events, always show the chosen account alias and email address before taking action.

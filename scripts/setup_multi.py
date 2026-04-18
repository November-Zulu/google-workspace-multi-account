#!/usr/bin/env python3
"""Multi-account Google Workspace OAuth setup CLI."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from account_store import (
    detect_legacy_single_account,
    ensure_account_dir,
    get_client_secret_path,
    get_metadata_path,
    get_pending_auth_path,
    get_token_path,
    list_accounts,
    load_account_metadata,
    load_json,
    now_iso,
    resolve_account_or_default,
    save_account_metadata,
    save_json,
    set_default_account,
    validate_account_alias,
)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/contacts.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/documents.readonly",
]

REQUIRED_PACKAGES = [
    "google-api-python-client",
    "google-auth-oauthlib",
    "google-auth-httplib2",
]

REDIRECT_URI = "http://localhost:1"


def _token_payload(alias: str) -> dict:
    return load_json(get_token_path(alias), default={})


def _missing_scopes_from_payload(payload: dict) -> list[str]:
    raw = payload.get("scopes") or payload.get("scope")
    if not raw:
        return []
    granted = {s.strip() for s in (raw.split() if isinstance(raw, str) else raw) if s.strip()}
    return sorted(scope for scope in SCOPES if scope not in granted)


def _format_missing_scopes(missing_scopes: list[str]) -> str:
    bullets = "\n".join(f"  - {scope}" for scope in missing_scopes)
    return (
        "Token is valid but missing required Google Workspace scopes:\n"
        f"{bullets}\n"
        "Run setup again for this same named account to refresh consent."
    )


def install_deps() -> bool:
    try:
        import googleapiclient  # noqa: F401
        import google_auth_oauthlib  # noqa: F401
        print("Dependencies already installed.")
        return True
    except ImportError:
        pass

    print("Installing Google API dependencies...")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet", *REQUIRED_PACKAGES],
            stdout=subprocess.DEVNULL,
        )
        print("Dependencies installed.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Failed to install dependencies: {e}", file=sys.stderr)
        print(
            f"Try manually: {sys.executable} -m pip install {' '.join(REQUIRED_PACKAGES)}",
            file=sys.stderr,
        )
        return False


def _ensure_deps() -> None:
    try:
        import googleapiclient  # noqa: F401
        import google_auth_oauthlib  # noqa: F401
    except ImportError:
        if not install_deps():
            raise SystemExit(1)


def _save_pending_auth(alias: str, *, state: str, code_verifier: str) -> None:
    save_json(
        get_pending_auth_path(alias),
        {
            "state": state,
            "code_verifier": code_verifier,
            "redirect_uri": REDIRECT_URI,
        },
    )


def _load_pending_auth(alias: str) -> dict:
    path = get_pending_auth_path(alias)
    if not path.exists():
        print("ERROR: No pending OAuth session found. Run --auth-url first.", file=sys.stderr)
        raise SystemExit(1)

    data = load_json(path, default={})
    if not data.get("state") or not data.get("code_verifier"):
        print("ERROR: Pending OAuth session is missing PKCE data.", file=sys.stderr)
        print("Run --auth-url again to start a fresh OAuth session.", file=sys.stderr)
        raise SystemExit(1)
    return data


def _extract_code_and_state(code_or_url: str) -> tuple[str, str | None]:
    if not code_or_url.startswith("http"):
        return code_or_url, None

    from urllib.parse import parse_qs, urlparse

    parsed = urlparse(code_or_url)
    params = parse_qs(parsed.query)
    if "code" not in params:
        print("ERROR: No 'code' parameter found in URL.", file=sys.stderr)
        raise SystemExit(1)

    state = params.get("state", [None])[0]
    return params["code"][0], state


def _fetch_identity(alias: str) -> dict:
    _ensure_deps()
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    token_path = get_token_path(alias)
    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    try:
        gmail = build("gmail", "v1", credentials=creds)
        profile = gmail.users().getProfile(userId="me").execute()
        return {
            "email": profile.get("emailAddress", ""),
        }
    except Exception:
        return {}


def cmd_list_accounts(_: argparse.Namespace) -> int:
    print(json.dumps(list_accounts(), indent=2, ensure_ascii=False))
    return 0


def cmd_show_account(args: argparse.Namespace) -> int:
    alias = resolve_account_or_default(args.account)
    payload = {
        "alias": alias,
        "paths": {
            "token": str(get_token_path(alias)),
            "client_secret": str(get_client_secret_path(alias)),
            "oauth_pending": str(get_pending_auth_path(alias)),
            "metadata": str(get_metadata_path(alias)),
        },
        "metadata": load_account_metadata(alias),
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def cmd_set_client_secret(args: argparse.Namespace) -> int:
    alias = validate_account_alias(args.account)
    src = Path(args.client_secret).expanduser().resolve()
    if not src.exists():
        print(f"ERROR: File not found: {src}", file=sys.stderr)
        return 1
    try:
        data = json.loads(src.read_text())
    except Exception as e:
        print(f"ERROR: Invalid JSON: {e}", file=sys.stderr)
        return 1
    if "installed" not in data and "web" not in data:
        print("ERROR: Not a Google OAuth client secret file.", file=sys.stderr)
        return 1

    ensure_account_dir(alias)
    dest = get_client_secret_path(alias)
    dest.write_text(json.dumps(data, indent=2) + "\n")
    save_account_metadata(alias, {"auth_status": "client_secret_saved"})
    print(json.dumps({"status": "ok", "alias": alias, "client_secret": str(dest)}, indent=2))
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    alias = resolve_account_or_default(args.account)
    token_path = get_token_path(alias)
    if not token_path.exists():
        print(
            json.dumps(
                {
                    "alias": alias,
                    "authenticated": False,
                    "status": "not_authenticated",
                    "token_path": str(token_path),
                },
                indent=2,
            )
        )
        return 1

    _ensure_deps()
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    try:
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    except Exception as e:
        print(json.dumps({"alias": alias, "authenticated": False, "status": "token_corrupt", "error": str(e)}, indent=2))
        return 1

    payload = _token_payload(alias)
    if creds.valid:
        missing_scopes = _missing_scopes_from_payload(payload)
        if missing_scopes:
            print(
                json.dumps(
                    {
                        "alias": alias,
                        "authenticated": False,
                        "status": "auth_scope_mismatch",
                        "missing_scopes": missing_scopes,
                        "message": _format_missing_scopes(missing_scopes),
                    },
                    indent=2,
                )
            )
            return 1
        metadata = save_account_metadata(alias, {"auth_status": "authenticated"})
        print(json.dumps({"alias": alias, "authenticated": True, "status": "authenticated", "metadata": metadata}, indent=2))
        return 0

    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            token_path.write_text(creds.to_json())
            missing_scopes = _missing_scopes_from_payload(_token_payload(alias))
            if missing_scopes:
                print(
                    json.dumps(
                        {
                            "alias": alias,
                            "authenticated": False,
                            "status": "auth_scope_mismatch",
                            "missing_scopes": missing_scopes,
                            "message": _format_missing_scopes(missing_scopes),
                        },
                        indent=2,
                    )
                )
                return 1
            metadata = save_account_metadata(alias, {"auth_status": "authenticated", "last_authenticated_at": now_iso()})
            print(json.dumps({"alias": alias, "authenticated": True, "status": "authenticated_refreshed", "metadata": metadata}, indent=2))
            return 0
        except Exception as e:
            print(json.dumps({"alias": alias, "authenticated": False, "status": "refresh_failed", "error": str(e)}, indent=2))
            return 1

    print(json.dumps({"alias": alias, "authenticated": False, "status": "token_invalid"}, indent=2))
    return 1


def cmd_auth_url(args: argparse.Namespace) -> int:
    alias = validate_account_alias(args.account)
    client_secret_path = get_client_secret_path(alias)
    if not client_secret_path.exists():
        print("ERROR: No client secret saved for this account.", file=sys.stderr)
        return 1

    _ensure_deps()
    from google_auth_oauthlib.flow import Flow

    flow = Flow.from_client_secrets_file(
        str(client_secret_path),
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
        autogenerate_code_verifier=True,
    )
    auth_url, state = flow.authorization_url(access_type="offline", prompt="consent")
    _save_pending_auth(alias, state=state, code_verifier=flow.code_verifier)
    print(auth_url)
    return 0


def cmd_auth_code(args: argparse.Namespace) -> int:
    alias = validate_account_alias(args.account)
    client_secret_path = get_client_secret_path(alias)
    token_path = get_token_path(alias)
    if not client_secret_path.exists():
        print("ERROR: No client secret saved for this account. Run --client-secret first.", file=sys.stderr)
        return 1

    pending_auth = _load_pending_auth(alias)
    code, returned_state = _extract_code_and_state(args.auth_code)
    if returned_state and returned_state != pending_auth["state"]:
        print("ERROR: OAuth state mismatch. Run --auth-url again to start a fresh session.", file=sys.stderr)
        return 1

    _ensure_deps()
    from google_auth_oauthlib.flow import Flow

    flow = Flow.from_client_secrets_file(
        str(client_secret_path),
        scopes=SCOPES,
        redirect_uri=pending_auth.get("redirect_uri", REDIRECT_URI),
        state=pending_auth["state"],
        code_verifier=pending_auth["code_verifier"],
    )

    try:
        flow.fetch_token(code=code)
    except Exception as e:
        print(f"ERROR: Token exchange failed: {e}", file=sys.stderr)
        print("The code may have expired. Run --auth-url to get a fresh URL.", file=sys.stderr)
        return 1

    creds = flow.credentials
    token_payload = json.loads(creds.to_json())
    missing_scopes = _missing_scopes_from_payload(token_payload)
    if missing_scopes:
        print(
            f"ERROR: Refusing to save incomplete Google Workspace token. {_format_missing_scopes(missing_scopes)}",
            file=sys.stderr,
        )
        if token_path.exists():
            print(f"Existing token at {token_path} was left unchanged.", file=sys.stderr)
        return 1

    save_json(token_path, token_payload)
    get_pending_auth_path(alias).unlink(missing_ok=True)

    identity = _fetch_identity(alias)
    save_account_metadata(
        alias,
        {
            "auth_status": "authenticated",
            "email": identity.get("email", ""),
            "last_authenticated_at": now_iso(),
            "scopes": token_payload.get("scopes") or token_payload.get("scope") or [],
        },
    )

    print(
        json.dumps(
            {
                "status": "ok",
                "alias": alias,
                "token_path": str(token_path),
                "email": identity.get("email", ""),
                "metadata": load_account_metadata(alias),
            },
            indent=2,
        )
    )
    return 0


def cmd_revoke(args: argparse.Namespace) -> int:
    alias = resolve_account_or_default(args.account)
    token_path = get_token_path(alias)
    _ensure_deps()

    if token_path.exists():
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            import urllib.request

            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
            urllib.request.urlopen(
                urllib.request.Request(
                    f"https://oauth2.googleapis.com/revoke?token={creds.token}",
                    method="POST",
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
            )
        except Exception:
            pass

    removed = []
    for path in [token_path, get_pending_auth_path(alias)]:
        if path.exists():
            path.unlink()
            removed.append(str(path))
    save_account_metadata(alias, {"auth_status": "revoked"})
    print(json.dumps({"status": "ok", "alias": alias, "removed": removed}, indent=2))
    return 0


def cmd_default_account(args: argparse.Namespace) -> int:
    alias = validate_account_alias(args.default_account)
    ensure_account_dir(alias)
    print(json.dumps(set_default_account(alias), indent=2))
    return 0


def cmd_migrate_legacy(args: argparse.Namespace) -> int:
    alias = validate_account_alias(args.migrate_legacy)
    legacy = detect_legacy_single_account()
    if not legacy:
        print(json.dumps({"status": "no_legacy_files_found"}, indent=2))
        return 0
    account_dir = ensure_account_dir(alias)
    copies = []
    mapping = {
        "token": account_dir / "token.json",
        "client_secret": account_dir / "client_secret.json",
        "oauth_pending": account_dir / "oauth_pending.json",
    }
    for key, src in legacy.items():
        dest = mapping[key]
        if dest.exists():
            print(f"ERROR: Destination already exists: {dest}", file=sys.stderr)
            return 1
        shutil.copy2(src, dest)
        copies.append({"from": src, "to": str(dest)})
    save_account_metadata(alias, {"auth_status": "migrated_from_legacy"})
    print(json.dumps({"status": "ok", "alias": alias, "copied": copies}, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Multi-account Google Workspace setup")
    parser.add_argument("--account", help="Account alias, e.g. work or personal")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--list-accounts", action="store_true")
    group.add_argument("--show-account", action="store_true")
    group.add_argument("--check", action="store_true")
    group.add_argument("--client-secret", metavar="PATH")
    group.add_argument("--auth-url", action="store_true")
    group.add_argument("--auth-code", metavar="CODE_OR_URL")
    group.add_argument("--revoke", action="store_true")
    group.add_argument("--default-account", metavar="ALIAS")
    group.add_argument("--migrate-legacy", metavar="ALIAS")
    group.add_argument("--install-deps", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.list_accounts:
        return cmd_list_accounts(args)
    if args.show_account:
        return cmd_show_account(args)
    if args.check:
        return cmd_check(args)
    if args.client_secret:
        if not args.account:
            print("ERROR: --client-secret requires --account", file=sys.stderr)
            return 1
        return cmd_set_client_secret(args)
    if args.auth_url:
        if not args.account:
            print("ERROR: --auth-url requires --account", file=sys.stderr)
            return 1
        return cmd_auth_url(args)
    if args.auth_code:
        if not args.account:
            print("ERROR: --auth-code requires --account", file=sys.stderr)
            return 1
        return cmd_auth_code(args)
    if args.revoke:
        return cmd_revoke(args)
    if args.default_account:
        return cmd_default_account(args)
    if args.migrate_legacy:
        return cmd_migrate_legacy(args)
    if args.install_deps:
        return 0 if install_deps() else 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Helpers for named Google account storage under HERMES_HOME/google_accounts/."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from hermes_constants import get_hermes_home
except ModuleNotFoundError:
    import sys

    candidates = []
    env_home = os.getenv("HERMES_HOME", "").strip()
    if env_home:
        candidates.append(Path(env_home) / "hermes-agent")
    candidates.append(Path.home() / ".hermes" / "hermes-agent")

    current = Path(__file__).resolve()
    for parent in current.parents:
        candidates.append(parent / "hermes-agent")

    seen: set[str] = set()
    for candidate in candidates:
        candidate_str = str(candidate)
        if candidate_str in seen:
            continue
        seen.add(candidate_str)
        if candidate.exists():
            sys.path.insert(0, candidate_str)
            break

    from hermes_constants import get_hermes_home

ACCOUNT_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,31}$")
SCHEMA_VERSION = 1


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def get_accounts_root() -> Path:
    return get_hermes_home() / "google_accounts"


def ensure_accounts_root() -> Path:
    root = get_accounts_root()
    root.mkdir(parents=True, exist_ok=True)
    return root


def validate_account_alias(alias: str) -> str:
    alias = (alias or "").strip().lower()
    if not ACCOUNT_RE.fullmatch(alias):
        raise ValueError("Account alias must match ^[a-z0-9][a-z0-9-]{0,31}$")
    return alias


def get_account_dir(alias: str) -> Path:
    alias = validate_account_alias(alias)
    return ensure_accounts_root() / alias


def ensure_account_dir(alias: str) -> Path:
    path = get_account_dir(alias)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_token_path(alias: str) -> Path:
    return get_account_dir(alias) / "token.json"


def get_client_secret_path(alias: str) -> Path:
    return get_account_dir(alias) / "client_secret.json"


def get_pending_auth_path(alias: str) -> Path:
    return get_account_dir(alias) / "oauth_pending.json"


def get_metadata_path(alias: str) -> Path:
    return get_account_dir(alias) / "metadata.json"


def get_default_account_path() -> Path:
    return ensure_accounts_root() / "default_account.json"


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    try:
        return json.loads(path.read_text())
    except Exception:
        return {} if default is None else default


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def list_accounts() -> list[dict[str, Any]]:
    root = ensure_accounts_root()
    results: list[dict[str, Any]] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        metadata = load_json(child / "metadata.json", default={})
        results.append(
            {
                "alias": child.name,
                "email": metadata.get("email", ""),
                "display_name": metadata.get("display_name", ""),
                "auth_status": metadata.get("auth_status", "unknown"),
                "last_authenticated_at": metadata.get("last_authenticated_at", ""),
            }
        )
    return results


def load_account_metadata(alias: str) -> dict[str, Any]:
    alias = validate_account_alias(alias)
    return load_json(get_metadata_path(alias), default={})


def save_account_metadata(alias: str, data: dict[str, Any]) -> dict[str, Any]:
    alias = validate_account_alias(alias)
    current = load_account_metadata(alias)
    merged = {
        "schema_version": SCHEMA_VERSION,
        "alias": alias,
        "created_at": current.get("created_at", now_iso()),
        **current,
        **data,
    }
    save_json(get_metadata_path(alias), merged)
    return merged


def get_default_account() -> str:
    data = load_json(get_default_account_path(), default={})
    value = (data.get("default_account") or "").strip().lower()
    return value


def set_default_account(alias: str) -> dict[str, Any]:
    alias = validate_account_alias(alias)
    data = {"schema_version": SCHEMA_VERSION, "default_account": alias, "updated_at": now_iso()}
    save_json(get_default_account_path(), data)
    return data


def resolve_account_or_default(requested_alias: str | None) -> str:
    if requested_alias:
        return validate_account_alias(requested_alias)

    accounts = list_accounts()
    if len(accounts) == 1:
        return accounts[0]["alias"]

    default_alias = get_default_account()
    if default_alias:
        return validate_account_alias(default_alias)

    if not accounts:
        raise RuntimeError("No configured Google accounts. Run setup first.")

    aliases = ", ".join(a["alias"] for a in accounts)
    raise RuntimeError(f"Multiple Google accounts exist with no default set. Use --account. Available: {aliases}")


def mark_account_used(alias: str) -> dict[str, Any]:
    metadata = load_account_metadata(alias)
    metadata["last_used_at"] = now_iso()
    return save_account_metadata(alias, metadata)


def detect_legacy_single_account() -> dict[str, str]:
    home = get_hermes_home()
    mapping = {
        "token": str(home / "google_token.json"),
        "client_secret": str(home / "google_client_secret.json"),
        "oauth_pending": str(home / "google_oauth_pending.json"),
    }
    return {k: v for k, v in mapping.items() if Path(v).exists()}

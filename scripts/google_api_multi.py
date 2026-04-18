#!/usr/bin/env python3
"""Account-aware Google Workspace API CLI for Hermes Agent."""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from pathlib import Path

from account_store import load_account_metadata, mark_account_used, resolve_account_or_default

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

ACTIVE_ALIAS: str | None = None


def _require_alias() -> str:
    if not ACTIVE_ALIAS:
        print("Internal error: no active account alias selected.", file=sys.stderr)
        raise SystemExit(1)
    return ACTIVE_ALIAS


def _account_label() -> dict:
    alias = _require_alias()
    metadata = load_account_metadata(alias)
    return {
        "account": {
            "alias": alias,
            "email": metadata.get("email", ""),
        }
    }


def _print_json(payload) -> None:
    if isinstance(payload, dict):
        data = {**_account_label(), **payload}
    elif isinstance(payload, list):
        data = {
            **_account_label(),
            "items": payload,
        }
    else:
        data = {
            **_account_label(),
            "result": payload,
        }
    print(json.dumps(data, indent=2, ensure_ascii=False))


def install_deps() -> bool:
    try:
        import googleapiclient  # noqa: F401
        import google_auth_oauthlib  # noqa: F401
        return True
    except ImportError:
        pass

    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet", *REQUIRED_PACKAGES],
            stdout=subprocess.DEVNULL,
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Failed to install dependencies: {e}", file=sys.stderr)
        return False


def _ensure_deps() -> None:
    try:
        import googleapiclient  # noqa: F401
        import google_auth_oauthlib  # noqa: F401
    except ImportError:
        if not install_deps():
            raise SystemExit(1)


def _token_path() -> Path:
    alias = _require_alias()
    from account_store import get_token_path

    return get_token_path(alias)


def _missing_scopes() -> list[str]:
    try:
        payload = json.loads(_token_path().read_text())
    except Exception:
        return []
    raw = payload.get("scopes") or payload.get("scope")
    if not raw:
        return []
    granted = {s.strip() for s in (raw.split() if isinstance(raw, str) else raw) if s.strip()}
    return sorted(scope for scope in SCOPES if scope not in granted)


def get_credentials():
    _ensure_deps()
    token_path = _token_path()
    if not token_path.exists():
        alias = _require_alias()
        print(
            f"Not authenticated for account '{alias}'. Run setup_multi.py --account {alias} first.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_path.write_text(creds.to_json())
    if not creds.valid:
        print("Token is invalid. Re-run setup.", file=sys.stderr)
        raise SystemExit(1)

    missing_scopes = _missing_scopes()
    if missing_scopes:
        print(
            "Token is valid but missing Google Workspace scopes required by this skill.",
            file=sys.stderr,
        )
        for scope in missing_scopes:
            print(f"  - {scope}", file=sys.stderr)
        print(
            f"Re-run setup_multi.py for account '{_require_alias()}' to restore full access.",
            file=sys.stderr,
        )
        raise SystemExit(1)
    return creds


def build_service(api, version):
    from googleapiclient.discovery import build

    return build(api, version, credentials=get_credentials())


# =========================================================================
# Gmail
# =========================================================================

def gmail_search(args):
    service = build_service("gmail", "v1")
    results = service.users().messages().list(userId="me", q=args.query, maxResults=args.max).execute()
    messages = results.get("messages", [])
    if not messages:
        _print_json([])
        return

    output = []
    for msg_meta in messages:
        msg = service.users().messages().get(
            userId="me",
            id=msg_meta["id"],
            format="metadata",
            metadataHeaders=["From", "To", "Subject", "Date"],
        ).execute()
        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        output.append(
            {
                "id": msg["id"],
                "threadId": msg["threadId"],
                "from": headers.get("From", ""),
                "to": headers.get("To", ""),
                "subject": headers.get("Subject", ""),
                "date": headers.get("Date", ""),
                "snippet": msg.get("snippet", ""),
                "labels": msg.get("labelIds", []),
            }
        )
    _print_json(output)


def gmail_get(args):
    service = build_service("gmail", "v1")
    msg = service.users().messages().get(userId="me", id=args.message_id, format="full").execute()

    headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}

    body = ""
    payload = msg.get("payload", {})
    if payload.get("body", {}).get("data"):
        body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
    elif payload.get("parts"):
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
                break
        if not body:
            for part in payload["parts"]:
                if part.get("mimeType") == "text/html" and part.get("body", {}).get("data"):
                    body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
                    break

    _print_json(
        {
            "id": msg["id"],
            "threadId": msg["threadId"],
            "from": headers.get("From", ""),
            "to": headers.get("To", ""),
            "subject": headers.get("Subject", ""),
            "date": headers.get("Date", ""),
            "labels": msg.get("labelIds", []),
            "body": body,
        }
    )


def gmail_send(args):
    service = build_service("gmail", "v1")
    message = MIMEText(args.body, "html" if args.html else "plain")
    message["to"] = args.to
    message["subject"] = args.subject
    if args.cc:
        message["cc"] = args.cc

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    body = {"raw": raw}
    if args.thread_id:
        body["threadId"] = args.thread_id

    result = service.users().messages().send(userId="me", body=body).execute()
    _print_json({"status": "sent", "id": result["id"], "threadId": result.get("threadId", "")})


def gmail_reply(args):
    service = build_service("gmail", "v1")
    original = service.users().messages().get(
        userId="me",
        id=args.message_id,
        format="metadata",
        metadataHeaders=["From", "Subject", "Message-ID"],
    ).execute()
    headers = {h["name"]: h["value"] for h in original.get("payload", {}).get("headers", [])}

    subject = headers.get("Subject", "")
    if not subject.startswith("Re:"):
        subject = f"Re: {subject}"

    message = MIMEText(args.body)
    message["to"] = headers.get("From", "")
    message["subject"] = subject
    if headers.get("Message-ID"):
        message["In-Reply-To"] = headers["Message-ID"]
        message["References"] = headers["Message-ID"]

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    body = {"raw": raw, "threadId": original["threadId"]}

    result = service.users().messages().send(userId="me", body=body).execute()
    _print_json({"status": "sent", "id": result["id"], "threadId": result.get("threadId", "")})


def gmail_labels(args):
    service = build_service("gmail", "v1")
    results = service.users().labels().list(userId="me").execute()
    labels = [{"id": l["id"], "name": l["name"], "type": l.get("type", "")} for l in results.get("labels", [])]
    _print_json(labels)


def gmail_modify(args):
    service = build_service("gmail", "v1")
    body = {}
    if args.add_labels:
        body["addLabelIds"] = args.add_labels.split(",")
    if args.remove_labels:
        body["removeLabelIds"] = args.remove_labels.split(",")
    result = service.users().messages().modify(userId="me", id=args.message_id, body=body).execute()
    _print_json({"id": result["id"], "labels": result.get("labelIds", [])})


# =========================================================================
# Calendar
# =========================================================================

def calendar_list(args):
    service = build_service("calendar", "v3")
    now = datetime.now(timezone.utc)
    time_min = args.start or now.isoformat()
    time_max = args.end or (now + timedelta(days=7)).isoformat()

    normalized = []
    for val in [time_min, time_max]:
        if "T" in val and "Z" not in val and "+" not in val and "-" not in val[11:]:
            val += "Z"
        normalized.append(val)
    time_min, time_max = normalized

    results = service.events().list(
        calendarId=args.calendar,
        timeMin=time_min,
        timeMax=time_max,
        maxResults=args.max,
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    events = []
    for e in results.get("items", []):
        events.append(
            {
                "id": e["id"],
                "summary": e.get("summary", "(no title)"),
                "start": e.get("start", {}).get("dateTime", e.get("start", {}).get("date", "")),
                "end": e.get("end", {}).get("dateTime", e.get("end", {}).get("date", "")),
                "location": e.get("location", ""),
                "description": e.get("description", ""),
                "status": e.get("status", ""),
                "htmlLink": e.get("htmlLink", ""),
            }
        )
    _print_json(events)


def calendar_create(args):
    service = build_service("calendar", "v3")
    event = {
        "summary": args.summary,
        "start": {"dateTime": args.start},
        "end": {"dateTime": args.end},
    }
    if args.location:
        event["location"] = args.location
    if args.description:
        event["description"] = args.description
    if args.attendees:
        event["attendees"] = [{"email": e.strip()} for e in args.attendees.split(",")]

    result = service.events().insert(calendarId=args.calendar, body=event).execute()
    _print_json(
        {
            "status": "created",
            "id": result["id"],
            "summary": result.get("summary", ""),
            "htmlLink": result.get("htmlLink", ""),
        }
    )


def calendar_delete(args):
    service = build_service("calendar", "v3")
    service.events().delete(calendarId=args.calendar, eventId=args.event_id).execute()
    _print_json({"status": "deleted", "eventId": args.event_id})


# =========================================================================
# Drive
# =========================================================================

def drive_search(args):
    service = build_service("drive", "v3")
    query = f"fullText contains '{args.query}'" if not args.raw_query else args.query
    results = service.files().list(
        q=query,
        pageSize=args.max,
        fields="files(id, name, mimeType, modifiedTime, webViewLink)",
    ).execute()
    _print_json(results.get("files", []))


# =========================================================================
# Contacts
# =========================================================================

def contacts_list(args):
    service = build_service("people", "v1")
    results = service.people().connections().list(
        resourceName="people/me",
        pageSize=args.max,
        personFields="names,emailAddresses,phoneNumbers",
    ).execute()
    contacts = []
    for person in results.get("connections", []):
        names = person.get("names", [{}])
        emails = person.get("emailAddresses", [])
        phones = person.get("phoneNumbers", [])
        contacts.append(
            {
                "name": names[0].get("displayName", "") if names else "",
                "emails": [e.get("value", "") for e in emails],
                "phones": [p.get("value", "") for p in phones],
            }
        )
    _print_json(contacts)


# =========================================================================
# Sheets
# =========================================================================

def sheets_get(args):
    service = build_service("sheets", "v4")
    result = service.spreadsheets().values().get(spreadsheetId=args.sheet_id, range=args.range).execute()
    _print_json(result.get("values", []))


def sheets_update(args):
    service = build_service("sheets", "v4")
    values = json.loads(args.values)
    body = {"values": values}
    result = service.spreadsheets().values().update(
        spreadsheetId=args.sheet_id,
        range=args.range,
        valueInputOption="USER_ENTERED",
        body=body,
    ).execute()
    _print_json({"updatedCells": result.get("updatedCells", 0), "updatedRange": result.get("updatedRange", "")})


def sheets_append(args):
    service = build_service("sheets", "v4")
    values = json.loads(args.values)
    body = {"values": values}
    result = service.spreadsheets().values().append(
        spreadsheetId=args.sheet_id,
        range=args.range,
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body=body,
    ).execute()
    _print_json({"updatedCells": result.get("updates", {}).get("updatedCells", 0)})


# =========================================================================
# Docs
# =========================================================================

def docs_get(args):
    service = build_service("docs", "v1")
    doc = service.documents().get(documentId=args.doc_id).execute()
    text_parts = []
    for element in doc.get("body", {}).get("content", []):
        paragraph = element.get("paragraph", {})
        for pe in paragraph.get("elements", []):
            text_run = pe.get("textRun", {})
            if text_run.get("content"):
                text_parts.append(text_run["content"])
    _print_json(
        {
            "title": doc.get("title", ""),
            "documentId": doc.get("documentId", ""),
            "body": "".join(text_parts),
        }
    )


# =========================================================================
# CLI parser
# =========================================================================

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Multi-account Google Workspace API for Hermes Agent")
    parser.add_argument("--account", help="Named account alias, e.g. work or personal")
    sub = parser.add_subparsers(dest="service", required=True)

    gmail = sub.add_parser("gmail")
    gmail_sub = gmail.add_subparsers(dest="action", required=True)

    p = gmail_sub.add_parser("search")
    p.add_argument("query", help="Gmail search query (e.g. 'is:unread')")
    p.add_argument("--max", type=int, default=10)
    p.set_defaults(func=gmail_search)

    p = gmail_sub.add_parser("get")
    p.add_argument("message_id")
    p.set_defaults(func=gmail_get)

    p = gmail_sub.add_parser("send")
    p.add_argument("--to", required=True)
    p.add_argument("--subject", required=True)
    p.add_argument("--body", required=True)
    p.add_argument("--cc", default="")
    p.add_argument("--html", action="store_true", help="Send body as HTML")
    p.add_argument("--thread-id", default="", help="Thread ID for threading")
    p.set_defaults(func=gmail_send)

    p = gmail_sub.add_parser("reply")
    p.add_argument("message_id", help="Message ID to reply to")
    p.add_argument("--body", required=True)
    p.set_defaults(func=gmail_reply)

    p = gmail_sub.add_parser("labels")
    p.set_defaults(func=gmail_labels)

    p = gmail_sub.add_parser("modify")
    p.add_argument("message_id")
    p.add_argument("--add-labels", default="", help="Comma-separated label IDs to add")
    p.add_argument("--remove-labels", default="", help="Comma-separated label IDs to remove")
    p.set_defaults(func=gmail_modify)

    cal = sub.add_parser("calendar")
    cal_sub = cal.add_subparsers(dest="action", required=True)

    p = cal_sub.add_parser("list")
    p.add_argument("--start", default="", help="Start time (ISO 8601)")
    p.add_argument("--end", default="", help="End time (ISO 8601)")
    p.add_argument("--max", type=int, default=25)
    p.add_argument("--calendar", default="primary")
    p.set_defaults(func=calendar_list)

    p = cal_sub.add_parser("create")
    p.add_argument("--summary", required=True)
    p.add_argument("--start", required=True, help="Start (ISO 8601 with timezone)")
    p.add_argument("--end", required=True, help="End (ISO 8601 with timezone)")
    p.add_argument("--location", default="")
    p.add_argument("--description", default="")
    p.add_argument("--attendees", default="", help="Comma-separated email addresses")
    p.add_argument("--calendar", default="primary")
    p.set_defaults(func=calendar_create)

    p = cal_sub.add_parser("delete")
    p.add_argument("event_id")
    p.add_argument("--calendar", default="primary")
    p.set_defaults(func=calendar_delete)

    drv = sub.add_parser("drive")
    drv_sub = drv.add_subparsers(dest="action", required=True)

    p = drv_sub.add_parser("search")
    p.add_argument("query")
    p.add_argument("--max", type=int, default=10)
    p.add_argument("--raw-query", action="store_true", help="Use query as raw Drive API query")
    p.set_defaults(func=drive_search)

    con = sub.add_parser("contacts")
    con_sub = con.add_subparsers(dest="action", required=True)

    p = con_sub.add_parser("list")
    p.add_argument("--max", type=int, default=50)
    p.set_defaults(func=contacts_list)

    sh = sub.add_parser("sheets")
    sh_sub = sh.add_subparsers(dest="action", required=True)

    p = sh_sub.add_parser("get")
    p.add_argument("sheet_id")
    p.add_argument("range")
    p.set_defaults(func=sheets_get)

    p = sh_sub.add_parser("update")
    p.add_argument("sheet_id")
    p.add_argument("range")
    p.add_argument("--values", required=True, help="JSON array of arrays")
    p.set_defaults(func=sheets_update)

    p = sh_sub.add_parser("append")
    p.add_argument("sheet_id")
    p.add_argument("range")
    p.add_argument("--values", required=True, help="JSON array of arrays")
    p.set_defaults(func=sheets_append)

    docs = sub.add_parser("docs")
    docs_sub = docs.add_subparsers(dest="action", required=True)

    p = docs_sub.add_parser("get")
    p.add_argument("doc_id")
    p.set_defaults(func=docs_get)

    return parser


def main() -> int:
    global ACTIVE_ALIAS

    parser = build_parser()
    args = parser.parse_args()

    try:
        ACTIVE_ALIAS = resolve_account_or_default(args.account)
    except Exception as e:
        print(str(e), file=sys.stderr)
        return 1

    mark_account_used(ACTIVE_ALIAS)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CodeBuddy credits claim tool.

Batch-claims activity rewards (DeepSeek compensation, welcome gift) for
CodeBuddy accounts managed by Cockpit Tools.

Credential sources (pick one):
  1. Cockpit Tools local encrypted storage (default): decrypts
     <cockpit-root>/secure-account-storage.key together with
     codebuddy_accounts/*.json and workbuddy_accounts/*.json (AES-256-GCM).
     Read-only, nothing is written back to Cockpit Tools.
  2. An exported JSON file via --data (array of account objects).

Commands:
  list    Show accounts and token validity.
  claim   Check and claim rewards for every account (use --dry-run to
          only report status without claiming).

The global options --cockpit-root, --data and --account are accepted
both before and after the command name.

Examples:
  python codebuddy_claim.py list
  python codebuddy_claim.py claim --dry-run
  python codebuddy_claim.py claim --account user@example.com

Requires Python 3.9 or newer.
"""

import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

if sys.version_info < (3, 9):
    sys.stderr.write("Python 3.9 or newer is required.\n")
    raise SystemExit(1)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

KEY_FILE = "secure-account-storage.key"
ACCOUNT_DIRS = ("codebuddy_accounts", "workbuddy_accounts")
COCKPIT_ROOT_CANDIDATES = (".cockpit_tools", ".antigravity_cockpit")

HTTP_TIMEOUT = 25
HTTP_RETRIES = 2
INTER_ACCOUNT_DELAY = 1.5  # seconds, keep request pace gentle

CHECK_ENDPOINTS = (
    ("/billing/meter/compensation-status", "/billing/meter/claim-compensation", "compensation"),
    ("/billing/meter/check-gift-claimed", "/billing/meter/claim-gift", "gift"),
)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
)

HISTORY_DIR = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "codebuddy-claim"
)
HISTORY_FILE = os.path.join(HISTORY_DIR, "claim-history.jsonl")
MAX_HISTORY_BYTES = 5 * 1024 * 1024  # rotate to .1 past this size

_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # direct, no proxy


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


def http_post_json(url, token, body=b"{}", form=False):
    """POST with Bearer auth. Returns (http_status, parsed_body_or_None)."""
    req = urllib.request.Request(url, method="POST", data=body)
    if form:
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
    else:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    req.add_header("X-Client-Platform", "web")
    req.add_header("User-Agent", USER_AGENT)

    last_error = None
    for attempt in range(1, HTTP_RETRIES + 1):
        try:
            with _opener.open(req, timeout=HTTP_TIMEOUT) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", "replace")
            try:
                payload = json.loads(raw)
            except ValueError:
                payload = {"raw": raw[:200]}
            if exc.code >= 500 and attempt < HTTP_RETRIES:
                last_error = exc
                time.sleep(2)
                continue
            return exc.code, payload
        except Exception as exc:  # network errors: retry
            last_error = exc
            if attempt < HTTP_RETRIES:
                time.sleep(2)
                continue
    raise RuntimeError("request failed after %d attempts: %s" % (HTTP_RETRIES, last_error))


def refresh_access_token(account):
    """Refresh an expired access token via the Keycloak token endpoint."""
    url = "https://%s/auth/realms/copilot/protocol/openid-connect/token" % account["domain"]
    body = urllib.parse.urlencode(
        {
            "grant_type": "refresh_token",
            "client_id": "console",
            "refresh_token": account["refresh_token"],
        }
    ).encode("utf-8")
    status, payload = http_post_json(url, token=None, body=body, form=True)
    if status == 200 and isinstance(payload, dict) and payload.get("access_token"):
        account["access_token"] = payload["access_token"]
        if payload.get("refresh_token"):
            account["refresh_token"] = payload["refresh_token"]
        if payload.get("expires_in"):
            account["expires_at"] = int((time.time() + payload["expires_in"]) * 1000)
        return True
    return False


def call_endpoint(account, path):
    """Call an endpoint for an account; refresh token once on 401."""
    url = "https://%s%s" % (account["domain"], path)
    status, payload = http_post_json(url, account["access_token"])
    if status == 401 and account.get("refresh_token"):
        if refresh_access_token(account):
            status, payload = http_post_json(url, account["access_token"])
    return status, payload


# ---------------------------------------------------------------------------
# Credential loading
# ---------------------------------------------------------------------------


def account_from_obj(obj, source):
    if not isinstance(obj, dict):
        return None
    domain = obj.get("domain")
    token = obj.get("access_token")
    if not isinstance(domain, str) or not domain:
        return None
    if not isinstance(token, str) or not token:
        return None
    return {
        "id": str(obj.get("id") or ""),
        "email": str(obj.get("email") or ""),
        "uid": str(obj.get("uid") or ""),
        "nickname": str(obj.get("nickname") or ""),
        "domain": domain,
        "access_token": token,
        "refresh_token": str(obj.get("refresh_token") or ""),
        "expires_at": obj.get("expires_at"),
        "status": str(obj.get("status") or ""),
        "source": source,
    }


def account_key(account):
    """Dedup key for one account: id, else uid, else the token itself."""
    return account["id"] or account["uid"] or account["access_token"]


def token_iat(token):
    """Issue time of a JWT access token; 0 when unparsable."""
    try:
        part = token.split(".")[1]
        part += "=" * (-len(part) % 4)
        return int(json.loads(base64.urlsafe_b64decode(part)).get("iat", 0))
    except Exception:
        return 0


def load_accounts_from_cockpit(root):
    """Decrypt Cockpit Tools account storage (read-only)."""
    key_path = os.path.join(root, KEY_FILE)
    if not os.path.isfile(key_path):
        raise FileNotFoundError("key file not found: %s" % key_path)
    key = base64.b64decode(open(key_path, encoding="utf-8").read().strip())
    aead = AESGCM(key)

    best = {}  # account_key -> (iat, account)
    for sub in ACCOUNT_DIRS:
        folder = os.path.join(root, sub)
        if not os.path.isdir(folder):
            continue
        for name in sorted(os.listdir(folder)):
            if not name.endswith(".json"):
                continue
            path = os.path.join(folder, name)
            try:
                blob = json.load(open(path, encoding="utf-8"))
                plain = aead.decrypt(
                    base64.b64decode(blob["nonce"]),
                    base64.b64decode(blob["ciphertext"]),
                    None,
                )
                obj = json.loads(plain.decode("utf-8", "replace"))
            except Exception as exc:
                print("  [skip] %s: %s" % (path, exc))
                continue
            account = account_from_obj(obj, "cockpit")
            if not account:
                continue
            key = account_key(account)
            iat = token_iat(account["access_token"])
            prev = best.get(key)
            if prev is None or iat > prev[0]:
                best[key] = (iat, account)
    return [
        item[1]
        for item in sorted(best.values(), key=lambda x: (x[1]["email"], x[1]["uid"]))
    ]


def load_accounts_from_export(path):
    data = json.load(open(path, encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("accounts", [])
    accounts = []
    for obj in data:
        account = account_from_obj(obj, "export")
        if account:
            accounts.append(account)
    return accounts


def load_accounts(args):
    if args.data:
        return load_accounts_from_export(args.data)
    root = args.cockpit_root or detect_cockpit_root()
    if not root:
        raise FileNotFoundError(
            "cannot locate Cockpit Tools data root; pass --cockpit-root or --data"
        )
    print("cockpit root: %s" % root)
    return load_accounts_from_cockpit(root)


def detect_cockpit_root():
    env_root = os.environ.get("COCKPIT_TOOLS_HOME", "").strip()
    if env_root and os.path.isfile(os.path.join(env_root, KEY_FILE)):
        return env_root
    home = os.path.expanduser("~")
    for name in COCKPIT_ROOT_CANDIDATES:
        candidate = os.path.join(home, name)
        if os.path.isfile(os.path.join(candidate, KEY_FILE)):
            return candidate
    return None


def filter_accounts(accounts, needle):
    if not needle:
        return accounts
    low = needle.lower()
    return [
        a
        for a in accounts
        if low in a["email"].lower() or low in a["id"].lower() or low in a["uid"].lower()
    ]


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def token_state(account):
    expires_at = account.get("expires_at")
    if not expires_at:
        return "UNKNOWN"
    seconds_left = expires_at / 1000 - time.time()
    if seconds_left <= 0:
        return "EXPIRED"
    days = seconds_left / 86400
    return "VALID %dd" % days if days >= 1 else "VALID %.1fh" % (seconds_left / 3600)


def fmt_ts(ms):
    try:
        return datetime.fromtimestamp(ms / 1000).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return "?"


def cmd_list(args):
    accounts = filter_accounts(load_accounts(args), args.account)
    print("accounts: %d" % len(accounts))
    for idx, acc in enumerate(accounts, 1):
        print(
            "%2d. %-18s uid=%s %-17s token=%-12s expires=%s status=%s"
            % (
                idx,
                acc["email"],
                acc["uid"][:8],
                acc["domain"],
                token_state(acc),
                fmt_ts(acc.get("expires_at")) if acc.get("expires_at") else "?",
                acc.get("status") or "?",
            )
        )


def short_body(payload):
    if payload is None:
        return ""
    text = json.dumps(payload, ensure_ascii=True)
    return text[:160]


def check_and_claim(account, check_path, claim_path, label, dry_run):
    """Return a status string for one reward item of one account."""
    status, payload = call_endpoint(account, check_path)
    if status != 200 or not isinstance(payload, dict) or payload.get("code") != 0:
        return "CHECK-FAILED http=%s %s" % (status, short_body(payload))

    info = payload.get("data") or {}
    if not info.get("active"):
        return "INACTIVE"
    if info.get("claimed"):
        when = info.get("claimed_text") or info.get("claimed_at") or ""
        return ("ALREADY-CLAIMED %s" % when).strip()
    if dry_run:
        return "CLAIMABLE credit=%s" % info.get("credit_num", "?")

    status, payload = call_endpoint(account, claim_path)
    if status == 200 and isinstance(payload, dict) and payload.get("code") == 0:
        credit = (payload.get("data") or {}).get("credit_num", info.get("credit_num", "?"))
        return "CLAIMED credit=%s" % credit
    return "CLAIM-FAILED http=%s %s" % (status, short_body(payload))


def cmd_claim(args):
    accounts = filter_accounts(load_accounts(args), args.account)
    if not accounts:
        print("no accounts matched; nothing to do")
        return
    print("accounts to process: %d%s" % (len(accounts), ", DRY-RUN (no claim calls)" if args.dry_run else ""))

    history_rows = []
    failed_items = 0
    for idx, acc in enumerate(accounts, 1):
        print(
            "[%d/%d] %s uid=%s domain=%s" % (idx, len(accounts), acc["email"], acc["uid"][:8], acc["domain"])
        )
        row = {"email": acc["email"], "id": acc["id"], "domain": acc["domain"], "items": {}}
        for check_path, claim_path, label in CHECK_ENDPOINTS:
            try:
                result = check_and_claim(acc, check_path, claim_path, label, args.dry_run)
            except Exception as exc:
                result = "ERROR %s" % exc
            if "FAILED" in result or "ERROR" in result:
                failed_items += 1
            row["items"][label] = result
            print("      %-13s %s" % (label + ":", result))
            time.sleep(0.8)
        history_rows.append(row)
        if idx < len(accounts):
            time.sleep(INTER_ACCOUNT_DELAY)

    print()
    print("summary: accounts=%d failed_items=%d%s" % (len(accounts), failed_items, " (dry-run, nothing claimed)" if args.dry_run else ""))
    append_history({"ts": datetime.now().isoformat(timespec="seconds"), "mode": "dry-run" if args.dry_run else "claim", "results": history_rows})
    print("history: %s" % HISTORY_FILE)
    if failed_items:
        sys.exit(2)


def rotate_history():
    """Move the history file aside once it grows past MAX_HISTORY_BYTES."""
    if not os.path.isfile(HISTORY_FILE):
        return
    try:
        if os.path.getsize(HISTORY_FILE) < MAX_HISTORY_BYTES:
            return
        backup = HISTORY_FILE + ".1"
        if os.path.exists(backup):
            os.remove(backup)
        os.replace(HISTORY_FILE, backup)
        print("history rotated to: %s" % backup)
    except OSError as exc:
        print("warn: cannot rotate history: %s" % exc)


def append_history(entry):
    try:
        os.makedirs(HISTORY_DIR, exist_ok=True)
        rotate_history()
        with open(HISTORY_FILE, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=True) + "\n")
    except OSError as exc:
        print("warn: cannot write history: %s" % exc)


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------


def add_global_options(parser, suppress_defaults=False):
    """Register the shared options on the main parser and on each subcommand.

    Subcommands use SUPPRESS so an option given before the command name
    survives when it is not repeated after the command name.
    """
    default = argparse.SUPPRESS if suppress_defaults else None
    parser.add_argument("--cockpit-root", default=default, help="Cockpit Tools data root (default: auto-detect)")
    parser.add_argument("--data", default=default, help="exported account JSON file (overrides cockpit source)")
    parser.add_argument("--account", default=default, help="filter by email/id/uid substring")


def build_parser():
    parser = argparse.ArgumentParser(description="CodeBuddy credits claim tool")
    add_global_options(parser)
    sub = parser.add_subparsers(dest="command", required=True)

    list_cmd = sub.add_parser("list", help="show accounts and token validity")
    add_global_options(list_cmd, suppress_defaults=True)

    claim = sub.add_parser("claim", help="check and claim rewards for all accounts")
    add_global_options(claim, suppress_defaults=True)
    claim.add_argument("--dry-run", action="store_true", help="only report status, do not claim")
    return parser


def main():
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args()
    if args.command == "list":
        cmd_list(args)
    elif args.command == "claim":
        cmd_claim(args)


if __name__ == "__main__":
    main()

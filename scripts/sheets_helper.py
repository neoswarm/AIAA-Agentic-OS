#!/usr/bin/env python3
"""
sheets_helper.py — Google Sheets integration for D100 pipeline tracking.

Authentication: Google service account JSON key.
Set GOOGLE_SERVICE_ACCOUNT_JSON in .env (path to the JSON file).
The service account must have Editor access to the target sheet.

Usage:
    from sheets_helper import append_to_tracking_sheet, read_tracking_sheet, update_cell

Sheet structure (tab: "D100 Pipeline"):
    Company Name | Website | Run Date | Deliverables URL | App URL | Preview URL |
    Loom Status | Loom ID | Loom Deployed | Organic Traffic | Keywords | Quick Wins |
    Page Opened | App Opened | Booked Call | Outreach Status | Notes
"""

import json
import os
import sys
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path


# ── Header row definition (order matters) ─────────────────────────────────────
HEADERS = [
    "Company Name", "Website", "Run Date", "Deliverables URL", "App URL",
    "Preview URL", "Loom Status", "Loom ID", "Loom Deployed",
    "Organic Traffic", "Keywords", "Quick Wins",
    "Page Opened", "App Opened", "Booked Call",
    "Outreach Status", "Notes",
]

SHEET_TAB = "D100 Pipeline"


# ── Auth ───────────────────────────────────────────────────────────────────────
def _get_service_account_key() -> dict:
    """Load service account JSON from path in env or inline JSON string."""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    env_path = project_root / ".env"

    sa_path = None
    sa_inline = None

    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("GOOGLE_SERVICE_ACCOUNT_JSON="):
                val = line.split("=", 1)[1].strip()
                if val.startswith("{"):
                    sa_inline = val
                else:
                    sa_path = val.strip("'\"")
                break

    if not sa_path and not sa_inline:
        val = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
        if val.startswith("{"):
            sa_inline = val
        elif val:
            sa_path = val

    if sa_inline:
        return json.loads(sa_inline)
    if sa_path:
        return json.loads(Path(sa_path).read_text(encoding="utf-8"))

    raise RuntimeError(
        "GOOGLE_SERVICE_ACCOUNT_JSON not set in .env — "
        "set to path of service account JSON or inline JSON string"
    )


def _get_access_token(key: dict) -> str:
    """Get OAuth2 access token from service account key via JWT (no external libs)."""
    import base64
    import hashlib
    import hmac
    import struct
    import time

    # ── Build JWT ──────────────────────────────────────────────────────────────
    now = int(time.time())
    header = base64.urlsafe_b64encode(
        json.dumps({"alg": "RS256", "typ": "JWT"}).encode()
    ).rstrip(b"=").decode()

    claim = base64.urlsafe_b64encode(json.dumps({
        "iss":   key["client_email"],
        "scope": "https://www.googleapis.com/auth/spreadsheets",
        "aud":   "https://oauth2.googleapis.com/token",
        "iat":   now,
        "exp":   now + 3600,
    }).encode()).rstrip(b"=").decode()

    # Sign with RS256 using the private key — requires cryptography or fallback
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding as _padding
        from cryptography.hazmat.backends import default_backend

        private_key_pem = key["private_key"].encode()
        private_key = serialization.load_pem_private_key(
            private_key_pem, password=None, backend=default_backend()
        )
        signing_input = f"{header}.{claim}".encode()
        signature = private_key.sign(signing_input, _padding.PKCS1v15(), hashes.SHA256())
        sig_b64 = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()
    except ImportError:
        raise RuntimeError(
            "The 'cryptography' package is required for Google Sheets auth. "
            "Install it: pip install cryptography"
        )

    jwt_token = f"{header}.{claim}.{sig_b64}"

    # ── Exchange JWT for access token ──────────────────────────────────────────
    body = urllib.parse.urlencode({
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": jwt_token,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        token_data = json.loads(resp.read().decode("utf-8"))

    if "access_token" not in token_data:
        raise RuntimeError(f"Failed to get access token: {token_data}")

    return token_data["access_token"]


def _sheets_request(method: str, url: str, token: str, body: dict = None):
    """Make a Sheets API request. Returns parsed JSON response."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ── Public API ─────────────────────────────────────────────────────────────────
def _ensure_headers(sheets_id: str, token: str):
    """Create header row if sheet is empty."""
    url = (f"https://sheets.googleapis.com/v4/spreadsheets/{sheets_id}/values/"
           f"{urllib.parse.quote(SHEET_TAB)}!A1:A1")
    try:
        result = _sheets_request("GET", url, token)
        if result.get("values"):
            return  # Headers already exist
    except Exception:
        pass

    # Write headers
    write_url = (f"https://sheets.googleapis.com/v4/spreadsheets/{sheets_id}/values/"
                 f"{urllib.parse.quote(SHEET_TAB)}!A1?valueInputOption=RAW")
    _sheets_request("PUT", write_url, token, {"values": [HEADERS]})


def append_to_tracking_sheet(sheets_id: str, row_data: dict):
    """Append a row to the D100 Pipeline sheet. Creates headers if missing."""
    key = _get_service_account_key()
    token = _get_access_token(key)
    _ensure_headers(sheets_id, token)

    row = [str(row_data.get(h, "")) for h in HEADERS]
    url = (f"https://sheets.googleapis.com/v4/spreadsheets/{sheets_id}/values/"
           f"{urllib.parse.quote(SHEET_TAB)}!A1:append?valueInputOption=USER_ENTERED"
           f"&insertDataOption=INSERT_ROWS")
    _sheets_request("POST", url, token, {"values": [row]})


def read_tracking_sheet(sheets_id: str) -> list[dict]:
    """Read all rows from D100 Pipeline. Returns list of dicts keyed by header."""
    key = _get_service_account_key()
    token = _get_access_token(key)

    url = (f"https://sheets.googleapis.com/v4/spreadsheets/{sheets_id}/values/"
           f"{urllib.parse.quote(SHEET_TAB)}")
    result = _sheets_request("GET", url, token)
    values = result.get("values", [])
    if len(values) < 2:
        return []

    headers = values[0]
    return [
        {headers[j]: row[j] if j < len(row) else "" for j in range(len(headers))}
        for row in values[1:]
    ]


def update_cell(sheets_id: str, row_index: int, column_name: str, value: str):
    """Update a single cell. row_index is 0-based (0 = first data row, not header)."""
    key = _get_service_account_key()
    token = _get_access_token(key)

    col_idx = HEADERS.index(column_name) if column_name in HEADERS else None
    if col_idx is None:
        raise ValueError(f"Column '{column_name}' not in HEADERS")

    col_letter = chr(ord("A") + col_idx)
    sheet_row = row_index + 2  # +1 for header, +1 for 1-based index
    cell_range = f"{SHEET_TAB}!{col_letter}{sheet_row}"
    url = (f"https://sheets.googleapis.com/v4/spreadsheets/{sheets_id}/values/"
           f"{urllib.parse.quote(cell_range)}?valueInputOption=USER_ENTERED")
    _sheets_request("PUT", url, token, {"values": [[value]]})


def find_rows_by_column(sheets_id: str, column_name: str, value: str) -> list[tuple[int, dict]]:
    """Return [(row_index, row_dict), ...] for rows where column_name == value."""
    rows = read_tracking_sheet(sheets_id)
    return [(i, r) for i, r in enumerate(rows) if r.get(column_name, "").strip() == value]


if __name__ == "__main__":
    # Quick sanity test: python3 sheets_helper.py <sheets_id>
    if len(sys.argv) < 2:
        print("Usage: python3 sheets_helper.py <google_sheets_id>")
        sys.exit(1)

    sid = sys.argv[1]
    rows = read_tracking_sheet(sid)
    print(f"Sheet has {len(rows)} data rows")
    if rows:
        print(f"First row: {rows[0]}")

"""
m365_upgrade_silent.py — take an existing MSAL token cache (base64) that was
minted with a subset of scopes but whose refresh token is consented for the
FULL scope set, and silently acquire a full-scope token. No browser needed.

Usage:
    python m365_upgrade_silent.py <path-to-file-containing-M365_TOKEN_B64=...>
The file can be a previous m365_login output; we extract the M365_TOKEN_B64 line.
"""
import base64
import os
import re
import sys

import msal
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
_session = requests.Session()
_session.verify = False

CLIENT_ID = os.getenv("M365_CLIENT_ID", "").strip()
TENANT_ID = os.getenv("M365_TENANT_ID", "common").strip()
FULL_SCOPES = ["Mail.Read", "Mail.ReadWrite", "Calendars.Read",
               "OnlineMeetings.Read", "OnlineMeetingTranscript.Read.All"]


def _read_b64(path: str) -> str:
    raw = open(path, "r", encoding="utf-8", errors="replace").read()
    m = re.search(r"M365_TOKEN_B64=([A-Za-z0-9+/=]+)", raw)
    if not m:
        print("ERROR: no M365_TOKEN_B64=... found in file", file=sys.stderr)
        sys.exit(1)
    return m.group(1)


def main():
    if len(sys.argv) < 2:
        print("usage: python m365_upgrade_silent.py <file-with-M365_TOKEN_B64>", file=sys.stderr)
        sys.exit(1)
    if not CLIENT_ID:
        print("ERROR: set M365_CLIENT_ID / M365_TENANT_ID first.", file=sys.stderr)
        sys.exit(1)

    b64 = _read_b64(sys.argv[1])
    cache = msal.SerializableTokenCache()
    cache.deserialize(base64.b64decode(b64).decode("utf-8"))

    app = msal.PublicClientApplication(
        CLIENT_ID,
        authority=f"https://login.microsoftonline.com/{TENANT_ID}",
        token_cache=cache,
        http_client=_session,
    )
    accounts = app.get_accounts()
    if not accounts:
        print("ERROR: no account in the seeded cache.", file=sys.stderr)
        sys.exit(1)

    print(f"Account: {accounts[0].get('username')}")
    print(f"Silently requesting full scopes: {' '.join(FULL_SCOPES)}")
    result = app.acquire_token_silent(FULL_SCOPES, account=accounts[0])
    if not result or "access_token" not in result:
        print(f"ERROR: silent full-scope acquire failed: "
              f"{(result or {}).get('error_description', 'no token / needs interaction')}",
              file=sys.stderr)
        sys.exit(2)

    granted = result.get("scope", "")
    print(f"\nGranted scopes on the new access token:\n  {granted}\n")
    new_b64 = base64.b64encode(cache.serialize().encode("utf-8")).decode("ascii")
    print("=" * 64)
    print("SUCCESS — full-scope token. Set these on the claude-bridge Railway service:\n")
    print(f"M365_SCOPES={' '.join(FULL_SCOPES)}\n")
    print(f"M365_TOKEN_B64={new_b64}")
    print("=" * 64)


if __name__ == "__main__":
    main()

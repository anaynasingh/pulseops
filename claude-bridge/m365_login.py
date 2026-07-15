"""
m365_login.py — one-time LOCAL login to mint the M365 token for the Railway bridge.

Run this on YOUR machine (it opens a browser-based device-code login). It prints
`M365_TOKEN_B64` and `M365_SCOPES` to paste into the claude-bridge Railway
service. The bridge then refreshes tokens silently forever — no browser needed
in the container.

Usage (PowerShell):
    pip install msal requests
    $env:M365_CLIENT_ID="<your azure app client id>"
    $env:M365_TENANT_ID="d2df1e4d-b444-4a6f-b465-92b187684c19"
    python m365_login.py

It tries the full scope set (incl. Teams transcripts, which needs tenant-admin
consent) and, if that's refused, automatically falls back to email+calendar+
meetings so you at least get those working.
"""
import base64
import os
import sys

import msal
import requests
import urllib3

# Match the rest of the PulseOps stack: tolerate local AV/proxy TLS interception.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
_session = requests.Session()
_session.verify = False

CLIENT_ID = os.getenv("M365_CLIENT_ID", "").strip()
TENANT_ID = os.getenv("M365_TENANT_ID", "common").strip()

FULL_SCOPES = ["Mail.Read", "Mail.ReadWrite", "Calendars.Read",
               "OnlineMeetings.Read", "OnlineMeetingTranscript.Read.All",
               "Files.Read.All", "Sites.Read.All"]
NO_TRANSCRIPT_SCOPES = ["Mail.Read", "Mail.ReadWrite", "Calendars.Read", "OnlineMeetings.Read"]


def _try_login(scopes):
    cache = msal.SerializableTokenCache()
    app = msal.PublicClientApplication(
        CLIENT_ID,
        authority=f"https://login.microsoftonline.com/{TENANT_ID}",
        token_cache=cache,
        http_client=_session,
    )
    flow = app.initiate_device_flow(scopes=scopes)
    if "user_code" not in flow:
        return None, f"could not start device flow: {flow.get('error_description', flow)}"
    print("\n" + "=" * 64)
    print(flow["message"])
    print("=" * 64 + "\n")
    result = app.acquire_token_by_device_flow(flow)  # blocks until you finish in the browser
    if "access_token" not in result:
        return None, result.get("error_description", result.get("error", "unknown error"))
    return cache, None


def main():
    if not CLIENT_ID:
        print("ERROR: set M365_CLIENT_ID (and M365_TENANT_ID) first.", file=sys.stderr)
        sys.exit(1)

    print(f"Client: {CLIENT_ID}\nTenant: {TENANT_ID}")
    print("Trying full login (incl. Teams transcript scope, needs admin consent)...")
    cache, err = _try_login(FULL_SCOPES)
    scopes_used = FULL_SCOPES
    if err:
        print(f"\n  full-scope login failed: {err}")
        print("  retrying WITHOUT the transcript scope (email + calendar + meetings)...")
        cache, err = _try_login(NO_TRANSCRIPT_SCOPES)
        scopes_used = NO_TRANSCRIPT_SCOPES
        if err:
            print(f"ERROR: login failed: {err}", file=sys.stderr)
            sys.exit(1)

    b64 = base64.b64encode(cache.serialize().encode("utf-8")).decode("ascii")
    print("\n" + "=" * 64)
    print("SUCCESS — set these on the claude-bridge Railway service:\n")
    print(f"M365_SCOPES={' '.join(scopes_used)}\n")
    print(f"M365_TOKEN_B64={b64}")
    print("=" * 64)
    if scopes_used is NO_TRANSCRIPT_SCOPES:
        print("\nNOTE: transcript scope was NOT granted, so get_meeting_transcript won't work")
        print("until an admin consents to OnlineMeetingTranscript.Read.All. Email + calendar do.")


if __name__ == "__main__":
    main()

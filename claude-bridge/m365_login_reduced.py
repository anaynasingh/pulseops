"""
m365_login_reduced.py — same as m365_login.py but requests ONLY the
email + calendar + meetings scopes (skips the admin-consent transcript scope).
"""
import base64
import os
import sys

import msal
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
_session = requests.Session()
_session.verify = False

CLIENT_ID = os.getenv("M365_CLIENT_ID", "").strip()
TENANT_ID = os.getenv("M365_TENANT_ID", "common").strip()

SCOPES = ["Mail.Read", "Mail.ReadWrite", "Calendars.Read", "OnlineMeetings.Read"]


def main():
    if not CLIENT_ID:
        print("ERROR: set M365_CLIENT_ID (and M365_TENANT_ID) first.", file=sys.stderr)
        sys.exit(1)

    print(f"Client: {CLIENT_ID}\nTenant: {TENANT_ID}")
    print(f"Requesting scopes: {' '.join(SCOPES)}")
    cache = msal.SerializableTokenCache()
    app = msal.PublicClientApplication(
        CLIENT_ID,
        authority=f"https://login.microsoftonline.com/{TENANT_ID}",
        token_cache=cache,
        http_client=_session,
    )
    flow = app.initiate_device_flow(scopes=SCOPES)
    if "user_code" not in flow:
        print(f"ERROR: could not start device flow: {flow.get('error_description', flow)}", file=sys.stderr)
        sys.exit(1)
    print("\n" + "=" * 64)
    print(flow["message"])
    print("=" * 64 + "\n", flush=True)
    result = app.acquire_token_by_device_flow(flow)
    if "access_token" not in result:
        print(f"ERROR: login failed: {result.get('error_description', result.get('error'))}", file=sys.stderr)
        sys.exit(1)

    b64 = base64.b64encode(cache.serialize().encode("utf-8")).decode("ascii")
    print("\n" + "=" * 64)
    print("SUCCESS — set these on the claude-bridge Railway service:\n")
    print(f"M365_SCOPES={' '.join(SCOPES)}\n")
    print(f"M365_TOKEN_B64={b64}")
    print("=" * 64)


if __name__ == "__main__":
    main()

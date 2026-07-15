"""Print ONLY the scp/roles claim of the access token in a base64 MSAL cache,
plus the refresh-token target. No secrets are printed."""
import base64, json, re, sys

def b64pad(s): return s + "=" * (-len(s) % 4)

raw = open(sys.argv[1], "r", encoding="utf-8", errors="replace").read()
b64 = re.search(r"M365_TOKEN_B64=([A-Za-z0-9+/=]+)", raw).group(1)
cache = json.loads(base64.b64decode(b64).decode("utf-8"))

# Access token JWT -> decode payload -> scp
at = next(iter(cache.get("AccessToken", {}).values()), None)
if at:
    payload = at["secret"].split(".")[1]
    claims = json.loads(base64.urlsafe_b64decode(b64pad(payload)))
    print("Access token scp claim:", claims.get("scp", "(none)"))
    print("Access token aud       :", claims.get("aud", "(none)"))
    print("Access token expires   :", claims.get("exp"))
else:
    print("No AccessToken in cache")

rt = next(iter(cache.get("RefreshToken", {}).values()), None)
if rt:
    print("Refresh token target   :", rt.get("target", "(none)"))

import time
import uuid
import secrets
import httpx
import msal
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from app.db.session import get_db
from app.models.models import User
from app.schemas.schemas import MicrosoftTokenRequest, TokenResponse, UserOut
from app.core.security import create_access_token, decode_token
from app.core.deps import get_current_user
from app.core.config import settings
from app.core.crypto import encrypt_str
from datetime import datetime, timezone

router = APIRouter(prefix="/auth", tags=["auth"])

_state_store: dict[str, float] = {}
_exchange_store: dict[str, tuple[str, float]] = {}

_SCOPES = ["User.Read"]


def _msal_app(cache: "msal.SerializableTokenCache | None" = None) -> msal.ConfidentialClientApplication:
    return msal.ConfidentialClientApplication(
        settings.AZURE_CLIENT_ID,
        authority=f"https://login.microsoftonline.com/{settings.AZURE_TENANT_ID}",
        client_credential=settings.AZURE_CLIENT_SECRET,
        token_cache=cache,
    )


@router.get("/microsoft/login")
async def microsoft_login() -> RedirectResponse:
    state = str(uuid.uuid4())
    _state_store[state] = time.time() + 300
    auth_url = _msal_app().get_authorization_request_url(
        scopes=_SCOPES,
        state=state,
        redirect_uri=settings.AZURE_REDIRECT_URI,
    )
    return RedirectResponse(url=auth_url)


@router.get("/microsoft/callback")
async def microsoft_callback(
    code: str = "",
    state: str = "",
    error: str = "",
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    error_redirect = f"{settings.FRONTEND_URL}/login?error="

    if error:
        return RedirectResponse(url=f"{error_redirect}{error}")

    expiry = _state_store.pop(state, None)
    if not expiry or time.time() > expiry:
        return RedirectResponse(url=f"{error_redirect}invalid_state")

    result = _msal_app().acquire_token_by_authorization_code(
        code=code,
        scopes=_SCOPES,
        redirect_uri=settings.AZURE_REDIRECT_URI,
    )

    if "error" in result:
        return RedirectResponse(url=f"{error_redirect}token_exchange_failed")

    ms_access_token = result.get("access_token", "")
    id_claims = result.get("id_token_claims", {})
    ms_oid = id_claims.get("oid", "")
    name = id_claims.get("name", "") or id_claims.get("preferred_username", "")

    async with httpx.AsyncClient() as client:
        graph_resp = await client.get(
            "https://graph.microsoft.com/v1.0/me",
            headers={"Authorization": f"Bearer {ms_access_token}"},
        )
    if graph_resp.status_code != 200:
        return RedirectResponse(url=f"{error_redirect}graph_fetch_failed")

    graph_data = graph_resp.json()
    email = (graph_data.get("mail") or graph_data.get("userPrincipalName") or "").lower()
    display_name = graph_data.get("displayName") or name

    if not email or not ms_oid:
        return RedirectResponse(url=f"{error_redirect}missing_user_claims")

    result_db = await db.execute(
        select(User).where(or_(User.ms_oid == ms_oid, User.email == email))
    )
    user = result_db.scalar_one_or_none()

    if user:
        user.ms_oid = ms_oid
        user.name = display_name
    else:
        user = User(email=email, name=display_name, ms_oid=ms_oid)
        db.add(user)

    await db.commit()
    await db.refresh(user)

    if not user.is_active:
        return RedirectResponse(url=f"{error_redirect}account_disabled")

    jwt = create_access_token({"sub": str(user.id)})
    exchange_code = str(uuid.uuid4())
    _exchange_store[exchange_code] = (jwt, time.time() + 60)

    return RedirectResponse(url=f"{settings.FRONTEND_URL}/callback?code={exchange_code}")


@router.post("/microsoft/token", response_model=TokenResponse)
async def microsoft_token(
    payload: MicrosoftTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    entry = _exchange_store.pop(payload.code, None)
    if not entry or time.time() > entry[1]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired code")

    jwt_str = entry[0]
    token_data = decode_token(jwt_str)
    if not token_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    result = await db.execute(select(User).where(User.id == token_data["sub"]))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    return TokenResponse(access_token=jwt_str, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(current_user)


@router.get("/api-key")
async def get_api_key(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not current_user.api_key:
        current_user.api_key = secrets.token_urlsafe(32)
        await db.commit()
        await db.refresh(current_user)
    return {"api_key": current_user.api_key}


@router.post("/mcp-complete", response_model=UserOut)
async def mcp_complete(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark Claude/MCP setup as completed for this user."""
    current_user.mcp_setup_done = True
    await db.commit()
    await db.refresh(current_user)
    return UserOut.model_validate(current_user)


@router.post("/mcp-reset", response_model=UserOut)
async def mcp_reset(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reset Claude/MCP setup so the guide shows again."""
    current_user.mcp_setup_done = False
    await db.commit()
    await db.refresh(current_user)
    return UserOut.model_validate(current_user)


# ── Microsoft "Connect" — per-user Graph access for the in-app assistant ───────
# Distinct from sign-in above: this attaches the CURRENT PulseOps user's OWN
# Microsoft mailbox/calendar/transcript access to their account, so the assistant
# reads THEIR data instead of a single shared token. Same Azure app as sign-in
# (7d7b5cc0), whose Graph scopes are already admin-consented org-wide.

@router.get("/microsoft/connect")
async def microsoft_connect(current_user: User = Depends(get_current_user)) -> dict:
    """Return the Microsoft authorization URL for the signed-in user to grant
    mail/calendar/transcript access. The SPA redirects the browser to it. `state`
    is a short signed token binding the callback back to this user."""
    state = create_access_token({"sub": str(current_user.id), "purpose": "m365_connect"})
    auth_url = _msal_app().get_authorization_request_url(
        scopes=settings.M365_GRAPH_SCOPES,
        state=state,
        redirect_uri=settings.AZURE_CONNECT_REDIRECT_URI,
    )
    return {"auth_url": auth_url}


@router.get("/microsoft/connect/callback")
async def microsoft_connect_callback(
    code: str = "",
    state: str = "",
    error: str = "",
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """OAuth redirect target. Exchanges the code, captures the user's MSAL token
    cache (incl. refresh token), and stores it encrypted on their user row."""
    done_redirect = f"{settings.FRONTEND_URL}/?m365="
    if error or not code or not state:
        return RedirectResponse(url=f"{done_redirect}error")

    claims = decode_token(state)
    if not claims or claims.get("purpose") != "m365_connect":
        return RedirectResponse(url=f"{done_redirect}invalid_state")

    result_db = await db.execute(select(User).where(User.id == claims["sub"]))
    user = result_db.scalar_one_or_none()
    if not user or not user.is_active:
        return RedirectResponse(url=f"{done_redirect}user_not_found")

    cache = msal.SerializableTokenCache()
    result = _msal_app(cache).acquire_token_by_authorization_code(
        code=code,
        scopes=settings.M365_GRAPH_SCOPES,
        redirect_uri=settings.AZURE_CONNECT_REDIRECT_URI,
    )
    if "access_token" not in result:
        return RedirectResponse(url=f"{done_redirect}exchange_failed")

    user.m365_token_cache = encrypt_str(cache.serialize())
    user.m365_connected_at = datetime.now(timezone.utc)
    await db.commit()
    return RedirectResponse(url=f"{done_redirect}connected")


@router.get("/microsoft/connect/status")
async def microsoft_connect_status(current_user: User = Depends(get_current_user)) -> dict:
    """Whether this user has connected their Microsoft account for the assistant."""
    return {
        "connected": bool(current_user.m365_token_cache),
        "connected_at": current_user.m365_connected_at.isoformat() if current_user.m365_connected_at else None,
    }


@router.post("/microsoft/disconnect", response_model=UserOut)
async def microsoft_disconnect(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserOut:
    """Forget this user's stored Microsoft token (they can reconnect anytime)."""
    current_user.m365_token_cache = None
    current_user.m365_connected_at = None
    await db.commit()
    await db.refresh(current_user)
    return UserOut.model_validate(current_user)

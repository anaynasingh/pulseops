"""Symmetric encryption for secrets stored at rest (e.g. per-user MSAL token caches).

Uses Fernet (AES-128-CBC + HMAC) with a key from settings.M365_TOKEN_ENC_KEY.
Generate a key once with:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
and set it as the M365_TOKEN_ENC_KEY env var (Railway secret). Rotating the key
invalidates existing stored caches — users would simply re-connect Microsoft.
"""
from cryptography.fernet import Fernet

from app.core.config import settings


def _fernet() -> Fernet:
    key = settings.M365_TOKEN_ENC_KEY
    if not key:
        raise RuntimeError(
            "M365_TOKEN_ENC_KEY is not set. Generate one with "
            '`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` '
            "and set it in the backend environment."
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_str(plaintext: str) -> str:
    """Encrypt a UTF-8 string; returns a urlsafe token string safe to store in TEXT."""
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt_str(ciphertext: str) -> str:
    """Reverse of encrypt_str."""
    return _fernet().decrypt(ciphertext.encode("ascii")).decode("utf-8")

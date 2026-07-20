"""
Encrypts/decrypts user-supplied LLM provider API keys before they touch
the database, using AES-256-GCM. Key material is derived from
SECRET_KEY, so no separate secret needs managing -- but that also means
SECRET_KEY must be kept safe and never change in place: rotating it
makes every previously-stored key undecryptable. If you ever need to
rotate SECRET_KEY, decrypt all UserApiKey rows with the old value first,
then re-encrypt and save with the new one.
"""
from __future__ import annotations

import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from core.config import settings

_NONCE_BYTES = 12


def _derive_key() -> bytes:
    # SHA-256 -> 32 bytes, exactly what AES-256 needs. This is a
    # deterministic KDF (no salt) because we need to re-derive the same
    # key on every decrypt without storing it anywhere.
    return hashlib.sha256(settings.secret_key.encode("utf-8")).digest()


def encrypt(plaintext: str) -> tuple[bytes, bytes]:
    """Returns (nonce, ciphertext). Both are safe to store; neither is secret on its own."""
    aesgcm = AESGCM(_derive_key())
    nonce = os.urandom(_NONCE_BYTES)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return nonce, ciphertext


def decrypt(nonce: bytes, ciphertext: bytes) -> str:
    aesgcm = AESGCM(_derive_key())
    return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")

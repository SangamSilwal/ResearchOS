"""
<<<<<<< ours
AES-256-GCM encryption for user-supplied API keys.

Design:
    - Each secret gets a fresh random 12-byte nonce (GCM requirement —
      nonce reuse under the same key is catastrophic, so we never let
      a nonce be anything other than freshly random per encryption).
    - Ciphertext and nonce are stored separately (see models.UserApiKey)
      so nothing here depends on a particular serialization format.
    - The master key never touches the database. It lives only in the
      environment (or better: a secrets manager in prod) and is loaded
      once at import time.
    - Decryption happens ONLY at the moment a run actually needs to call
      the provider — see services/model_resolver.py. Nothing decrypts
      keys "just in case" or logs them.

Env var:
    API_KEY_ENCRYPTION_KEY — base64-encoded 32 random bytes, e.g.
        python -c "import os,base64; print(base64.b64encode(os.urandom(32)).decode())"
"""
import base64
=======
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
>>>>>>> theirs
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

<<<<<<< ours
_NONCE_SIZE = 12  # bytes — standard for AES-GCM


class EncryptionKeyMissing(RuntimeError):
    pass


def _load_key() -> bytes:
    raw = os.environ.get("API_KEY_ENCRYPTION_KEY")
    if not raw:
        raise EncryptionKeyMissing(
            "API_KEY_ENCRYPTION_KEY is not set. Generate one with:\n"
            "  python -c \"import os,base64; print(base64.b64encode(os.urandom(32)).decode())\"\n"
            "and set it as an environment variable (never commit it)."
        )
    key = base64.b64decode(raw)
    if len(key) != 32:
        raise EncryptionKeyMissing(
            f"API_KEY_ENCRYPTION_KEY must decode to 32 bytes for AES-256, got {len(key)}."
        )
    return key


# Loaded once per process. Rotate by re-encrypting all rows and
# swapping the env var — see rotate_key() below for a helper.
_KEY = None


def _get_key() -> bytes:
    global _KEY
    if _KEY is None:
        _KEY = _load_key()
    return _KEY


def encrypt_secret(plaintext: str) -> tuple[bytes, bytes]:
    """Returns (ciphertext, nonce), both raw bytes for BYTEA columns."""
    aesgcm = AESGCM(_get_key())
    nonce = os.urandom(_NONCE_SIZE)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), associated_data=None)
    return ciphertext, nonce


def decrypt_secret(ciphertext: bytes, nonce: bytes) -> str:
    aesgcm = AESGCM(_get_key())
    plaintext = aesgcm.decrypt(nonce, bytes(ciphertext), associated_data=None)
    return plaintext.decode("utf-8")


def rotate_key(ciphertext: bytes, nonce: bytes, new_key_b64: str) -> tuple[bytes, bytes]:
    """
    Re-encrypts a single secret under a new master key. Callers rotating
    the whole table should decrypt every row with the old key (this
    module's normal decrypt_secret, under the old env var), then call
    this with the new key for each, then swap the env var once all rows
    are rewritten.
    """
    plaintext = decrypt_secret(ciphertext, nonce)
    new_key = base64.b64decode(new_key_b64)
    if len(new_key) != 32:
        raise EncryptionKeyMissing("New key must decode to 32 bytes for AES-256.")
    aesgcm = AESGCM(new_key)
    new_nonce = os.urandom(_NONCE_SIZE)
    new_ciphertext = aesgcm.encrypt(new_nonce, plaintext.encode("utf-8"), associated_data=None)
    return new_ciphertext, new_nonce
=======
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
>>>>>>> theirs

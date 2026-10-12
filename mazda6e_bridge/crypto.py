"""Credential encryption the Mazda 6e app backend expects.

Ported from fano0001/home-assistant-mazda-6e (credential_crypto.py, Apache-2.0).
Only the read-side helpers are kept: this bridge never signs vehicle commands.
"""

from __future__ import annotations

import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

# The backend's public key, shipped inside the official app. Email and password
# are RSA-encrypted with it before they leave the process.
SERVER_PUBLIC_KEY = (
    "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAkyhr43cBPTJ3jLiYsmbUwUp74cMJIOju5vqVzgtu"
    "K63Q99qV6iVT8wN5cXlyMtWI2mfOmhIao/fUN821im69MfOHsWXdqQEo5e9v654GPw+bju0pCphEPtD1I0Vc"
    "yS34QkAu04urSun2U1q3Dr2OICLVWSnLa+01ioKxkaB0D209zXcls2eFQpvRAWm7xxVsoqzSwqp+neu5quOp"
    "n+eO/bW0TxcSQ8VZcDEUvadRTLSR0eOWgRuHIBiD2RGqPIPzKCm5A14q1qhxUZ8U0pmYe0Sx7eMy4RVe2iW7"
    "fnjc6pxTUMBkercSL26mevYouuCKqyie+LVQAtGa29RMl/lyiwIDAQAB"
)

# PKCS#1 v1.5 with a 2048-bit key fits at most 245 bytes per block.
_CHUNK = 245


class CryptoError(ValueError):
    """Encryption failed. The message never contains the input."""


def encrypt_credential(value: str, public_key_b64: str = SERVER_PUBLIC_KEY) -> str:
    """Encrypt like the app's RSAUtils.encrypt: UTF-8, 245-byte chunks, PKCS#1 v1.5.

    The result keeps the line breaks of Android's Base64.DEFAULT, which is what
    the backend was captured accepting.
    """
    try:
        der = base64.b64decode("".join(public_key_b64.split()), validate=True)
        key = serialization.load_der_public_key(der)
    except ValueError:
        raise CryptoError("invalid public key") from None
    if not isinstance(key, rsa.RSAPublicKey) or key.key_size != 2048:
        raise CryptoError("a 2048-bit RSA public key is required")
    plain = value.encode("utf-8")
    encrypted = b"".join(
        key.encrypt(plain[i : i + _CHUNK], padding.PKCS1v15()) for i in range(0, len(plain), _CHUNK)
    )
    return base64.encodebytes(encrypted).decode("ascii")


def generate_public_key() -> str:
    """Return a fresh 2048-bit RSA public key, base64 DER, as the login call wants.

    The login endpoint registers this key for signing vehicle commands. The
    bridge sends none, so the private half is discarded on purpose.
    """
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    der = private.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return base64.encodebytes(der).decode("ascii")

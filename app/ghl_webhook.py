"""Verification of GoHighLevel Marketplace webhook signatures.

GHL signs the raw request body with its private key and sends the signature in
a header. We verify it against GHL's published public keys so a malicious actor
cannot spoof an event (e.g. a fake UNINSTALL that would wipe a real install, or
a fake INSTALL).

Two headers may be present (see the GHL Webhook Integration Guide):

    X-GHL-Signature   Ed25519    current, preferred (legacy RSA deprecated
                                 2026-07-01, so this is the one in use now)
    X-WH-Signature    RSA-SHA256 legacy fallback

Verification runs over the EXACT raw body bytes that were signed, so callers
must pass ``await request.body()`` unchanged — never a re-serialized dict.
"""
from __future__ import annotations

import base64
import logging

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.serialization import load_pem_public_key

log = logging.getLogger("ghl_bulkgate")

# Current Ed25519 public key — verifies X-GHL-Signature.
GHL_ED25519_PUBLIC_KEY_PEM = b"""-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEAi2HR1srL4o18O8BRa7gVJY7G7bupbN3H9AwJrHCDiOg=
-----END PUBLIC KEY-----"""

# Legacy RSA public key — verifies X-WH-Signature (deprecated 2026-07-01).
GHL_RSA_PUBLIC_KEY_PEM = b"""-----BEGIN PUBLIC KEY-----
MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEAokvo/r9tVgcfZ5DysOSC
Frm602qYV0MaAiNnX9O8KxMbiyRKWeL9JpCpVpt4XHIcBOK4u3cLSqJGOLaPuXw6
dO0t6Q/ZVdAV5Phz+ZtzPL16iCGeK9po6D6JHBpbi989mmzMryUnQJezlYJ3DVfB
csedpinheNnyYeFXolrJvcsjDtfAeRx5ByHQmTnSdFUzuAnC9/GepgLT9SM4nCpv
uxmZMxrJt5Rw+VUaQ9B8JSvbMPpez4peKaJPZHBbU3OdeCVx5klVXXZQGNHOs8gF
3kvoV5rTnXV0IknLBXlcKKAQLZcY/Q9rG6Ifi9c+5vqlvHPCUJFT5XUGG5RKgOKU
J062fRtN+rLYZUV+BjafxQauvC8wSWeYja63VSUruvmNj8xkx2zE/Juc+yjLjTXp
IocmaiFeAO6fUtNjDeFVkhf5LNb59vECyrHD2SQIrhgXpO4Q3dVNA5rw576PwTzN
h/AMfHKIjE4xQA1SZuYJmNnmVZLIZBlQAF9Ntd03rfadZ+yDiOXCCs9FkHibELhC
HULgCsnuDJHcrGNd5/Ddm5hxGQ0ASitgHeMZ0kcIOwKDOzOU53lDza6/Y09T7sYJ
PQe7z0cvj7aE4B+Ax1ZoZGPzpJlZtGXCsu9aTEGEnKzmsFqwcSsnw3JB31IGKAyk
T1hhTiaCeIY/OwwwNUY2yvcCAwEAAQ==
-----END PUBLIC KEY-----"""

_ed25519_key = load_pem_public_key(GHL_ED25519_PUBLIC_KEY_PEM)
_rsa_key = load_pem_public_key(GHL_RSA_PUBLIC_KEY_PEM)


def _decode_sig(signature: str) -> bytes | None:
    if not signature or signature == "N/A":
        return None
    try:
        return base64.b64decode(signature)
    except (ValueError, TypeError):
        return None


def verify_webhook(body: bytes, headers) -> bool:
    """Return True iff ``body`` carries a valid GHL signature.

    ``headers`` is any case-insensitive mapping (FastAPI ``request.headers``).
    Prefers the Ed25519 (X-GHL-Signature) header; falls back to legacy RSA.
    """
    ghl_sig = _decode_sig(headers.get("x-ghl-signature", ""))
    if ghl_sig is not None and isinstance(_ed25519_key, Ed25519PublicKey):
        try:
            _ed25519_key.verify(ghl_sig, body)
            return True
        except InvalidSignature:
            log.warning("webhook: X-GHL-Signature verification failed")
            return False

    legacy_sig = _decode_sig(headers.get("x-wh-signature", ""))
    if legacy_sig is not None and isinstance(_rsa_key, RSAPublicKey):
        try:
            _rsa_key.verify(legacy_sig, body, padding.PKCS1v15(), SHA256())
            return True
        except InvalidSignature:
            log.warning("webhook: X-WH-Signature verification failed")
            return False

    log.warning("webhook: no verifiable signature header present")
    return False

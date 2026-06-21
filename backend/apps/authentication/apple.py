import json

import jwt
import requests
from django.conf import settings
from django.core.cache import cache

APPLE_ISSUER = "https://appleid.apple.com"
APPLE_JWKS_URL = "https://appleid.apple.com/auth/keys"
APPLE_JWKS_CACHE_KEY = "authentication:apple:jwks"
APPLE_JWKS_CACHE_TIMEOUT = 60 * 60


def configured_apple_client_ids():
    """Return configured Apple audiences for native and web sign-in."""
    return tuple(
        client_id
        for client_id in (
            getattr(settings, "APPLE_SIGN_IN_IOS_CLIENT_ID", None),
            getattr(settings, "APPLE_SIGN_IN_WEB_CLIENT_ID", None),
        )
        if client_id
    )


def verify_apple_identity_token(identity_token):
    """Verify a Sign in with Apple identity token and return its claims."""
    client_ids = configured_apple_client_ids()
    if not client_ids:
        raise ValueError("Apple login is not configured.")

    try:
        header = jwt.get_unverified_header(identity_token)
    except jwt.PyJWTError as exc:
        raise ValueError("Invalid Apple login token.") from exc

    if header.get("alg") != "RS256":
        raise ValueError("Invalid Apple login token algorithm.")

    key = _apple_public_key(header.get("kid"))

    try:
        return jwt.decode(
            identity_token,
            key=key,
            algorithms=["RS256"],
            audience=client_ids,
            issuer=APPLE_ISSUER,
        )
    except jwt.PyJWTError as exc:
        raise ValueError("Invalid Apple login token.") from exc


def _apple_public_key(kid):
    if not kid:
        raise ValueError("Invalid Apple login token key.")

    for key_data in _apple_jwks().get("keys", []):
        if key_data.get("kid") == kid:
            return jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key_data))

    cache.delete(APPLE_JWKS_CACHE_KEY)
    for key_data in _apple_jwks().get("keys", []):
        if key_data.get("kid") == kid:
            return jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key_data))

    raise ValueError("Apple login token key was not found.")


def _apple_jwks():
    cached_keys = cache.get(APPLE_JWKS_CACHE_KEY)
    if cached_keys:
        return cached_keys

    try:
        response = requests.get(APPLE_JWKS_URL, timeout=5)
        response.raise_for_status()
        keys = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise ValueError("Could not load Apple login keys.") from exc

    cache.set(APPLE_JWKS_CACHE_KEY, keys, APPLE_JWKS_CACHE_TIMEOUT)
    return keys

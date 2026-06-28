import json
import time
from pathlib import Path

import jwt
import requests
from django.conf import settings
from django.core.cache import cache

APPLE_ISSUER = "https://appleid.apple.com"
APPLE_JWKS_URL = "https://appleid.apple.com/auth/keys"
APPLE_TOKEN_URL = "https://appleid.apple.com/auth/token"
APPLE_REVOKE_URL = "https://appleid.apple.com/auth/revoke"
APPLE_JWKS_CACHE_KEY = "authentication:apple:jwks"
APPLE_JWKS_CACHE_TIMEOUT = 60 * 60
APPLE_CLIENT_SECRET_TTL_SECONDS = 60 * 60 * 24 * 30


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


def exchange_apple_authorization_code(client_id, authorization_code, redirect_uri=None):
    """Exchange a one-time Apple authorization code for tokens."""
    if not authorization_code:
        return {}

    try:
        data = {
            "client_id": client_id,
            "client_secret": make_apple_client_secret(client_id),
            "code": authorization_code,
            "grant_type": "authorization_code",
        }
        if redirect_uri:
            data["redirect_uri"] = redirect_uri

        response = requests.post(APPLE_TOKEN_URL, data=data, timeout=10)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as exc:
        raise ValueError("Could not exchange Apple authorization code.") from exc


def revoke_apple_token(client_id, token, token_type_hint="refresh_token"):
    """Ask Apple to revoke a Sign in with Apple refresh or access token."""
    if not token:
        return

    try:
        data = {
            "client_id": client_id,
            "client_secret": make_apple_client_secret(client_id),
            "token": token,
            "token_type_hint": token_type_hint,
        }
        response = requests.post(APPLE_REVOKE_URL, data=data, timeout=10)
        response.raise_for_status()
    except (requests.RequestException, ValueError) as exc:
        raise ValueError("Could not revoke Apple token.") from exc


def make_apple_client_secret(client_id):
    """Build the ES256 client-secret JWT Apple requires for token APIs."""
    team_id = getattr(settings, "APPLE_SIGN_IN_TEAM_ID", None)
    key_id = getattr(settings, "APPLE_SIGN_IN_KEY_ID", None)
    private_key_path = getattr(settings, "APPLE_SIGN_IN_PRIVATE_KEY_PATH", None)
    if not all([team_id, key_id, private_key_path]):
        raise ValueError("Apple token API credentials are not configured.")

    issued_at = int(time.time())
    payload = {
        "iss": team_id,
        "iat": issued_at,
        "exp": issued_at + APPLE_CLIENT_SECRET_TTL_SECONDS,
        "aud": APPLE_ISSUER,
        "sub": client_id,
    }
    try:
        private_key = Path(private_key_path).read_text()
    except OSError as exc:
        raise ValueError("Apple token API private key could not be read.") from exc

    return jwt.encode(payload, private_key, algorithm="ES256", headers={"kid": key_id})


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

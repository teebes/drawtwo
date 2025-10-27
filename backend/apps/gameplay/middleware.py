"""
Custom middleware for WebSocket authentication using JWT tokens.
"""
import logging
from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken

logger = logging.getLogger(__name__)

User = get_user_model()


@database_sync_to_async
def get_user_from_token(token_string):
    """
    Validate JWT token and return the associated user.
    """
    try:
        # Validate and decode the token
        access_token = AccessToken(token_string)
        user_id = access_token['user_id']

        # Get the user from the database
        user = User.objects.get(id=user_id)
        return user
    except (TokenError, InvalidToken, User.DoesNotExist) as e:
        logger.warning(f"Invalid token or user not found: {e}")
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """
    Custom middleware that authenticates WebSocket connections using JWT tokens
    passed as query parameters.
    """

    async def __call__(self, scope, receive, send):
        # Get query string from scope
        query_string = scope.get('query_string', b'').decode()
        query_params = parse_qs(query_string)

        # Extract token from query parameters
        token = query_params.get('token', [None])[0]

        if token:
            # Authenticate user with JWT token
            scope['user'] = await get_user_from_token(token)
            logger.info(f"JWT auth: User {scope['user']} authenticated via token")
        else:
            # No token provided, keep the user from the session (if any)
            # This allows backwards compatibility with session-based auth
            if 'user' not in scope:
                scope['user'] = AnonymousUser()
            logger.debug(f"No JWT token in query params, user from session: {scope['user']}")

        return await super().__call__(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    """
    Helper function to wrap the JWT authentication middleware.
    Maintains compatibility with AuthMiddlewareStack pattern.
    """
    from channels.auth import AuthMiddlewareStack
    return JWTAuthMiddleware(AuthMiddlewareStack(inner))

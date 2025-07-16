from django.http import JsonResponse
from django.urls import resolve
from django.contrib.auth import get_user_model
from .models import SiteSettings

User = get_user_model()


class SiteAccessControlMiddleware:
    """
    Middleware to enforce site-wide access controls based on SiteSettings.

    Features:
    1. Whitelist mode - only approved users can access the site
    2. Signup restrictions - prevent new registrations when disabled
    """

    def __init__(self, get_response):
        self.get_response = get_response

        # URLs that should always be accessible (even in whitelist mode)
        self.always_allowed_urls = [
            'authentication:register',  # Allow registration page even if signup disabled (to show message)
            'authentication:passwordless_login',
            'authentication:email_confirm',
            'authentication:google_login',
            'admin:index',  # Allow Django admin
            'control:site_settings',  # Allow checking site settings
        ]

        # URL patterns that should always be accessible
        self.always_allowed_patterns = [
            '/api/auth/',
            '/admin/',
            '/api/control/',  # Control panel APIs
        ]

    def __call__(self, request):
        # Get site settings
        settings = SiteSettings.get_cached_settings()

        # Check if this is an API request
        is_api_request = request.path.startswith('/api/')

        # Skip middleware for certain URLs and static files
        if self._should_skip_middleware(request):
            return self.get_response(request)

        # Handle signup restrictions
        if settings.signup_disabled and self._is_registration_request(request):
            if is_api_request:
                return JsonResponse({
                    'error': 'User registration is currently disabled.'
                }, status=403)
            # For non-API requests, let the view handle it (can show a message)

        # Handle whitelist mode
        if settings.whitelist_mode_enabled:
            if not self._is_user_allowed_in_whitelist_mode(request):
                if is_api_request:
                    return JsonResponse({
                        'error': 'Site is in restricted access mode. Please contact an administrator.',
                        'whitelist_mode': True
                    }, status=403)
                # For non-API requests, could redirect to a maintenance page
                # For now, we'll just return the JSON response
                return JsonResponse({
                    'error': 'Site is in restricted access mode. Please contact an administrator.',
                    'whitelist_mode': True
                }, status=403)

        return self.get_response(request)

    def _should_skip_middleware(self, request):
        """Check if middleware should be skipped for this request."""
        # Skip for static files and media
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return True

        # Skip for certain URL patterns
        for pattern in self.always_allowed_patterns:
            if request.path.startswith(pattern):
                return True

        # Skip for admin and auth URLs
        try:
            resolver_match = resolve(request.path)
            if resolver_match and resolver_match.url_name in self.always_allowed_urls:
                return True
        except:
            pass

        return False

    def _is_registration_request(self, request):
        """Check if this is a user registration request."""
        try:
            resolver_match = resolve(request.path)
            if resolver_match and resolver_match.url_name == 'authentication:register':
                return request.method == 'POST'
        except:
            pass

        # Also check for dj-rest-auth registration endpoint
        if request.path.startswith('/api/auth/registration/') and request.method == 'POST':
            return True

        return False

    def _is_user_allowed_in_whitelist_mode(self, request):
        """Check if user is allowed to access the site in whitelist mode."""
        # Allow unauthenticated users to access auth endpoints
        if not request.user.is_authenticated:
            return True  # Let auth views handle authentication

        # Always allow staff users
        if request.user.is_staff:
            return True

        # Check if user is approved
        if hasattr(request.user, 'is_approved') and request.user.is_approved:
            return True

        return False
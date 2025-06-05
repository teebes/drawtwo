from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from . import views

app_name = 'authentication'

urlpatterns = [
    # JWT Token endpoints
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),

    # dj-rest-auth endpoints
    path('auth/', include('dj_rest_auth.urls')),
    path('auth/registration/', include('dj_rest_auth.registration.urls')),

    # Allauth account URLs (needed for email confirmation)
    path('accounts/', include('allauth.urls')),

    # Custom authentication views
    path('register/', views.register_view, name='register'),
    path('passwordless-login/', views.PasswordlessLoginView.as_view(), name='passwordless_login'),
    path('email-confirm/', views.EmailConfirmationView.as_view(), name='email_confirm'),
    path('profile/', views.UserProfileView.as_view(), name='user_profile'),
    path('test/', views.protected_test_view, name='protected_test'),

    # Social authentication
    path('google/', views.GoogleLogin.as_view(), name='google_login'),
]
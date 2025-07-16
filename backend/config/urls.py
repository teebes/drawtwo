"""
URL configuration for drawtwo project.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.core.urls")),
    path("api/auth/", include("apps.authentication.urls")),
    path("api/builder/", include("apps.builder.urls")),
    path("api/collection/", include("apps.collection.urls")),
    path("api/gameplay/", include("apps.gameplay.urls")),
    path("api/control/", include("apps.control.urls")),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

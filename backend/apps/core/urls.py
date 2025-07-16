from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("health/", views.health_check, name="health_check"),
    path("titles/", views.titles, name="titles"),
    path("titles/<slug:slug>/", views.title_by_slug, name="title-by-slug"),
    path("titles/<slug:slug>/cards/", views.title_cards, name="title-cards"),
    path("titles/<slug:slug>/heroes/", views.title_heroes, name="title-heroes"),
]

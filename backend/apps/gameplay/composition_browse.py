"""Public composition statistics, matchups, and recorded player/hero usage."""

from datetime import timedelta

from django.db.models import Count, F, FloatField, Max, OuterRef, Q, Subquery
from django.db.models.functions import Cast
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.authentication.models import User
from apps.builder.models import CardTemplate, HeroTemplate, Title
from apps.collection.compositions import CompositionCodeError, resolve_composition_code
from apps.collection.models import DeckComposition
from apps.gameplay.composition_records import (
    composition_record,
    composition_result_counts,
)
from apps.gameplay.models import Game, GameLoadout


def stats_filters(params):
    filters = {
        "game_type": params.get("game_type", "ranked"),
        "days": params.get("days", "all"),
        "ladder": params.get("ladder", "all"),
    }
    for key, choices in {
        "game_type": {"ranked", "friendly"},
        "days": {"all", "7", "30", "90"},
        "ladder": {"all", "rapid", "daily"},
    }.items():
        if filters[key] not in choices:
            raise ValidationError({"error": f"Invalid {key} filter."})
    if filters["game_type"] == "friendly":
        filters["ladder"] = "all"
    return filters


def eligible_loadouts(title, filters):
    loadouts = GameLoadout.objects.filter(
        composition__title=title,
        game__title=title,
        game__type=filters["game_type"],
        game__status=Game.GAME_STATUS_ENDED,
    )
    if filters["days"] != "all":
        loadouts = loadouts.filter(
            game__created_at__gte=timezone.now() - timedelta(days=int(filters["days"]))
        )
    if filters["ladder"] != "all":
        loadouts = loadouts.filter(game__ladder_type=filters["ladder"])
    return loadouts


def _title(request, title_slug):
    title = get_object_or_404(Title, slug=title_slug, is_latest=True)
    if not title.can_be_viewed_by(request.user):
        raise PermissionDenied("You do not have access to this title")
    return title


def _integer(params, key, default, maximum):
    try:
        value = int(params.get(key, default))
    except (ValueError, TypeError):
        raise ValidationError({"error": f"{key} must be a positive integer."})
    if not 1 <= value <= maximum:
        raise ValidationError({"error": f"{key} must be between 1 and {maximum}."})
    return value


def composition_summaries(title, ids):
    """An explicit public projection: never serialize a deck or its owner."""
    compositions = list(DeckComposition.objects.filter(title=title, id__in=ids))
    slugs = {card["slug"] for comp in compositions for card in comp.manifest}
    names = {}
    for card in (
        CardTemplate.objects.filter(title=title, slug__in=slugs)
        .order_by("slug", "-is_latest", "-version", "-id")
        .values("slug", "name")
    ):
        names.setdefault(card["slug"], card["name"])
    return {
        comp.id: {
            "code": comp.code,
            "digest": comp.digest,
            "total_cards": comp.total_cards,
            "cards": [
                {
                    "slug": card["slug"],
                    "count": card["count"],
                    "name": names.get(card["slug"], card["slug"]),
                }
                for card in comp.manifest
            ],
        }
        for comp in compositions
    }


def _page(request, title, loadouts, group):
    minimum = _integer(request.query_params, "min_games", 1, 1000000)
    page = _integer(request.query_params, "page", 1, 1000000)
    page_size = _integer(request.query_params, "page_size", 20, 50)
    sort = request.query_params.get("sort", "win_rate")
    ordering = {
        "win_rate": ("-rate", "-games", group),
        "win_rate_asc": ("rate", "-games", group),
        "games": ("-games", "-rate", group),
    }
    if sort not in ordering:
        raise ValidationError({"error": "Invalid sort order."})
    rows = (
        loadouts.order_by()
        .values(group)
        .annotate(**composition_result_counts())
        .filter(games__gte=minimum)
        .annotate(rate=Cast(F("wins"), FloatField()) / F("games"))
        .order_by(*ordering[sort])
    )
    count = rows.count()
    page_rows = list(rows[(page - 1) * page_size : page * page_size])
    compositions = composition_summaries(title, [row[group] for row in page_rows])
    return {
        "count": count,
        "page": page,
        "page_size": page_size,
        "results": [
            {"composition": compositions[row[group]], "record": composition_record(row)}
            for row in page_rows
        ],
    }


@api_view(["GET"])
@permission_classes([AllowAny])
def composition_list(request, title_slug):
    title = _title(request, title_slug)
    filters = stats_filters(request.query_params)
    loadouts = eligible_loadouts(title, filters)
    summary = loadouts.aggregate(
        matches=Count("game_id", distinct=True),
        appearances=Count("id"),
        compositions=Count("composition_id", distinct=True),
    )
    search = request.query_params.get("q", "").strip()
    if len(search) > 200:
        raise ValidationError({"error": "Search must be 200 characters or fewer."})
    if search:
        # Search names as well as slugs, matching complete manifest slugs so
        # similarly named cards do not produce false positives.
        slugs = (
            CardTemplate.objects.filter(title=title)
            .filter(Q(name__icontains=search) | Q(slug__icontains=search))
            .values_list("slug", flat=True)
            .distinct()
        )
        matches = Q(composition__code=search)
        for slug in slugs:
            matches |= Q(composition__manifest__contains=[{"slug": slug}])
        loadouts = loadouts.filter(matches)
    return Response(
        {
            **_page(request, title, loadouts, "composition_id"),
            "filters": filters,
            "summary": summary,
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def composition_players(request, title_slug, code):
    title = _title(request, title_slug)
    filters = stats_filters(request.query_params)
    try:
        resolved = resolve_composition_code(title, code, create=False)
    except CompositionCodeError as exc:
        raise ValidationError({"error": str(exc)})

    page = _integer(request.query_params, "page", 1, 1000000)
    page_size = _integer(request.query_params, "page_size", 20, 50)
    usage = (
        eligible_loadouts(title, filters)
        .filter(composition=resolved.composition, player__isnull=False)
        .order_by()
        .values("player_id", "hero_slug")
        .annotate(games=Count("id"), hero_name=Max("hero_name"))
        .order_by("-games", "player_id", "hero_slug")
    )
    count = usage.count()
    rows = list(usage[(page - 1) * page_size : page * page_size])
    players = User.objects.in_bulk({row["player_id"] for row in rows})
    hero_names = {}
    for hero in HeroTemplate.objects.filter(
        title=title, slug__in={row["hero_slug"] for row in rows}
    ).order_by("slug", "-is_latest", "-version", "-id"):
        hero_names.setdefault(hero.slug, hero.name)

    return Response(
        {
            "count": count,
            "page": page,
            "page_size": page_size,
            "results": [
                {
                    "player": {
                        "id": row["player_id"],
                        "display_name": players[row["player_id"]].display_name,
                    },
                    "hero": {
                        "slug": row["hero_slug"],
                        "name": hero_names.get(row["hero_slug"], row["hero_name"]),
                    },
                    "uses": row["games"],
                }
                for row in rows
            ],
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def composition_matchups(request, title_slug, code):
    title = _title(request, title_slug)
    filters = stats_filters(request.query_params)
    try:
        resolved = resolve_composition_code(title, code, create=False)
    except CompositionCodeError as exc:
        raise ValidationError({"error": str(exc)})
    loadouts = eligible_loadouts(title, filters).filter(
        composition=resolved.composition
    )
    opponent = (
        GameLoadout.objects.filter(
            game_id=OuterRef("game_id"),
            composition__title=title,
        )
        .exclude(side=OuterRef("side"))
        .values("composition_id")[:1]
    )
    loadouts = loadouts.annotate(opponent_id=Subquery(opponent))
    missing = loadouts.filter(opponent_id__isnull=True).count()
    loadouts = loadouts.filter(opponent_id__isnull=False)
    return Response(
        {
            **_page(request, title, loadouts, "opponent_id"),
            "filters": filters,
            "unattributed_appearances": missing,
        }
    )

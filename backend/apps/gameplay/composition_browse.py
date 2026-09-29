"""Public composition statistics, matchups, and recorded player/hero usage."""

from datetime import timedelta

from django.db.models import Count, F, FloatField, Max, OuterRef, Q, Subquery
from django.db.models.functions import Cast, Coalesce, NullIf
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


def _integer(params, key, default, maximum, minimum=1):
    try:
        value = int(params.get(key, default))
    except (ValueError, TypeError):
        raise ValidationError({"error": f"{key} must be an integer."})
    if not minimum <= value <= maximum:
        raise ValidationError(
            {"error": f"{key} must be between {minimum} and {maximum}."}
        )
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
            "name": comp.name,
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


def _page(request, title, loadouts, group, *, compositions=None):
    default_minimum = 0 if compositions is not None else 1
    minimum = _integer(
        request.query_params,
        "min_games",
        default_minimum,
        1000000,
        minimum=default_minimum,
    )
    page = _integer(request.query_params, "page", 1, 1000000)
    page_size = _integer(request.query_params, "page_size", 20, 50)
    sort = request.query_params.get("sort", "win_rate")
    ordering = {
        "win_rate": (F("rate").desc(nulls_last=True), "-games", group),
        "win_rate_asc": (F("rate").asc(nulls_last=True), "-games", group),
        "games": ("-games", F("rate").desc(nulls_last=True), group),
    }
    if sort not in ordering:
        raise ValidationError({"error": "Invalid sort order."})
    if compositions is None:
        rows = loadouts.order_by().values(group).annotate(**composition_result_counts())
    else:
        # Start with saved compositions so favorites without eligible matches
        # remain visible. Use the same result attribution as the other scopes.
        records = (
            loadouts.filter(composition_id=OuterRef("pk"))
            .order_by()
            .values("composition_id")
            .annotate(**composition_result_counts())
        )
        rows = compositions.annotate(
            **{
                field: Coalesce(Subquery(records.values(field)[:1]), 0)
                for field in ("games", "wins", "losses")
            }
        ).values(group, "games", "wins", "losses")
    rows = (
        rows.filter(games__gte=minimum)
        .annotate(rate=Cast(F("wins"), FloatField()) / NullIf(F("games"), 0))
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
    scope = request.query_params.get("scope", "all")
    if scope not in {"all", "mine", "favorites"}:
        raise ValidationError({"error": "Invalid composition scope."})
    if scope in {"mine", "favorites"} and not request.user.is_authenticated:
        raise PermissionDenied("Sign in to see your compositions.")
    loadouts = eligible_loadouts(title, filters)
    if scope == "mine":
        # Attribute results to the player captured when the game began, even
        # if the source deck has since changed cards or ownership.
        loadouts = loadouts.filter(player=request.user)
    compositions = DeckComposition.objects.filter(title=title)
    if scope == "favorites":
        compositions = compositions.filter(favorites__user=request.user)
        loadouts = loadouts.filter(composition__in=compositions)
    totals = loadouts.aggregate(
        matches=Count("game_id", distinct=True),
        compositions=Count("composition_id", distinct=True),
        **composition_result_counts(),
    )
    summary = {
        "matches": totals["matches"],
        "appearances": totals["games"],
        "compositions": (
            compositions.count() if scope == "favorites" else totals["compositions"]
        ),
        "record": composition_record(totals),
    }
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
        matches = Q(code=search) | Q(name__icontains=search)
        for slug in slugs:
            matches |= Q(manifest__contains=[{"slug": slug}])
        compositions = compositions.filter(matches)
        loadouts = loadouts.filter(composition__in=compositions)
    return Response(
        {
            **_page(
                request,
                title,
                loadouts,
                "id" if scope == "favorites" else "composition_id",
                compositions=compositions if scope == "favorites" else None,
            ),
            "scope": scope,
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

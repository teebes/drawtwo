from django.shortcuts import render, get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.exceptions import PermissionDenied
from django.contrib.auth import get_user_model
from django.db import transaction

# Import your models and serializers when you create them
# from .models import Project, Canvas, Layer
# from .serializers import ProjectSerializer, CanvasSerializer, LayerSerializer

from .models import Title, CardTemplate, CardTrait
from .serializers import TitleSerializer, CardTemplateSerializer

User = get_user_model()


def get_title_or_403(slug, user):
    """
    Get a title by slug and check if the user has permission to view it.

    Raises:
        Http404: If the title doesn't exist
        PermissionDenied: If the user doesn't have permission to view the title

    Returns:
        Title: The title object if user has permission
    """
    title = get_object_or_404(Title, slug=slug, is_latest=True)
    if not title.can_be_viewed_by(user):
        raise PermissionDenied("You do not have permission to view this title.")
    return title


@api_view(['GET'])
@permission_classes([AllowAny])
def title_by_slug(request, slug):
    """Get the latest version of a title by its slug."""
    title = get_title_or_403(slug, request.user)

    serializer = TitleSerializer(title)
    data = serializer.data

    # Add edit permission info if user is authenticated
    if request.user and request.user.is_authenticated:
        data['can_edit'] = title.can_be_edited_by(request.user)
    else:
        data['can_edit'] = False

    return Response(data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_card(request, title_slug):
    """Create a new card for a title."""
    # Get the title (latest version) or return 404
    title = get_object_or_404(Title, slug=title_slug, is_latest=True)

    # Check if user has permission to edit this title
    if not title.can_be_edited_by(request.user):
        return Response(
            {'error': 'You do not have permission to edit this title'},
            status=status.HTTP_403_FORBIDDEN
        )

    yaml_data = request.data.get('yaml_definition')
    if not yaml_data:
        return Response(
            {'error': 'yaml_definition is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Get and validate slug
    slug = request.data.get('slug', '').strip()
    if not slug:
        return Response(
            {'error': 'slug is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Validate slug format
    import re
    if not re.match(r'^[a-z0-9\-_]+$', slug):
        return Response(
            {'error': 'Slug can only contain lowercase letters, numbers, hyphens, and underscores'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if len(slug) < 2:
        return Response(
            {'error': 'Slug must be at least 2 characters long'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if len(slug) > 50:
        return Response(
            {'error': 'Slug must be no more than 50 characters long'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Check if slug already exists in this title
    if CardTemplate.objects.filter(title=title, slug=slug).exists():
        return Response(
            {'error': f'A card with slug "{slug}" already exists in this title'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        with transaction.atomic():
            # Create new card using YAML data and specified slug
            serializer = CardTemplateSerializer()
            new_card = serializer.create_from_yaml(title, yaml_data, slug=slug)

            response_serializer = CardTemplateSerializer(new_card)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def card_detail(request, title_slug, card_slug):
    """Get or update a specific card by title and card slug."""
    # Get the title (latest version) or return 404
    title = get_object_or_404(Title, slug=title_slug, is_latest=True)

    # Check if user has permission to edit this title
    if not title.can_be_edited_by(request.user):
        return Response(
            {'error': 'You do not have permission to edit this title'},
            status=status.HTTP_403_FORBIDDEN
        )

    # Get the card (latest version) or return 404
    card = get_object_or_404(
        CardTemplate,
        title=title,
        slug=card_slug,
        is_latest=True
    )

    if request.method == 'GET':
        serializer = CardTemplateSerializer(card)
        return Response(serializer.data)

    elif request.method == 'PUT':
        yaml_data = request.data.get('yaml_definition')
        bump_version = request.data.get('bump_version', False)

        if not yaml_data:
            return Response(
                {'error': 'yaml_definition is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                if bump_version:
                    # Create new version using the version bump logic
                    updated_card = bump_card_version(card, yaml_data)
                else:
                    # Update the existing card in place
                    serializer = CardTemplateSerializer()
                    updated_card = serializer.update_from_yaml(card, yaml_data)

                serializer = CardTemplateSerializer(updated_card)
                return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    elif request.method == 'DELETE':
        try:
            with transaction.atomic():
                # Soft delete by setting is_latest=False
                card.is_latest = False
                card.save(update_fields=['is_latest'])

                return Response(
                    {'message': f'Card "{card.name}" has been deleted'},
                    status=status.HTTP_200_OK
                )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


def bump_card_version(card: CardTemplate, yaml_data: str) -> CardTemplate:
    """Create a new version of a card with updated data from YAML."""
    # Lock the current latest row
    prev = (CardTemplate.objects
            .select_for_update()
            .get(title=card.title, slug=card.slug, is_latest=True))

    # Mark it no longer latest
    prev.is_latest = False
    prev.save(update_fields=["is_latest"])

    # Create new version with copied data
    new_card = CardTemplate.objects.create(
        title=prev.title,
        slug=prev.slug,
        name=prev.name,
        description=prev.description,
        version=prev.version + 1,
        is_latest=True,
        card_type=prev.card_type,
        cost=prev.cost,
        attack=prev.attack,
        health=prev.health,
        spec=prev.spec,
        faction=prev.faction
    )

    # Copy tags
    new_card.tags.set(prev.tags.all())

    # Copy traits
    for card_trait in prev.cardtrait_set.all():
        CardTrait.objects.create(
            card=new_card,
            trait=card_trait.trait,
            data=card_trait.data
        )

    # Update with YAML data
    serializer = CardTemplateSerializer()
    updated_card = serializer.update_from_yaml(new_card, yaml_data)

    return updated_card

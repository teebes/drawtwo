from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.builder.models import Title, CardTemplate
from apps.builder.serializers import TitleSerializer
from .schemas import Card, Trait

def health_check(request):
    """Simple health check endpoint"""
    return JsonResponse({"status": "healthy"})

@api_view(['GET'])
def titles(request):
    titles = Title.objects.order_by('-published_at')
    serializer = TitleSerializer(titles, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def title_by_slug(request, slug):
    """Get the latest version of a title by its slug."""
    title = get_object_or_404(Title, slug=slug, is_latest=True)
    serializer = TitleSerializer(title)
    return Response(serializer.data)

@api_view(['GET'])
def title_cards(request, slug):
    """
    Get all cards for a title, ordered by cost then name.
    Returns data in the Card schema format with efficient trait fetching.
    """
    # Get the title (latest version) or return 404
    title = get_object_or_404(Title, slug=slug, is_latest=True)

    # Build an efficient query with prefetching
    cards = (CardTemplate.objects
             .filter(title=title, is_latest=True)
             .select_related('title', 'faction')  # Avoid N+1 on title and faction
             .prefetch_related(
                 'traits',  # Prefetch traits
                 'cardtraitargument_set__trait'  # Prefetch trait arguments
             )
             .order_by('cost', 'card_type', 'attack', 'health', 'name'))  # Order by cost, then type (minions before spells), then stats, then name

    # Transform to Card schema format
    card_data = []
    for card in cards:
        # Build traits list with arguments
        traits_list = []

        # Get trait arguments efficiently
        trait_arguments = {
            ta.trait_id: {'argument': ta.argument, 'extra_data': ta.extra_data}
            for ta in card.cardtraitargument_set.all()
        }

        for trait in card.traits.all().order_by('name'):
            argument_info = trait_arguments.get(trait.id, {})

            trait_obj = Trait(
                slug=trait.slug,
                name=trait.name,
                argument=argument_info.get('argument'),
                extra_data=argument_info.get('extra_data', {})
            )
            traits_list.append(trait_obj)

        # Create Card schema object
        card_obj = Card(
            slug=card.slug,
            name=card.name,
            description=card.description,
            card_type=card.card_type,
            cost=card.cost,
            attack=card.attack or 0,  # Handle null values for spells
            health=card.health or 0,  # Handle null values for spells
            traits=traits_list,
            faction=card.faction.slug if card.faction else None
        )

        card_data.append(card_obj.model_dump())

    return Response(card_data)
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.builder.models import Title, CardTemplate
from apps.builder.serializers import TitleSerializer
from .serializers import serialize_cards_with_traits

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

    # Build the queryset with filtering and ordering
    cards_queryset = (CardTemplate.objects
                     .filter(title=title, is_latest=True)
                     .order_by('cost', 'card_type', 'attack', 'health', 'name'))

    # Use the helper function to serialize with efficient prefetching
    card_data = serialize_cards_with_traits(cards_queryset)

    return Response(card_data)
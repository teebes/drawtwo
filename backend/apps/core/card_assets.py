"""
Utility functions for generating card asset URLs.

This module handles URL generation for card artwork, supporting both:
- Cloudflare R2 (production and testing)
- Local file serving (development fallback)
"""
from django.conf import settings


def get_hero_art_url(title_slug: str, hero_slug: str, extension: str = "webp") -> str:
    """
    Generate the URL for a hero's artwork.
    """
    if settings.USE_R2_FOR_CARDS and settings.CARD_ASSETS_BASE_URL:
        base_url = settings.CARD_ASSETS_BASE_URL.rstrip('/')
        return f"{base_url}/titles/{title_slug}/heroes/{hero_slug}.{extension}"
    else:
        return f"{settings.MEDIA_URL}titles/{title_slug}/heroes/{hero_slug}.{extension}"

def get_card_art_url(title_slug: str, card_slug: str, extension: str = "webp") -> str:
    """
    Generate the URL for a card's artwork.

    Args:
        title_slug: The slug of the title (e.g., 'archetype')
        card_slug: The slug of the card (e.g., 'zap')
        extension: The file extension (default: 'webp')

    Returns:
        Full URL to the card artwork

    Examples:
        >>> get_card_art_url('archetype', 'zap')
        'https://assets.drawtwo.com/titles/archetype/cards/zap.webp'
    """
    if settings.USE_R2_FOR_CARDS and settings.CARD_ASSETS_BASE_URL:
        # Use Cloudflare R2
        base_url = settings.CARD_ASSETS_BASE_URL.rstrip('/')
        return f"{base_url}/titles/{title_slug}/cards/{card_slug}.{extension}"
    else:
        # Fallback to local media files
        return f"{settings.MEDIA_URL}titles/{title_slug}/cards/{card_slug}.{extension}"


def get_card_back_url(title_slug: str, extension: str = "webp") -> str:
    """
    Generate the URL for a title's card back artwork.

    Args:
        title_slug: The slug of the title (e.g., 'archetype')
        extension: The file extension (default: 'webp')

    Returns:
        Full URL to the card back artwork
    """
    if settings.USE_R2_FOR_CARDS and settings.CARD_ASSETS_BASE_URL:
        base_url = settings.CARD_ASSETS_BASE_URL.rstrip('/')
        return f"{base_url}/titles/{title_slug}/card_back.{extension}"
    else:
        return f"{settings.MEDIA_URL}titles/{title_slug}/card_back.{extension}"

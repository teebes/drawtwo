from typing import List, Dict, Any
#from .schemas import Card, Trait, Deck, Hero
from .schemas import Deck, Hero
from apps.builder.schemas import Card, Trait
from pydantic import TypeAdapter
from .card_assets import get_card_art_url


def to_card_schema(card) -> Card:
    """
    Convert a single CardTemplate instance to Card schema.
    Assumes traits are already prefetched for performance.
    """
    # Build traits list with data
    traits_list = []

    # Use all() which uses prefetch cache if available
    # Note: Avoid using .order_by() here as it would invalidate prefetch cache
    # The prefetch query should handle ordering if needed
    traits = card.cardtrait_set.all()
    # Sort in python to avoid DB hit if prefetched
    traits = sorted(traits, key=lambda t: t.trait_slug)

    for card_trait in traits:
        trait_data = {
            'type': card_trait.trait_slug,
            **card_trait.data
        }

        # Use TypeAdapter to properly validate and create the discriminated union
        trait_adapter = TypeAdapter(Trait)
        trait_obj = trait_adapter.validate_python(trait_data)
        traits_list.append(trait_obj)

    # Create Card schema object
    return Card(
        id=card.id,
        slug=card.slug,
        name=card.name,
        description=card.description,
        card_type=card.card_type,
        cost=card.cost,
        attack=card.attack or 0,  # Handle null values for spells
        health=card.health or 0,  # Handle null values for spells
        traits=traits_list,
        faction=card.faction.slug if card.faction else None,
        art_url=get_card_art_url(card.title.slug, card.slug)
    )


def serialize_cards_with_traits(queryset) -> List[Card]:
    """
    Efficiently serialize a CardTemplate queryset to Card schema format.

    Args:
        queryset: CardTemplate queryset (can be filtered, ordered, etc.)

    Returns:
        List of Card schema objects
    """
    # Apply efficient prefetching to the queryset
    cards = queryset.select_related('title', 'faction').prefetch_related(
        'cardtrait_set'  # Prefetch card traits
    )

    # Transform to Card schema format
    return [to_card_schema(card) for card in cards]

def serialize_decks(queryset) -> List[Dict[str, Any]]:
    queryset = queryset.select_related(
        'hero', 'title', 'ai_player', 'user'
    ).prefetch_related('deckcard_set')
    return [
        Deck(
            id=deck.id,
            name=deck.name,
            description=deck.description,
            hero=Hero(
                id=deck.hero.id,
                slug=deck.hero.slug,
                name=deck.hero.name,
                health=deck.hero.health,
                hero_power=deck.hero.hero_power,
                spec=deck.hero.spec,
                faction=deck.hero.faction.slug if deck.hero.faction else None,
            ),
            card_count=deck.deck_size,
            created_at=deck.created_at,
            updated_at=deck.updated_at,
        ).model_dump()
        for deck in queryset
    ]
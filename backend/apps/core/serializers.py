from typing import List, Dict, Any
from .schemas import Card, Trait, Deck, Hero


def serialize_cards_with_traits(queryset) -> List[Dict[str, Any]]:
    """
    Efficiently serialize a CardTemplate queryset to Card schema format.

    Args:
        queryset: CardTemplate queryset (can be filtered, ordered, etc.)

    Returns:
        List of dictionaries in Card schema format
    """
    # Apply efficient prefetching to the queryset
    cards = queryset.select_related('title', 'faction').prefetch_related(
        'cardtrait_set__trait'  # Prefetch card traits with trait data
    )

    # Transform to Card schema format
    card_data = []
    for card in cards:
        # Build traits list with data
        traits_list = []

        for card_trait in card.cardtrait_set.all().order_by('trait__name'):
            trait_obj = Trait(
                slug=card_trait.trait.slug,
                name=card_trait.trait.name,
                data=card_trait.data
            )
            traits_list.append(trait_obj)

        # Create Card schema object
        card_obj = Card(
            id=card.id,
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

    return card_data

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
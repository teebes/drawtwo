from apps.builder.schemas import TitleConfig


class DeckValidationError(ValueError):
    """Raised when a deck is not legal for play."""


def get_title_config(title) -> TitleConfig:
    return TitleConfig.model_validate(title.config or {})


def _copy_word(count: int) -> str:
    return "copy" if count == 1 else "copies"


def _card_has_trait(card, trait_slug: str) -> bool:
    prefetched = getattr(card, "_prefetched_objects_cache", {})
    if "cardtrait_set" in prefetched:
        return any(
            trait.trait_slug == trait_slug for trait in prefetched["cardtrait_set"]
        )
    return card.cardtrait_set.filter(trait_slug=trait_slug).exists()


def _card_is_available_to_hero(card, hero) -> bool:
    if hero is None:
        return False

    prefetched = getattr(card, "_prefetched_objects_cache", {})
    if "allowed_heroes" in prefetched:
        allowed_hero_ids = [
            allowed_hero.id for allowed_hero in prefetched["allowed_heroes"]
        ]
        return not allowed_hero_ids or hero.id in allowed_hero_ids

    return card.is_available_to_hero(hero)


def validate_card_for_deck(deck, card) -> str | None:
    if card.title_id != deck.title_id:
        return (
            f'"{card.name}" belongs to a different title and cannot be used '
            "in this deck"
        )

    if deck.user_id is not None and not card.is_collectible:
        return f'"{card.name}" is not collectible and cannot be added to a deck'

    if not _card_is_available_to_hero(card, deck.hero):
        return (
            f'"{card.name}" is only available to specific heroes and cannot be used '
            f"by {deck.hero.name}"
        )

    return None


def validate_deck_card_count(
    deck, card, new_count: int, current_count: int = 0
) -> str | None:
    card_error = validate_card_for_deck(deck, card)
    if card_error:
        return card_error

    config = get_title_config(deck.title)

    if new_count < 1:
        return "count must be at least 1"

    if new_count > config.deck_card_max_count:
        return (
            f"Cannot have more than {config.deck_card_max_count} "
            f"{_copy_word(config.deck_card_max_count)} of a card"
        )

    if _card_has_trait(card, "unique") and new_count > 1:
        return f'"{card.name}" has the Unique trait and can only have 1 copy in a deck'

    new_deck_size = deck.deck_size - current_count + new_count
    if new_deck_size > config.deck_size_limit:
        return f"Deck size would exceed the limit of {config.deck_size_limit} cards"

    return None


def validate_deck_for_play(deck, deck_label: str = "Deck") -> str | None:
    if getattr(deck, "archived_at", None):
        return f"{deck_label} has been archived"

    config = get_title_config(deck.title)
    deck_size = deck.deck_size
    enforce_deck_rules = not deck.is_ai_deck

    if deck.hero.title_id != deck.title_id:
        return f"{deck_label} has a hero from a different title"

    if enforce_deck_rules and deck_size < config.min_cards_in_deck:
        return (
            f"{deck_label} must have at least {config.min_cards_in_deck} cards "
            f"({deck_size} currently)"
        )

    if enforce_deck_rules and deck_size > config.deck_size_limit:
        return (
            f"{deck_label} cannot have more than {config.deck_size_limit} cards "
            f"({deck_size} currently)"
        )

    deck_cards = (
        deck.deckcard_set.select_related("card", "card__title")
        .prefetch_related("card__allowed_heroes", "card__cardtrait_set")
        .order_by("card__name")
    )

    for deck_card in deck_cards:
        card = deck_card.card

        if deck_card.count < 1:
            return f"{deck_label} contains an invalid count for {card.name}"

        card_error = validate_card_for_deck(deck, card)
        if card_error:
            return f"{deck_label} contains an invalid card: {card_error}"

        if enforce_deck_rules and deck_card.count > config.deck_card_max_count:
            return (
                f"{deck_label} cannot have more than "
                f"{config.deck_card_max_count} "
                f"{_copy_word(config.deck_card_max_count)} of {card.name}"
            )

        if (
            enforce_deck_rules
            and _card_has_trait(card, "unique")
            and deck_card.count > 1
        ):
            return (
                f'{deck_label} contains too many copies of "{card.name}"; '
                "Unique cards can only have 1 copy"
            )

    return None


def validate_deck_for_play_or_raise(deck, deck_label: str = "Deck") -> None:
    error = validate_deck_for_play(deck, deck_label)
    if error:
        raise DeckValidationError(error)

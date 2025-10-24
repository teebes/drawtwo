"""
Default trait definitions for card game mechanics.

These definitions are used across all titles unless overridden.
Title authors can customize trait names/descriptions via TraitOverride model.
"""

# Trait type constants
TRAIT_ARMOR = "armor"
TRAIT_BATTLECRY = "battlecry"
TRAIT_CHARGE = "charge"
TRAIT_CLEAVE = "cleave"
TRAIT_DEATHRATTLE = "deathrattle"
TRAIT_INSPIRE = "inspire"
TRAIT_LIFESTEAL = "lifesteal"
TRAIT_RANGED = "ranged"
TRAIT_STEALTH = "stealth"
TRAIT_TAUNT = "taunt"
TRAIT_UNIQUE = "unique"

# Default trait definitions
TRAIT_DEFINITIONS = {
    TRAIT_ARMOR: {
        'name': 'Armor',
        'description': 'Reduces incoming damage by a specified amount.',
    },
    TRAIT_BATTLECRY: {
        'name': 'Battlecry',
        'description': 'Triggers an effect when the card is played.',
    },
    TRAIT_CHARGE: {
        'name': 'Charge',
        'description': 'Can attack immediately when played.',
    },
    TRAIT_CLEAVE: {
        'name': 'Cleave',
        'description': 'Attacks hit multiple targets.',
    },
    TRAIT_DEATHRATTLE: {
        'name': 'Deathrattle',
        'description': 'Triggers an effect when the creature dies.',
    },
    TRAIT_INSPIRE: {
        'name': 'Inspire',
        'description': 'Triggers an effect when you use your hero power.',
    },
    TRAIT_LIFESTEAL: {
        'name': 'Lifesteal',
        'description': 'Restores health equal to damage dealt.',
    },
    TRAIT_RANGED: {
        'name': 'Ranged',
        'description': 'Can attack without taking retaliation damage.',
    },
    TRAIT_STEALTH: {
        'name': 'Stealth',
        'description': 'Cannot be targeted by attacks until this creature attacks.',
    },
    TRAIT_TAUNT: {
        'name': 'Taunt',
        'description': 'Must be attacked before other targets.',
    },
    TRAIT_UNIQUE: {
        'name': 'Unique',
        'description': 'Only one copy can exist in your deck.',
    },
}

# List of all valid trait slugs
TRAIT_SLUGS = list(TRAIT_DEFINITIONS.keys())


def get_trait_info(title, slug: str) -> dict:
    """
    Get trait information (name, description) for a given title and slug.

    First checks for title-specific overrides, then falls back to defaults.

    Args:
        title: Title instance
        slug: Trait slug (e.g., 'charge', 'taunt')

    Returns:
        Dict with 'slug', 'name', 'description'

    Raises:
        ValueError: If slug is not a valid trait
    """
    if slug not in TRAIT_DEFINITIONS:
        raise ValueError(f"Unknown trait slug: {slug}")

    # Import here to avoid circular dependency
    from apps.builder.models import TraitOverride

    # Check for title-specific override
    try:
        override = TraitOverride.objects.get(title=title, slug=slug)
        return {
            'slug': slug,
            'name': override.name,
            'description': override.description,
        }
    except TraitOverride.DoesNotExist:
        # Use default
        default = TRAIT_DEFINITIONS[slug]
        return {
            'slug': slug,
            'name': default['name'],
            'description': default['description'],
        }


def validate_trait_slug(slug: str) -> bool:
    """Check if a slug is a valid trait."""
    return slug in TRAIT_DEFINITIONS

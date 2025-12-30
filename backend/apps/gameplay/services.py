import logging
import random
import traceback
import uuid

from django.db import transaction, DatabaseError
from pydantic import TypeAdapter, ValidationError

logger = logging.getLogger(__name__)

from apps.builder.models import CardTemplate
from apps.builder.schemas import (
    Action,
    BuffAction,
    ClearAction,
    DeckScript,
    DrawAction,
    DamageAction,
    HealAction,
    HeroPower,
    RemoveAction,
    SummonAction,
    TitleConfig,
    TempManaBoostAction,
)
from apps.core.serializers import serialize_cards_with_traits, to_card_schema
from apps.gameplay.engine.dispatcher import resolve
from apps.gameplay.models import Game
from apps.gameplay.schemas.game import (
    CardInPlay,
    GameState,
    HeroInPlay,
)
from apps.gameplay.schemas.commands import (
    AttackCommand,
    Command,
    ConcedeCommand,
    PlayCardCommand,
    EndTurnCommand,
    UseHeroCommand,
)
from apps.gameplay.schemas.effects import (
    AttackEffect,
    BuffEffect,
    ClearEffect,
    ConcedeEffect,
    DamageEffect,
    DrawEffect,
    Effect,
    EndTurnEffect,
    HealEffect,
    PlayEffect,
    RemoveEffect,
    StartGameEffect,
    SummonEffect,
    TempManaBoostEffect,
    UseHeroEffect,
)
from apps.gameplay.schemas.engine import Success, Result, Prevented, Rejected, Fault
from apps.gameplay.schemas.events import (
    ActionableEvent,
    CreatureDeathEvent,
    EndTurnEvent,
    GameOverEvent,
    NewPhaseEvent,
)


# Moved to avoid circular import - imported where needed


from apps.builder.schemas import Card
from apps.core.card_assets import get_hero_art_url
from apps.gameplay.notifications import send_game_updates_to_clients
from apps.gameplay.schemas.game import GameState


class GameService:

    def get_card_in_play(card: Card, card_id: int) -> CardInPlay:
        return CardInPlay(
            card_type=card.card_type,
            card_id=str(card_id),
            template_slug=card.slug,
            name=card.name,
            description=card.description,
            attack=card.attack,
            health=card.health,
            cost=card.cost,
            traits=card.traits,
            art_url=card.art_url,
        )

    @staticmethod
    @transaction.atomic
    def create_game(
        deck_a,
        deck_b,
        randomize_starting_player: bool = False
    ) -> Game:

        existing_game = Game.objects.filter(
            side_a=deck_a,
            side_b=deck_b,
        ).exclude(
            status=Game.GAME_STATUS_ENDED,
        ).first()
        if existing_game:
            return existing_game

        # Load world config
        config = TitleConfig.model_validate(deck_a.title.config)

        # Optionally randomize which deck goes first (50/50 chance)
        # By default, deck_a always goes first for deterministic behavior
        # This allows for future enhancements like alternating starts between same players
        if randomize_starting_player and random.random() < 0.5:
            # Swap the decks so deck_b starts
            deck_a, deck_b = deck_b, deck_a

        deck_a_card_copies = {
            card_copy.card.id: card_copy.count
            for card_copy in deck_a.deckcard_set.all()
        }
        deck_b_card_copies = {
            card_copy.card.id: card_copy.count
            for card_copy in deck_b.deckcard_set.all()
        }

        cards_a = serialize_cards_with_traits(deck_a.cards.all())
        cards_b = serialize_cards_with_traits(deck_b.cards.all())

        card_id = 0
        cards_in_play = {}
        decks = {'side_a': [], 'side_b': []}

        for card in cards_a:
            for _ in range(deck_a_card_copies[card.id]):
                card_id += 1
                cards_in_play[str(card_id)] = GameService.get_card_in_play(card, card_id)
                decks['side_a'].append(str(card_id))

        for card in cards_b:
            for _ in range(deck_b_card_copies[card.id]):
                card_id += 1
                cards_in_play[str(card_id)] = GameService.get_card_in_play(card, card_id)
                decks['side_b'].append(str(card_id))

        # Get the side b compensation card if it exists
        comp_card = None
        if config.side_b_compensation:
            card = CardTemplate.objects.get(
                slug=config.side_b_compensation,
                is_latest=True)
            comp_card = to_card_schema(card)
            card_id += 1
            comp_card_in_play = GameService.get_card_in_play(comp_card, card_id)
            cards_in_play[str(card_id)] = comp_card_in_play

        # shuffle both decks
        random.shuffle(decks['side_a'])
        random.shuffle(decks['side_b'])

        # Collect all summonable card slugs from cards and heroes
        summonable_slugs = set()

        # Scan all cards in play for summon actions
        for card in cards_in_play.values():
            for trait in card.traits:
                for action in trait.actions:
                    if isinstance(action, SummonAction):
                        summonable_slugs.add(action.target)

        # Scan hero powers for summon actions
        for hero_template in [deck_a.hero, deck_b.hero]:
            # Convert hero_power dict to HeroPower model
            hero_power = HeroPower.model_validate(hero_template.hero_power)
            for action in hero_power.actions:
                if isinstance(action, SummonAction):
                    summonable_slugs.add(action.target)

        # Load and store the summonable card templates
        summonable_cards = {}
        for slug in summonable_slugs:
            try:
                card_template = CardTemplate.objects.get(slug=slug, is_latest=True)
                card_schema = to_card_schema(card_template)
                # Create a CardInPlay template (card_id will be assigned when summoned)
                summonable_cards[slug] = CardInPlay(
                    card_type=card_schema.card_type,
                    card_id="",  # Placeholder, will be assigned during summon
                    template_slug=slug,
                    name=card_schema.name,
                    description=card_schema.description,
                    attack=card_schema.attack,
                    health=card_schema.health,
                    cost=card_schema.cost,
                    traits=card_schema.traits,
                    art_url=card_schema.art_url,
                )
            except CardTemplate.DoesNotExist:
                logger.warning(f"Summonable card with slug '{slug}' not found")

        heroes = {
            'side_a': HeroInPlay(
                hero_id=str(deck_a.hero.id),
                template_slug=deck_a.hero.slug,
                health=deck_a.hero.health,
                health_max=deck_a.hero.health,
                name=deck_a.hero.name,
                description=deck_a.hero.description,
                hero_power=deck_a.hero.hero_power,
                exhausted=False,
                art_url=get_hero_art_url(deck_a.title.slug, deck_a.hero.slug),
                player_name=deck_a.owner_name,
            ),
            'side_b': HeroInPlay(
                hero_id=str(deck_b.hero.id),
                template_slug=deck_b.hero.slug,
                health=deck_b.hero.health,
                health_max=deck_b.hero.health,
                name=deck_b.hero.name,
                description=deck_b.hero.description,
                hero_power=deck_b.hero.hero_power,
                exhausted=False,
                art_url=get_hero_art_url(deck_b.title.slug, deck_b.hero.slug),
                player_name=deck_b.owner_name,

            ),
        }

        ai_sides = []
        if deck_a.is_ai_deck:
            ai_sides.append('side_a')
        if deck_b.is_ai_deck:
            ai_sides.append('side_b')

        hands = {'side_a': [], 'side_b': []}
        if comp_card:
            hands['side_b'].append(comp_card_in_play.card_id)

        game_state = GameState(
            turn=0,
            active='side_a',
            phase='start',
            cards=cards_in_play,
            heroes=heroes,
            hands=hands,
            decks=decks,
            ai_sides=ai_sides,
            config=config,
            summonable_cards=summonable_cards,
        )

        game = Game.objects.create(
            status=Game.GAME_STATUS_INIT,
            side_a=deck_a,
            side_b=deck_b,
            state=game_state.model_dump(),
        )

        game.enqueue([StartGameEffect(side='side_a')])

        return game

    @staticmethod
    @transaction.atomic
    def step(game_id: int):

        try:
            game = (Game.objects
                        .select_for_update(nowait=True)
                        .get(id=game_id))
        except DatabaseError:
            return

        logger.debug("==== STEP FUNCTION with queue: ====")
        for queue_item in game.queue or []:
            logger.debug(queue_item)
        logger.debug("===================================")

        if game.status == Game.GAME_STATUS_ENDED: return
        game.status = Game.GAME_STATUS_IN_PROGRESS
        game_state = GameState.model_validate(game.state)
        previous_phase = game_state.phase

        # Check for turn timeout - automatically concede if time expired
        if (game_state.phase == 'main'
            and game_state.time_per_turn > 0
            and game.turn_expires
            and game.status != Game.GAME_STATUS_ENDED):
            from django.utils import timezone
            if timezone.now() >= game.turn_expires:
                # Time expired - automatically concede for the active player
                from apps.gameplay.schemas.effects import ConcedeEffect
                logger.info(f"Turn expired for {game_state.active} in game {game_id}, auto-conceding")
                game.enqueue([ConcedeEffect(side=game_state.active)], trigger=False)
                # Continue processing to handle the concede effect

        # Process multiple effects in a batch to reduce DB round-trips
        effects_processed = 0
        processed_cap = 10
        all_events = []
        all_errors = []

        while len(game.queue) > 0 and effects_processed < processed_cap:

            # Pop one effect
            effect = game.queue.pop(0)
            try:
                effect = TypeAdapter(Effect).validate_python(effect)
            except ValidationError:
                logger.warning(f"Invalid effect: {effect}")
                continue

            # Wrap the entire effect processing in a try-except to catch any unhandled exceptions
            try:
                # Effect engine resolution
                result = resolve(effect, game_state)
                effects_processed += 1

                # Handle different result types
                if isinstance(result, Success):
                    # Update state and process normally
                    game_state = result.new_state

                    # Terminal Check
                    for event in result.events:
                        if isinstance(event, GameOverEvent):
                            game.status = Game.GAME_STATUS_ENDED
                            game.winner = getattr(game, event.winner)
                            game.save(update_fields=["status", "winner"])
                            game_state.winner = event.winner
                            game_state.queue = []
                            # Clear the queue immediately to prevent processing any remaining effects
                            game.queue = []
                            game.save(update_fields=["queue"])

                            # Calculate and save ELO changes for PvP matches
                            GameService._update_elo_ratings(game)
                            # Break out of the effect processing loop - game is over
                            break

                    # If game ended, stop processing remaining effects
                    if game.status == Game.GAME_STATUS_ENDED:
                        break

                    # Enqueue child effects (depth-first)
                    if result.child_effects:
                        game.enqueue(result.child_effects, trigger=False, prepend=True)

                    all_events.extend(result.events)

                    # ==== Event Triggers =====
                    from apps.gameplay import traits

                    for event in result.events:
                        trait_result = traits.apply(game_state, event)
                        if trait_result.child_effects:
                            game.enqueue(trait_result.child_effects, trigger=False, prepend=True)

                        if isinstance(event, NewPhaseEvent):
                            if event.phase == 'main' and game_state.time_per_turn > 0:
                                from django.utils import timezone
                                from datetime import timedelta
                                turn_expires_dt = timezone.now() + timedelta(seconds=game_state.time_per_turn)
                                game.turn_expires = turn_expires_dt
                                # Also set in GameState so it's sent to frontend
                                game_state.turn_expires = turn_expires_dt.isoformat()

                        if isinstance(event, EndTurnEvent):
                            game.turn_expires = None
                            game_state.turn_expires = None


                elif isinstance(result, (Prevented, Rejected)):
                    # Domain-level prevention or rejection
                    # State doesn't change, but we send user feedback and emit any events
                    logger.info(f"Effect {result.type}: {result.reason}")
                    all_events.extend(result.events)

                    # Add user-visible error message
                    all_errors.append({
                        'type': result.type,
                        'reason': result.reason,
                        'details': result.details,
                    })
                    # Continue processing (these are not critical failures)

                elif isinstance(result, Fault):
                    # System/engine error - this is a bug
                    logger.error(f"⚠️  FAULT: {result.reason} (error_id: {result.error_id})")
                    all_errors.append({
                        'error_id': result.error_id,
                        'reason': result.reason,
                        'details': result.details,
                        'effect': effect.model_dump(mode="json"),
                    })

                    # If unrecoverable, stop processing to avoid cascading failures
                    if not result.retryable:
                        logger.error(f"Non-retryable fault encountered, stopping effect processing")
                        break
                    # Otherwise continue processing (retryable faults)

            except Exception as e:
                # Catch any unhandled exceptions and convert them to Fault responses
                error_id = str(uuid.uuid4())
                logger.error(f"⚠️  UNHANDLED EXCEPTION: {str(e)} (error_id: {error_id})")
                logger.error(traceback.format_exc())

                # Create a Fault response
                all_errors.append({
                    'type': 'outcome_fault',
                    'error_id': error_id,
                    'reason': f'System error: {type(e).__name__}',
                    'details': {
                        'exception_type': type(e).__name__,
                        'exception_message': str(e),
                        'traceback': traceback.format_exc(),
                    },
                    'effect': effect.model_dump(mode="json"),
                })

                # Stop processing to avoid cascading failures
                logger.error(f"Stopping effect processing due to unhandled exception")
                break

        # Convert events to updates and persist them
        all_updates = GameService._events_to_updates(all_events)

        # Persist updates to database
        for update in all_updates:
            from apps.gameplay.models import GameUpdate
            GameUpdate.objects.create(
                game=game,
                update=update.model_dump(mode="json"),
            )

        # Single DB save for all processed events
        game.state = game_state.model_dump()
        game.save()

        # Send filtered updates to clients
        send_game_updates_to_clients(
            game_id=game.id,
            state=game_state,
            updates=all_updates,
            errors=all_errors
        )

        # See if we need to choose an AI move
        if (len(game.queue) == 0
            and game.state['phase'] == 'main'
            and game.state['active'] in game.state['ai_sides']):
            deck = getattr(game, game.state['active'])
            script=DeckScript.model_validate(deck.script or {})
            from apps.gameplay.ai import AIMoveChooser
            ai_event = AIMoveChooser.choose_move(game_state, script)
            if ai_event:
                game.enqueue([ai_event], trigger=False)
            else:
                game.enqueue([EndTurnEffect(side=game.state['active'])], trigger=False)

        # Continue processing if there are more effects in queue
        if len(game.queue) > 0:
            from apps.gameplay.tasks import step
            step.apply_async(args=[game_id], countdown=0.1)

    @staticmethod
    @transaction.atomic
    def process_command(game_id: int, command: dict, side):
        try:
            game = Game.objects.get(id=game_id)
        except Game.DoesNotExist:
            raise ValueError(f"Game with id {game_id} does not exist")

        # Reject commands if the game has already ended
        if game.status == Game.GAME_STATUS_ENDED:
            raise ValueError("The game has already ended.")

        game_state = GameState.model_validate(game.state)

        # Check for turn timeout before processing command
        if (game_state.phase == 'main'
            and game_state.time_per_turn > 0
            and game.turn_expires
            and side == game_state.active):
            from django.utils import timezone
            if timezone.now() >= game.turn_expires:
                # Time expired - automatically concede
                from apps.gameplay.schemas.effects import ConcedeEffect
                logger.info(f"Turn expired for {side} in game {game_id} when processing command, auto-conceding")
                game.enqueue([ConcedeEffect(side=side)], trigger=False)
                return  # Don't process the command, the concede will be handled

        effects = GameService.compile_cmd(game_state, command, side)
        game.enqueue(effects)

    @staticmethod
    def compile_cmd(game_state: GameState, command: dict, side) -> list[Effect]:
        "Translates a Command into a list of Effect objects"

        effects = []

        command = TypeAdapter(Command).validate_python(command)

        # Allow concede at any time, regardless of whose turn it is
        if isinstance(command, ConcedeCommand):
            effects.append(ConcedeEffect(side=side))
            return effects

        if side != game_state.active:
            raise ValueError(f"It is not your turn.")

        # Because we're transitioning to a system where the cards on the
        # board are creatures and not just cards, we make the transition
        # easier for the frontend by translating the target when possible.
        target_type = getattr(command, 'target_type', None)
        if target_type == "card":
            target_type = "creature"

        if isinstance(command, PlayCardCommand):
            effects.append(PlayEffect(
                side=game_state.active,
                source_id=command.card_id,
                position=command.position,
                target_type=target_type,
                target_id=command.target_id,
            ))
        elif isinstance(command, EndTurnCommand):
            effects.append(EndTurnEffect(
                side=game_state.active,
            ))
        elif isinstance(command, AttackCommand):
            # Validate that the creature belongs to the active player
            creature = game_state.creatures.get(command.card_id)
            if not creature:
                raise ValueError(f"Creature {command.card_id} does not exist")

            # Check if creature is on the active player's board
            if command.card_id not in game_state.board[game_state.active]:
                raise ValueError(f"You do not control creature {command.card_id}")

            # Validate that the target belongs to the opponent
            opposing_side = game_state.opposite_side
            if target_type == "creature":
                if command.target_id not in game_state.board[opposing_side]:
                    raise ValueError(f"Target creature {command.target_id} is not on opponent's board")
            elif target_type == "hero":
                # Hero must belong to opposing side
                opposing_hero = game_state.heroes.get(opposing_side)
                if not opposing_hero or opposing_hero.hero_id != command.target_id:
                    raise ValueError(f"Target hero {command.target_id} is not the opponent's hero")

            effects.append(AttackEffect(
                side=game_state.active,
                card_id=command.card_id,
                target_type=target_type,
                target_id=command.target_id,
            ))
        elif isinstance(command, UseHeroCommand):
            from apps.builder.schemas import HealAction

            # Validate that the hero belongs to the active player
            active_hero = game_state.heroes.get(game_state.active)
            if not active_hero or active_hero.hero_id != command.hero_id:
                raise ValueError(f"You do not control hero {command.hero_id}")

            # Determine if this hero power targets friendlies
            targets_friendly = any(
                ((isinstance(action, HealAction) and action.target == 'friendly') or
                (isinstance(action, DamageAction) and action.target == 'self'))
                for action in active_hero.hero_power.actions
            )

            # Validate that the target belongs to the correct side (if there is a target)
            if target_type:
                if targets_friendly:
                    # For healing/friendly powers, target must be on own side
                    if target_type == "creature":
                        if command.target_id not in game_state.board[game_state.active]:
                            raise ValueError(f"Target creature {command.target_id} is not on your board")
                    elif target_type == "hero":
                        if not active_hero or active_hero.hero_id != command.target_id:
                            raise ValueError(f"Target hero {command.target_id} is not your hero")
                else:
                    # For damage/enemy powers, target must be on opponent's side
                    opposing_side = game_state.opposite_side
                    if target_type == "creature":
                        if command.target_id not in game_state.board[opposing_side]:
                            raise ValueError(f"Target creature {command.target_id} is not on opponent's board")
                    elif target_type == "hero":
                        # Hero must belong to opposing side
                        opposing_hero = game_state.heroes.get(opposing_side)
                        if not opposing_hero or opposing_hero.hero_id != command.target_id:
                            raise ValueError(f"Target hero {command.target_id} is not the opponent's hero")

            effects.append(UseHeroEffect(
                side=game_state.active,
                source_id=command.hero_id,
                target_type=target_type,
                target_id=command.target_id,
            ))
        else:
            raise ValueError(f"Invalid command: {command}")

        logger.debug('effects: %s' % effects)

        return effects

    @staticmethod
    def compile_action(
        state: GameState,
        event: ActionableEvent,
        action: Action
    ) -> list[Effect]:
        """
        Compile an action into one or more effects.

        Handles scope parameter for damage and heal actions:
        - 'single': targets one entity
        - 'all': targets all valid entities on the target side
        - 'cleave': targets the selected entity and adjacent entities
        """

        # If a creature death event is triggering an action, we can safely assume
        # it's a deathrattle, in which case the source of the subsequent damage is
        # actually the creature that died.
        if isinstance(event, CreatureDeathEvent):
            source_id = event.target_id
            source_type = "creature"
            is_deathrattle = True
        else:
            source_id = event.source_id
            source_type = event.source_type
            is_deathrattle = False

        if isinstance(action, DrawAction):
            return [DrawEffect(
                side=event.side,
                amount=action.amount,
            )]

        if isinstance(action, DamageAction):
            opposing_side = "side_b" if event.side == "side_a" else "side_a"

            # Determine base target
            if action.target == "hero":
                base_target_type = "hero"
                base_target_id = state.heroes[opposing_side].hero_id
            elif action.target == "creature":
                base_target_type = "creature"
                base_target_id = event.target_id or (state.board[opposing_side][0] if state.board[opposing_side] else None)
            elif action.target == "enemy":
                # 'enemy' can be hero or creature, use event target
                base_target_type = event.target_type or "hero"
                base_target_id = event.target_id or state.heroes[opposing_side].hero_id
            elif action.target == "self":
                if source_type in ("hero", "creature") and source_id:
                    base_target_type = source_type
                    base_target_id = source_id
                else:
                    base_target_type = event.target_type
                    base_target_id = event.target_id
            else:
                base_target_type = event.target_type
                base_target_id = event.target_id

            # Get all targets based on scope
            targets = []

            if action.scope == 'single':
                if base_target_id:
                    targets = [(base_target_type, base_target_id)]

            elif action.scope == 'all':
                # Hit all enemies (all creatures + hero on opposing side)
                for creature_id in state.board[opposing_side]:
                    targets.append(("creature", creature_id))
                targets.append(("hero", state.heroes[opposing_side].hero_id))

            elif action.scope == 'cleave':
                # Hit target and adjacent creatures
                if base_target_type == "creature" and base_target_id in state.board[opposing_side]:
                    target_index = state.board[opposing_side].index(base_target_id)
                    # Add the main target
                    targets.append((base_target_type, base_target_id))
                    # Add left neighbor
                    if target_index > 0:
                        targets.append(("creature", state.board[opposing_side][target_index - 1]))
                    # Add right neighbor
                    if target_index < len(state.board[opposing_side]) - 1:
                        targets.append(("creature", state.board[opposing_side][target_index + 1]))
                elif base_target_id:
                    # If not a creature, just hit the single target
                    targets = [(base_target_type, base_target_id)]

            # Create damage effects for each target
            effects = []
            for target_type, target_id in targets:
                effects.append(DamageEffect(
                    side=event.side,
                    damage_type=action.damage_type,
                    source_type=source_type,
                    source_id=source_id,
                    target_type=target_type,
                    target_id=target_id,
                    damage=action.amount,
                    retaliate=not is_deathrattle,
                ))
            return effects

        if isinstance(action, HealAction):
            same_side = event.side

            # Determine base target for heal
            if action.target == "hero":
                base_target_type = "hero"
                base_target_id = state.heroes[same_side].hero_id
            elif action.target == "creature":
                base_target_type = "creature"
                base_target_id = event.target_id or (state.board[same_side][0] if state.board[same_side] else None)
            elif action.target == "friendly":
                # 'friendly' can be hero or creature, use event target
                base_target_type = event.target_type or "hero"
                base_target_id = event.target_id or state.heroes[same_side].hero_id
            else:
                base_target_type = event.target_type
                base_target_id = event.target_id

            # Get all targets based on scope
            targets = []

            if action.scope == 'single':
                if base_target_id:
                    targets = [(base_target_type, base_target_id)]

            elif action.scope == 'all':
                # Heal all friendlies (all creatures + hero on same side)
                for creature_id in state.board[same_side]:
                    targets.append(("creature", creature_id))
                targets.append(("hero", state.heroes[same_side].hero_id))

            elif action.scope == 'cleave':
                # Heal target and adjacent creatures
                if base_target_type == "creature" and base_target_id in state.board[same_side]:
                    target_index = state.board[same_side].index(base_target_id)
                    # Add the main target
                    targets.append((base_target_type, base_target_id))
                    # Add left neighbor
                    if target_index > 0:
                        targets.append(("creature", state.board[same_side][target_index - 1]))
                    # Add right neighbor
                    if target_index < len(state.board[same_side]) - 1:
                        targets.append(("creature", state.board[same_side][target_index + 1]))
                elif base_target_id:
                    # If not a creature, just heal the single target
                    targets = [(base_target_type, base_target_id)]

            # Create heal effects for each target
            effects = []
            for target_type, target_id in targets:
                effects.append(HealEffect(
                    side=event.side,
                    source_type=source_type,
                    source_id=source_id,
                    target_type=target_type,
                    target_id=target_id,
                    amount=action.amount,
                ))
            return effects

        if isinstance(action, RemoveAction):
            opposing_side = "side_b" if event.side == "side_a" else "side_a"

            # Determine base target
            if action.target == "creature":
                base_target_type = "creature"
                base_target_id = event.target_id or (state.board[opposing_side][0] if state.board[opposing_side] else None)
            elif action.target == "enemy":
                # 'enemy' can be creature, use event target (remove doesn't affect heroes)
                base_target_type = event.target_type or "creature"
                base_target_id = event.target_id
            else:
                base_target_type = event.target_type
                base_target_id = event.target_id

            # Get all targets based on scope
            targets = []

            if action.scope == 'single':
                if base_target_id and base_target_type == "creature":
                    targets = [(base_target_type, base_target_id)]

            elif action.scope == 'all':
                # Remove all enemy creatures
                for creature_id in state.board[opposing_side]:
                    targets.append(("creature", creature_id))

            elif action.scope == 'cleave':
                # Remove target and adjacent creatures
                if base_target_type == "creature" and base_target_id in state.board[opposing_side]:
                    target_index = state.board[opposing_side].index(base_target_id)
                    # Add the main target
                    targets.append((base_target_type, base_target_id))
                    # Add left neighbor
                    if target_index > 0:
                        targets.append(("creature", state.board[opposing_side][target_index - 1]))
                    # Add right neighbor
                    if target_index < len(state.board[opposing_side]) - 1:
                        targets.append(("creature", state.board[opposing_side][target_index + 1]))
                elif base_target_id:
                    # If not a creature, just remove the single target
                    targets = [(base_target_type, base_target_id)]

            # Create remove effects for each target
            effects = []
            for target_type, target_id in targets:
                effects.append(RemoveEffect(
                    side=event.side,
                    source_type=source_type,
                    source_id=source_id,
                    target_type=target_type,
                    target_id=target_id,
                ))
            return effects

        if isinstance(action, TempManaBoostAction):
            return [
                TempManaBoostEffect(
                    side=event.side,
                    source_type=source_type,
                    source_id=source_id,
                    amount=action.amount,
                )
            ]

        if isinstance(action, SummonAction):
            return [
                SummonEffect(
                    side=event.side,
                    source_type=source_type,
                    source_id=source_id,
                    target=action.target,
                )
            ]

        if isinstance(action, ClearAction):
            return [
                ClearEffect(
                    side=event.side,
                    source_type=source_type,
                    source_id=source_id,
                    target=action.target,
                )
            ]

        if isinstance(action, BuffAction):
            same_side = event.side

            # Determine base target for buff (buffs target friendly creatures)
            if action.target == "creature":
                base_target_type = "creature"
                base_target_id = event.target_id
            else:
                base_target_type = event.target_type
                base_target_id = event.target_id

            # Get all targets based on scope
            targets = []

            if action.scope == 'single':
                if base_target_id and base_target_type == "creature":
                    targets = [(base_target_type, base_target_id)]

            elif action.scope == 'all':
                # Buff all friendly creatures on same side
                for creature_id in state.board[same_side]:
                    targets.append(("creature", creature_id))

            elif action.scope == 'cleave':
                # Buff target and adjacent creatures
                if base_target_type == "creature" and base_target_id in state.board[same_side]:
                    target_index = state.board[same_side].index(base_target_id)
                    # Add the main target
                    targets.append((base_target_type, base_target_id))
                    # Add left neighbor
                    if target_index > 0:
                        targets.append(("creature", state.board[same_side][target_index - 1]))
                    # Add right neighbor
                    if target_index < len(state.board[same_side]) - 1:
                        targets.append(("creature", state.board[same_side][target_index + 1]))
                elif base_target_id:
                    # If not a creature, just buff the single target
                    targets = [(base_target_type, base_target_id)]

            # Create buff effects for each target
            effects = []
            for target_type, target_id in targets:
                effects.append(BuffEffect(
                    side=event.side,
                    source_type=source_type,
                    source_id=source_id,
                    target_type=target_type,
                    target_id=target_id,
                    attribute=action.attribute,
                    amount=action.amount,
                ))
            return effects

        raise ValueError(f"Invalid action: {action}")


    @staticmethod
    def _update_elo_ratings(game):
        """
        Calculate and save ELO rating changes for PvP matches.
        Only processes games between two human players (not vs AI).
        Updates ratings per-title (each user has a separate rating for each title).
        """
        from apps.gameplay.models import ELORatingChange, UserTitleRating
        from apps.gameplay.elo import ELOCalculator

        # Skip if this is a PvE game (vs AI)
        if game.is_vs_ai:
            logger.info(f"Skipping ELO update for PvE game {game.id}")
            return

        # Skip for friendly unrated matches
        if game.type == Game.GAME_TYPE_FRIENDLY:
            logger.info(f"Skipping ELO update for friendly (unrated) game {game.id}")
            return

        # Skip if no winner (shouldn't happen, but just in case)
        if not game.winner:
            logger.warning(f"Game {game.id} ended without a winner")
            return

        # Skip if ELO change already exists (idempotency)
        if hasattr(game, 'elo_change') and game.elo_change:
            logger.info(f"ELO change already exists for game {game.id}")
            return

        # Get the users and title
        winner_user = game.winner.user
        loser_deck = game.side_a if game.winner == game.side_b else game.side_b
        loser_user = loser_deck.user
        title = game.title

        # Skip if either player is None (shouldn't happen for non-AI games)
        if not winner_user or not loser_user:
            logger.warning(f"Game {game.id} has None user")
            return

        # Get or create title ratings for both users
        winner_rating, _ = UserTitleRating.objects.get_or_create(
            user=winner_user,
            title=title,
            defaults={'elo_rating': 1200}
        )
        loser_rating, _ = UserTitleRating.objects.get_or_create(
            user=loser_user,
            title=title,
            defaults={'elo_rating': 1200}
        )

        # Get current ratings
        winner_old_rating = winner_rating.elo_rating
        loser_old_rating = loser_rating.elo_rating

        # Calculate new ratings
        winner_new_rating, loser_new_rating = ELOCalculator.calculate_new_ratings(
            winner_old_rating,
            loser_old_rating
        )

        # Update title ratings
        winner_rating.elo_rating = winner_new_rating
        loser_rating.elo_rating = loser_new_rating
        winner_rating.save(update_fields=['elo_rating'])
        loser_rating.save(update_fields=['elo_rating'])

        # Create ELO change record
        ELORatingChange.objects.create(
            game=game,
            title=title,
            winner=winner_user,
            winner_old_rating=winner_old_rating,
            winner_new_rating=winner_new_rating,
            winner_rating_change=winner_new_rating - winner_old_rating,
            loser=loser_user,
            loser_old_rating=loser_old_rating,
            loser_new_rating=loser_new_rating,
            loser_rating_change=loser_new_rating - loser_old_rating,
        )

        logger.info(
            f"ELO updated for game {game.id} ({title.name}): "
            f"{winner_user.display_name} {winner_old_rating}->{winner_new_rating}, "
            f"{loser_user.display_name} {loser_old_rating}->{loser_new_rating}"
        )

    @staticmethod
    def _events_to_updates(events):
        """
        Convert events to updates. For now, events map directly to updates.
        In the future, this could handle more complex transformations.
        """
        from apps.gameplay.schemas.updates import (
            ClearUpdate,
            DrawCardUpdate,
            EndTurnUpdate,
            PlayCardUpdate,
            GameOverUpdate,
            DamageUpdate,
            HealUpdate,
            RemoveUpdate,
            SummonUpdate,
            TempManaBoostUpdate,
        )

        updates = []
        for event in events:
            # Map events to corresponding updates
            if event.type == "event_draw":
                updates.append(DrawCardUpdate(
                    side=event.side,
                    card_id=event.card_id,
                    target_type=event.target_type,
                    target_id=event.target_id,
                ))
            elif event.type == "event_play":
                updates.append(PlayCardUpdate(
                    side=event.side,
                    source_type=event.source_type,
                    source_id=event.source_id,
                    card_id=event.source_id,
                    position=event.position,
                    target_type=event.target_type,
                    target_id=event.target_id,
                ))
            elif event.type == "event_damage":
                updates.append(DamageUpdate(
                    side=event.side,
                    source_type=event.source_type,
                    source_id=event.source_id,
                    target_type=event.target_type,
                    target_id=event.target_id,
                    damage=event.damage,
                ))
            elif event.type == "event_heal":
                updates.append(HealUpdate(
                    side=event.side,
                    source_type=event.source_type,
                    source_id=event.source_id,
                    target_type=event.target_type,
                    target_id=event.target_id,
                    amount=event.amount,
                ))
            elif event.type == "event_remove":
                updates.append(RemoveUpdate(
                    side=event.side,
                    source_type=event.source_type,
                    source_id=event.source_id,
                    target_type=event.target_type,
                    target_id=event.target_id,
                ))
            elif event.type == "event_temp_mana_boost":
                updates.append(TempManaBoostUpdate(
                    side=event.side,
                    amount=event.amount,
                ))
            elif event.type == "event_summon":
                updates.append(SummonUpdate(
                    side=event.side,
                    source_type=event.source_type,
                    source_id=event.source_id,
                    target_type=event.target_type,
                    target_id=event.target_id,
                ))
            elif event.type == "event_clear":
                # Get cleared creature IDs from the state before the event
                opposing_side = "side_b" if event.side == "side_a" else "side_a"
                cleared_creature_ids = []
                # We need to figure out which creatures were cleared
                # For now, we'll rely on the event having this info or deduce from sides
                # Since the event doesn't carry this info, we'll leave it empty
                # The frontend can deduce which creatures disappeared from the state
                updates.append(ClearUpdate(
                    side=event.side,
                    source_type=event.source_type,
                    source_id=event.source_id,
                    target=event.target,
                    cleared_creature_ids=[],  # Frontend will detect from state diff
                ))
            elif event.type == "event_game_over":
                updates.append(GameOverUpdate(
                    side=event.side,
                    winner=event.winner,
                ))
            elif event.type == "event_end_turn":
                updates.append(EndTurnUpdate(
                    side=event.side,
                ))

        return updates

    @staticmethod
    @transaction.atomic
    def process_matchmaking(title_id: int):
        """
        Process matchmaking for a specific title.
        Finds two queued players with similar ELO and creates a game for them.

        Uses a simple ELO-based matchmaking algorithm:
        1. Find all queued players for this title
        2. Sort by ELO rating
        3. Match players with closest ratings
        4. Create game and notify both players
        """
        from apps.gameplay.models import MatchmakingQueue, Game
        from apps.builder.models import Title

        logger.info(f"Processing matchmaking for title_id={title_id}")

        # Get all queued entries for this title, ordered by ELO
        queued_entries = list(
            MatchmakingQueue.objects.filter(
                deck__title_id=title_id,
                status=MatchmakingQueue.STATUS_QUEUED
            )
            .select_related('user', 'deck', 'deck__hero', 'deck__title')
            .order_by('elo_rating')
        )

        if len(queued_entries) < 2:
            logger.info(f"Not enough players in queue ({len(queued_entries)}), skipping matchmaking")
            return 0

        # Simple matchmaking: pair closest ELO ratings
        # More sophisticated algorithms could consider wait time, rank tiers, etc.
        matched_pairs = []
        used_indices = set()

        for i in range(len(queued_entries)):
            if i in used_indices:
                continue

            entry_a = queued_entries[i]
            best_match = None
            best_diff = float('inf')
            best_index = None

            # Find closest ELO opponent
            for j in range(len(queued_entries)):
                if i == j or j in used_indices:
                    continue

                entry_b = queued_entries[j]

                # Don't match users against themselves
                if entry_a.user_id == entry_b.user_id:
                    continue

                elo_diff = abs(entry_a.elo_rating - entry_b.elo_rating)
                if elo_diff < best_diff:
                    best_diff = elo_diff
                    best_match = entry_b
                    best_index = j

            if best_match:
                matched_pairs.append((entry_a, best_match))
                used_indices.add(i)
                used_indices.add(best_index)
                logger.info(
                    f"Matched {entry_a.user.display_name} (ELO: {entry_a.elo_rating}) "
                    f"with {best_match.user.display_name} (ELO: {best_match.elo_rating}), "
                    f"diff: {best_diff}"
                )

        # Create games for each matched pair
        for entry_a, entry_b in matched_pairs:
            try:
                # Create the game
                game = GameService.create_game(
                    entry_a.deck,
                    entry_b.deck,
                    randomize_starting_player=True,
                )

                # Set game type to ranked for matchmaking games
                game.type = Game.GAME_TYPE_RANKED
                game.save(update_fields=['type'])

                # Update time_per_turn in game state based on title config
                from apps.gameplay.schemas.game import GameState
                game_state = GameState.model_validate(game.state)
                game_state.time_per_turn = game_state.config.ranked_time_per_turn
                game.state = game_state.model_dump()
                game.save(update_fields=['state'])

                # Update both queue entries
                entry_a.status = MatchmakingQueue.STATUS_MATCHED
                entry_a.matched_with = entry_b
                entry_a.game = game
                entry_a.save(update_fields=['status', 'matched_with', 'game'])

                entry_b.status = MatchmakingQueue.STATUS_MATCHED
                entry_b.matched_with = entry_a
                entry_b.game = game
                entry_b.save(update_fields=['status', 'matched_with', 'game'])

                logger.info(f"Created ranked game {game.id} for matched players")

                # Kick off first step to initialize the game
                from apps.gameplay.tasks import step
                step.delay(game.id)

                # Notify both players via websocket
                from apps.gameplay.notifications import send_matchmaking_success
                title_slug = getattr(entry_a.deck.title, 'slug', None)
                if title_slug:
                    send_matchmaking_success(entry_a.user_id, game.id, title_slug)
                    send_matchmaking_success(entry_b.user_id, game.id, title_slug)

            except Exception as e:
                logger.error(f"Failed to create game for matched pair: {e}")
                # Reset queue entries on failure
                entry_a.status = MatchmakingQueue.STATUS_QUEUED
                entry_a.save(update_fields=['status'])
                entry_b.status = MatchmakingQueue.STATUS_QUEUED
                entry_b.save(update_fields=['status'])

        matches_created = len(matched_pairs)
        logger.info(f"Matchmaking complete: created {matches_created} games")
        return matches_created

    @staticmethod
    @transaction.atomic
    def check_expired_turns():
        """
        Check all active games for expired turns and automatically concede.
        This is called periodically to catch timeouts even when no effects are being processed.
        """
        from django.utils import timezone
        from apps.gameplay.schemas.effects import ConcedeEffect

        now = timezone.now()

        # Find all active games in main phase with turn_expires set
        expired_games = Game.objects.filter(
            status=Game.GAME_STATUS_IN_PROGRESS,
            turn_expires__isnull=False,
            turn_expires__lte=now
        ).select_for_update(nowait=False)

        for game in expired_games:
            try:
                game_state = GameState.model_validate(game.state)

                # Only process if in main phase and has time control
                if game_state.phase == 'main' and game_state.time_per_turn > 0:
                    logger.info(f"Turn expired for {game_state.active} in game {game.id}, auto-conceding")
                    game.enqueue([ConcedeEffect(side=game_state.active)], trigger=True)
            except Exception as e:
                logger.error(f"Error checking expired turn for game {game.id}: {e}")
                continue

        return f"Checked {len(expired_games)} games for expired turns"

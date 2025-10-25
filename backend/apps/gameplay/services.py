import logging
import random
import traceback
import uuid

from django.db import transaction, DatabaseError
from pydantic import TypeAdapter, ValidationError

logger = logging.getLogger(__name__)

from apps.builder.schemas import (
    Action,
    DeckScript,
    DrawAction,
    DamageAction,
    HealAction,
    RemoveAction,
    TitleConfig,
)
from apps.core.serializers import serialize_cards_with_traits
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
    PlayCardCommand,
    EndTurnCommand,
    UseHeroCommand,
)
from apps.gameplay.schemas.effects import (
    AttackEffect,
    DamageEffect,
    DrawEffect,
    Effect,
    EndTurnEffect,
    HealEffect,
    PlayEffect,
    RemoveEffect,
    StartGameEffect,
    UseHeroEffect,
)
from apps.gameplay.schemas.engine import Success, Result, Prevented, Rejected, Fault
from apps.gameplay.schemas.events import (
    ActionableEvent,
    Event,
    GameOverEvent,
    UseHeroEvent,
)


# Moved to avoid circular import - imported where needed


from apps.gameplay.schemas.game import GameState
from apps.gameplay.notifications import send_game_updates_to_clients


class GameService:

    @staticmethod
    @transaction.atomic
    def start_game(deck_a, deck_b) -> Game:

        existing_game = Game.objects.filter(
            side_a=deck_a,
            side_b=deck_b,
        ).exclude(
            status=Game.GAME_STATUS_ENDED,
        ).first()
        if existing_game:
            return existing_game

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

            for _ in range(deck_a_card_copies[card["id"]]):

                card_id += 1
                cards_in_play[str(card_id)] = CardInPlay(
                    card_type=card["card_type"],
                    card_id=str(card_id),
                    template_slug=card["slug"],
                    name=card["name"],
                    description=card["description"],
                    attack=card["attack"],
                    health=card["health"],
                    cost=card["cost"],
                    traits=card["traits"],
                )
                decks['side_a'].append(str(card_id))

        for card in cards_b:

            for _ in range(deck_b_card_copies[card["id"]]):

                card_id += 1
                cards_in_play[str(card_id)] = CardInPlay(
                    card_type=card["card_type"],
                    card_id=str(card_id),
                    template_slug=card["slug"],
                    name=card["name"],
                    description=card["description"],
                    attack=card["attack"],
                    health=card["health"],
                    cost=card["cost"],
                    traits=card["traits"],
                )
                decks['side_b'].append(str(card_id))

        # shuffle both decks
        random.shuffle(decks['side_a'])
        random.shuffle(decks['side_b'])

        heroes = {
            'side_a': HeroInPlay(
                hero_id=str(deck_a.hero.id),
                template_slug=deck_a.hero.slug,
                health=deck_a.hero.health,
                name=deck_a.hero.name,
                hero_power=deck_a.hero.hero_power,
                exhausted=False,
            ),
            'side_b': HeroInPlay(
                hero_id=str(deck_b.hero.id),
                template_slug=deck_b.hero.slug,
                health=deck_b.hero.health,
                name=deck_b.hero.name,
                hero_power=deck_b.hero.hero_power,
                exhausted=False,
            ),
        }

        ai_sides = []
        if deck_a.is_ai_deck:
            ai_sides.append('side_a')
        if deck_b.is_ai_deck:
            ai_sides.append('side_b')

        config = TitleConfig.model_validate(deck_a.title.config)

        game_state = GameState(
            turn=0,
            active='side_a',
            phase='start',
            cards=cards_in_play,
            heroes=heroes,
            decks=decks,
            ai_sides=ai_sides,
            config=config,
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
                            break

                    # Enqueue child effects (depth-first)
                    if result.child_effects:
                        game.enqueue(result.child_effects, trigger=False, prepend=True)

                    all_events.extend(result.events)

                    # Process trait triggers for each event
                    from apps.gameplay import traits
                    for event in result.events:
                        trait_result = traits.apply(game_state, event)
                        if trait_result.child_effects:
                            game.enqueue(trait_result.child_effects, trigger=False, prepend=True)

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
        game.save(update_fields=["state", "queue", "status"])

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
            ai_event = GameService.choose_ai_move(game_state, script)
            if ai_event:
                game.enqueue([ai_event], trigger=False)
            else:
                game.enqueue([EndTurnEffect(side=game.state['active'])], trigger=False)

        # Continue processing if there are more effects in queue
        if len(game.queue) > 0:
            from apps.gameplay.tasks import step
            step.apply_async(args=[game_id], countdown=0.1)

    @staticmethod
    def process_command(game_id: int, command: dict, side):
        try:
            game = Game.objects.get(id=game_id)
        except Game.DoesNotExist:
            raise ValueError(f"Game with id {game_id} does not exist")

        game_state = GameState.model_validate(game.state)
        effects = GameService.compile_cmd(game_state, command, side)
        game.enqueue(effects)

    @staticmethod
    def compile_cmd(game_state: GameState, command: dict, side) -> list[Effect]:
        "Translates a Command into a list of Effect objects"

        if side != game_state.active:
            raise ValueError(f"It is not your turn.")

        effects = []

        command = TypeAdapter(Command).validate_python(command)

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
            # Validate that the hero belongs to the active player
            active_hero = game_state.heroes.get(game_state.active)
            if not active_hero or active_hero.hero_id != command.hero_id:
                raise ValueError(f"You do not control hero {command.hero_id}")

            # Validate that the target belongs to the opponent (if there is a target)
            if target_type:
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
        if isinstance(action, DrawAction):
            return [DrawEffect(
                side=event.side,
                amount=action.amount,
            )]

        if isinstance(action, DamageAction):
            opposing_side = state.opposite_side

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
                    damage_type="physical",
                    source_type=event.source_type,
                    source_id=event.source_id,
                    target_type=target_type,
                    target_id=target_id,
                    damage=action.amount,
                    retaliate=False,
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
                    source_type=event.source_type,
                    source_id=event.source_id,
                    target_type=target_type,
                    target_id=target_id,
                    amount=action.amount,
                ))
            return effects

        if isinstance(action, RemoveAction):
            opposing_side = state.opposite_side

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
                    source_type=event.source_type,
                    source_id=event.source_id,
                    target_type=target_type,
                    target_id=target_id,
                ))
            return effects

        raise ValueError(f"Invalid action: {action}")

    @staticmethod
    def choose_ai_move(state: GameState, script: DeckScript) -> Effect | None:

        mana_pool = state.mana_pool[state.active]
        mana_used = state.mana_used[state.active]
        mana_available = mana_pool - mana_used

        opposing_side = "side_b" if state.active == "side_a" else "side_a"

        # See if there's a card that can be played from hand to board
        for card_id in state.hands[state.active]:
            card = state.cards[card_id]
            if card.cost <= mana_available and card.card_type == 'creature':
                card_id_to_play = card_id
                return PlayEffect(
                    side=state.active,
                    source_id=card_id_to_play,
                    position=0,
                )

        # Check for taunt creatures on the opposing board
        from apps.gameplay.engine.handlers import get_taunt_creatures
        taunt_creatures = get_taunt_creatures(state, opposing_side)

        # See if there's a creature that can be used to attack
        for creature_id in state.board[state.active]:
            creature = state.creatures[creature_id]

            if creature.exhausted: continue

            # If there are taunt creatures, we MUST attack one of them
            if taunt_creatures:
                target_type = "creature"
                target_id = random.choice(taunt_creatures)
            elif script.strategy == "rush":
                target_type = "hero"
                target_id = state.heroes[opposing_side].hero_id
            elif script.strategy == "control":
                target_type = "creature"
                target_id = random.choice(state.board[opposing_side])
            else:
                # 50/50 chance to attack hero or card
                if random.random() < 0.5:
                    target_type = "hero"
                    target_id = state.heroes[opposing_side].hero_id
                else:
                    target_type = "creature"
                    try:
                        target_id = random.choice(state.board[opposing_side])
                    except IndexError:
                        target_type = "hero"
                        target_id = state.heroes[opposing_side].hero_id

            return AttackEffect(
                side=state.active,
                card_id=creature_id,
                target_type=target_type,
                target_id=target_id)

        return

    @staticmethod
    def _events_to_updates(events):
        """
        Convert events to updates. For now, events map directly to updates.
        In the future, this could handle more complex transformations.
        """
        from apps.gameplay.schemas.updates import (
            DrawCardUpdate,
            PlayCardUpdate,
            GameOverUpdate,
            DamageUpdate,
            HealUpdate,
        )

        updates = []
        for event in events:
            # Map events to corresponding updates
            if event.type == "event_draw":
                updates.append(DrawCardUpdate(
                    side=event.side,
                    card_id=event.card_id,
                ))
            elif event.type == "event_play":
                updates.append(PlayCardUpdate(
                    side=event.side,
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
            elif event.type == "event_game_over":
                updates.append(GameOverUpdate(
                    side=event.side,
                    winner=event.winner,
                ))
            # Add more event-to-update mappings as needed

        return updates

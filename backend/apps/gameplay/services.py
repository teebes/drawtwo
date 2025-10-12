import random

from django.db import transaction, DatabaseError
from pydantic import TypeAdapter, ValidationError

from apps.builder.schemas import (
    Action,
    DeckScript,
    DrawAction,
    DamageAction,
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
    Command,
    PlayCardCommand,
    EndTurnCommand,
    UseCardCommand,
    UseHeroCommand,
)
from apps.gameplay.schemas.effects import (
    DamageEffect,
    DrawEffect,
    Effect,
    EndTurnEffect,
    PlayEffect,
    StartGameEffect,
    UseCardEffect,
    UseHeroEffect,
)
from apps.gameplay.schemas.engine import Success, Result, Prevented, Rejected, Fault
from apps.gameplay.schemas.events import GameOverEvent

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
            ),
            'side_b': HeroInPlay(
                hero_id=str(deck_b.hero.id),
                template_slug=deck_b.hero.slug,
                health=deck_b.hero.health,
                name=deck_b.hero.name,
                hero_power=deck_b.hero.hero_power,
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
    def advance(game_id: int):

        try:
            game = (Game.objects
                        .select_for_update(nowait=True)
                        .get(id=game_id))
        except DatabaseError:
            return

        print("==== STEP FUNCTION with queue: ====")
        print(game.queue)

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
                print(f"Invalid effect: {effect}")
                continue

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
                print(f"Effect {result.type}: {result.reason}")
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
                print(f"⚠️  FAULT: {result.reason} (error_id: {result.error_id})")
                all_errors.append({
                    'error_id': result.error_id,
                    'reason': result.reason,
                    'details': result.details,
                    'effect': effect.model_dump(mode="json"),
                })

                # If unrecoverable, stop processing to avoid cascading failures
                if not result.retryable:
                    print(f"Non-retryable fault encountered, stopping effect processing")
                    break
                # Otherwise continue processing (retryable faults)

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
            from apps.gameplay.tasks import advance
            advance.apply_async(args=[game_id], countdown=0.1)

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

        # See if there's a card that can be used to attack, and if there is,
        # attack the hero.
        for card_id in state.board[state.active]:
            card = state.cards[card_id]

            if card.exhausted: continue

            if script.strategy == "rush":
                target_type = "hero"
                target_id = state.heroes[opposing_side].hero_id
            elif script.strategy == "control":
                target_type = "card"
                target_id = random.choice(state.board[opposing_side])
            else:
                # 50/50 chance to attack hero or card
                if random.random() < 0.5:
                    target_type = "hero"
                    target_id = state.heroes[opposing_side].hero_id
                else:
                    target_type = "card"
                    try:
                        target_id = random.choice(state.board[opposing_side])
                    except IndexError:
                        target_type = "hero"
                        target_id = state.heroes[opposing_side].hero_id

            return UseCardEffect(
                side=state.active,
                card_id=card_id,
                target_type=target_type,
                target_id=target_id)

        return

    @staticmethod
    def process_command(game_id: int, command: dict, side):
        try:
            game = Game.objects.get(id=game_id)
        except Game.DoesNotExist:
            raise ValueError(f"Game with id {game_id} does not exist")

        game_state = GameState.model_validate(game.state)
        print('state is good')
        effects = GameService.compile(game_state, command, side)
        print('effects: %s' % effects)
        game.enqueue(effects)

    @staticmethod
    def compile(game_state: GameState, command: dict, side) -> list[Effect]:
        "Translates a Command into a list of Effect objects"

        if side != game_state.active:
            raise ValueError(f"It is not your turn.")

        effects = []

        try:
            command = TypeAdapter(Command).validate_python(command)
        except ValidationError as e:
            # Extract the command type that was sent
            sent_type = command.get('type', 'unknown')
            raise ValueError(f"Invalid command type '{sent_type}'")

        # Because we're transitioning to a system where the cards on the
        # board are creatures and not just cards, we make the transition
        # easier for the frontend by translating the target when possible.
        target_type = command.target_type
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
        elif isinstance(command, UseCardCommand):
            effects.append(UseCardEffect(
                side=game_state.active,
                card_id=command.card_id,
                target_type=target_type,
                target_id=command.target_id,
            ))
        elif isinstance(command, UseHeroCommand):
            effects.append(UseHeroEffect(
                side=game_state.active,
                source_id=command.hero_id,
                target_type=target_type,
                target_id=command.target_id,
            ))
        else:
            raise ValueError(f"Invalid command: {command}")

        return effects

    @staticmethod
    def compile_action(game_state: GameState, action: Action) -> Effect:
        if isinstance(action, DrawAction):
            return DrawEffect(
                side=game_state.active,
                amount=action.amount,
            )
        elif isinstance(action, DamageAction):
            return DamageEffect(
                side=game_state.active,
                damage_type="physical",
                source_type="card",
                source_id=action.source_id,
                target_type=action.target_type,
                target_id=action.target_id,
                damage=action.amount,
                retaliate=False,
            )
        raise ValueError(f"Invalid action: {action}")

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
                    card_id=event.card_id,
                    position=event.position,
                    target_type=event.target_type,
                    target_id=event.target_id,
                ))
            elif event.type == "event_game_over":
                updates.append(GameOverUpdate(
                    side=event.side,
                    winner=event.winner,
                ))
            # Add more event-to-update mappings as needed

        return updates

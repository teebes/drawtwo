from django.core.management.base import BaseCommand, CommandError

from apps.builder.schemas import DeckScript
from apps.collection.models import Deck
from apps.gameplay.agents.legal import list_legal_commands
from apps.gameplay.agents.policies.scripted import ScriptedPolicy
from apps.gameplay.agents.simulator import apply_command, apply_effects
from apps.gameplay.models import Game
from apps.gameplay.schemas.effects import StartGameEffect
from apps.gameplay.services import GameService


def _decision_side(state):
    if state.phase == "mulligan":
        for side in ("side_a", "side_b"):
            if not state.mulligan_done.get(side, False):
                return side
    return state.active


class Command(BaseCommand):
    help = "Run local scripted self-play through the agent simulator."

    def add_arguments(self, parser):
        parser.add_argument("--deck-a", type=int, required=True)
        parser.add_argument("--deck-b", type=int, required=True)
        parser.add_argument("--games", type=int, default=1)
        parser.add_argument("--max-decisions", type=int, default=300)
        parser.add_argument(
            "--keep-games",
            action="store_true",
            help="Keep the temporary Game rows created for initial state setup.",
        )

    def handle(self, *args, **options):
        deck_a = Deck.objects.get(id=options["deck_a"])
        deck_b = Deck.objects.get(id=options["deck_b"])
        if deck_a.title_id != deck_b.title_id:
            raise CommandError("Decks must belong to the same title.")
        if options["keep_games"] and options["games"] > 1:
            raise CommandError("--keep-games currently supports one game at a time.")

        existing_game = (
            Game.objects.filter(side_a=deck_a, side_b=deck_b)
            .exclude(status=Game.GAME_STATUS_ENDED)
            .first()
        )
        if existing_game:
            raise CommandError(
                "An active Game already exists for these exact decks. "
                "Use dedicated self-play decks or finish/delete that game first."
            )

        summaries = []
        for index in range(options["games"]):
            game = GameService.create_game(
                deck_a,
                deck_b,
                randomize_starting_player=True,
            )
            try:
                state = game.game_state
                state.ai_sides = []
                start_result = apply_effects(state, [StartGameEffect(side="side_a")])
                state = start_result.state

                policies = {
                    "side_a": ScriptedPolicy(
                        DeckScript.model_validate(deck_a.script or {})
                    ),
                    "side_b": ScriptedPolicy(
                        DeckScript.model_validate(deck_b.script or {})
                    ),
                }

                decisions = 0
                while state.winner == "none" and decisions < options["max_decisions"]:
                    side = _decision_side(state)
                    legal_commands = list_legal_commands(state, side)
                    command = policies[side].select_command(state, legal_commands)
                    if command is None:
                        break
                    result = apply_command(state, side, command)
                    state = result.state
                    decisions += 1

                summaries.append(
                    {
                        "game": index + 1,
                        "winner": state.winner,
                        "decisions": decisions,
                    }
                )
            finally:
                if not options["keep_games"]:
                    game.delete()

        for summary in summaries:
            self.stdout.write(
                "game={game} winner={winner} decisions={decisions}".format(**summary)
            )

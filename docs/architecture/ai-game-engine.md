# AI Game Engine Plan

This document plans how to build a strong AI player for Archetype first, while
making the DrawTwo platform changes reusable for other games that run on the
same gameplay engine.

## Recommendation

Start with Archetype, not "any arbitrary DrawTwo game."

Archetype is the right first target because it is already represented by the
current DrawTwo title/content system: heroes, decks, cards, traits, commands,
effects, events, and a Pydantic `GameState`. That gives us a real game with a
bounded ruleset and enough complexity to learn meaningful play.

Do not hard-code an Archetype-only bot into the product, though. The platform
work should produce generic agent-facing primitives:

- legal command enumeration
- deterministic simulation
- player-perspective observations
- replay/action logs
- agent model/version metadata
- offline self-play and evaluation harnesses

Once those exist, Archetype becomes the first supported environment rather than
a one-off. Supporting "any DrawTwo game" can come later for titles that stay
inside this engine's command/action/trait model. Truly arbitrary games would
need a more formal game-description interface and separate agent adapters.

## Current Platform Shape

Relevant existing pieces:

- `backend/apps/gameplay/schemas/game.py` defines `GameState`, `CardInPlay`,
  `Creature`, and `HeroInPlay`.
- `backend/apps/gameplay/schemas/commands.py` defines the human-facing command
  vocabulary: play card, attack, use hero, end turn, concede, mulligan.
- `backend/apps/gameplay/schemas/effects.py` and
  `backend/apps/gameplay/engine/handlers.py` resolve lower-level effects.
- `backend/apps/gameplay/services.py` owns game creation, command compilation,
  effect stepping, event-to-update conversion, matchmaking, timers, and the
  current AI trigger.
- `backend/apps/gameplay/ai.py` contains the current rule-based `AIMoveChooser`.
  It chooses effects directly from the live state.
- `backend/apps/builder/schemas.py` defines title content primitives: cards,
  heroes, traits, actions, title config, and a small `DeckScript`.
- `backend/apps/collection/models.py` already supports AI-owned decks through
  `Deck.ai_player`.
- `backend/apps/builder/models.py` already has an `AIPlayer` model with
  difficulty and `strategy_config`.

The current AI is useful as a baseline opponent, but it is not a chess-engine
style AI. It has no search, no learned evaluation, no legal-action list, no
deterministic simulator, and no training loop.

## Platform Gaps To Fix

### 1. Legal Command Enumeration

Agents need the same action surface humans have, not direct effect access.

Add a backend module such as `backend/apps/gameplay/agents/legal.py`:

```python
def list_legal_commands(state: GameState, side: str) -> list[Command]:
    ...
```

It should enumerate:

- mulligan choices during mulligan
- playable cards and all valid board positions
- required targets for targeted battlecries and spells
- legal creature attacks, including taunt, stealth, exhaustion, and zero attack
- legal hero-power targets
- `cmd_end_turn`
- `cmd_concede` only for live-game integration, not training action selection

The frontend currently duplicates target inference in `Board.vue` and board
components. Centralizing legal actions in the backend gives humans, bots,
training, and UI hints the same source of truth.

### 2. Deterministic Simulation

Training and search need fast, repeatable simulation without Celery, WebSockets,
or database writes.

Add a pure simulator around the existing command/effect engine:

```python
def apply_command(
    state: GameState,
    side: str,
    command: Command,
) -> SimulationResult:
    ...
```

`SimulationResult` should include:

- next `GameState`
- emitted events/updates
- rejected/fault outcome if illegal
- terminal winner if any
- state hashes before/after

The simulator should reuse the same command compiler and effect handlers as live
games. Avoid maintaining a second rules implementation.

### 3. Controlled Randomness

Current game creation and AI choice use Python's global `random` module for deck
shuffle, mulligan shuffle-back, starting player, and simple AI choices. That is
fine for live play but bad for training reproducibility.

Add seeded randomness to game state or simulation context:

- `GameState.random_seed`
- optional `GameState.rng_state`
- helper methods for shuffle/choice
- state hashes that include RNG state when replay fidelity matters

Every self-play game should be reproducible from ruleset id, decks, starting
seed, and command sequence.

### 4. Player-Perspective Observations

The model must see the game the way a person does. It should not receive hidden
opponent hand contents or deck order.

Create an explicit observation schema instead of passing raw `GameState`:

```python
class AgentObservation(BaseModel):
    side: Literal["side_a", "side_b"]
    public_state: ...
    own_hand: list[str]
    hidden_counts: ...
    known_history: list[Event]
```

Also fix `filter_state_for_side` in `backend/apps/gameplay/notifications.py`.
It currently returns the full state before the hidden-information filtering code
runs. That means opponent hand/deck contents are exposed to clients today.

Training can use two observation modes:

- public observation for real bot play and human-like training
- privileged full state for debugging, oracle evaluation, or teacher models

The deployed agent should use public observations.

### 5. Replay And Action Logging

`GameUpdate` records display updates, but training needs decisions.

Add a durable action log, for example `GameAction`:

- game id
- title/ruleset id
- actor side
- turn and phase
- submitted command
- legal command list or legal mask
- pre-state hash
- post-state hash
- accepted/rejected outcome
- wall-clock decision time for humans
- final winner once known

Then add exporters:

- `export_replays` to JSONL/Parquet
- `export_positions` for supervised policy/value datasets
- filters by title, ruleset, ladder type, date range, player rating, and game
  status

Human games become imitation-learning data; self-play games become RL/evaluation
data.

### 6. Agent Runtime Interface

Replace the current `AIMoveChooser.choose_move(state, script) -> Effect | None`
shape with a command-level interface:

```python
class AgentPolicy(Protocol):
    def select_command(
        self,
        observation: AgentObservation,
        legal_commands: list[Command],
        budget_ms: int,
    ) -> Command:
        ...
```

Implement several policies:

- `RandomLegalPolicy` for testing
- `ScriptedPolicy` to preserve current PvE behavior
- `SearchPolicy` for heuristic/MCTS play
- `ModelPolicy` that calls a model server or loads a local model

Live games should enqueue the selected command through the same
`GameService.process_command` path used by humans.

### 7. Ruleset And Content Versioning

DrawTwo already has version fields for titles, cards, and heroes, though some
editing paths still update the latest row in place. The AI system needs content
publishing to produce a stricter compatibility id:

```text
ruleset_id = hash(
  engine schema versions +
  effect handler version +
  title config +
  latest hero/card/template manifests +
  trait/action definitions
)
```

Store `ruleset_id` on:

- created games
- exported replay rows
- trained model metadata
- evaluation results
- deployed AI profiles

This is the bridge between changing game content and knowing whether a model is
still valid.

## Training Architecture

Keep the canonical rules and live inference integration in this repository.
Keep heavyweight training code in a separate package or sibling repository once
it grows.

A pragmatic layout:

```text
drawtwo/
  backend/apps/gameplay/agents/
    legal.py
    observation.py
    simulator.py
    policies/
      random.py
      scripted.py
      search.py
      model_client.py
  backend/apps/gameplay/management/commands/
    export_replays.py
    run_selfplay.py

drawtwo-ai/ or drawtwo/ai/
  envs/drawtwo_env.py
  encoders/
  training/
  evaluation/
  models/
```

The DrawTwo repo should stay responsible for correctness of the environment.
The AI repo/package should own PyTorch/JAX dependencies, training jobs,
checkpoints, experiment tracking, and large generated datasets.

For early work, a local `ai/` subdirectory is acceptable. Split it out when the
dependency weight or experiment churn starts making the web app harder to run.

## Model Approach

### Baseline Engine First

Before training a neural model, build a non-neural engine:

- legal-action enumeration
- simple position evaluator
- one-ply and shallow search
- optional Monte Carlo Tree Search using random/scripted rollouts
- tactical checks for lethal damage, survival, favorable trades, and mana use

This gives us:

- a stronger PvE bot quickly
- a benchmark for learned models
- a teacher for generating early self-play
- debugging pressure on legal actions and simulator determinism

### Observation Encoding

Use side-relative encoding so the same model can play either side:

- own hero and enemy hero health/exhaustion/power features
- mana pool, mana used, turn, phase
- own hand cards with card feature vectors
- own board and enemy board in board-position order
- deck/hand/graveyard counts
- public event history or compressed recent-action features
- hidden-information counts, not hidden card identities

Card features should be mostly semantic, not just template ids:

- cost, attack, health, card type
- trait/action types
- action amount, target, scope, damage type
- hero restriction/faction if relevant

Template-id embeddings are still useful for known cards, but semantic features
make new cards less catastrophic after content updates.

### Action Encoding

Use a legal-action-list policy instead of a fixed global action head.

For each decision:

1. Enumerate legal commands.
2. Encode each candidate command with source, target, position, and command type.
3. Score each legal command.
4. Choose from the scored legal list.

This handles dynamic hands, board sizes, target choices, and future cards better
than trying to reserve fixed logits for every possible card/target combination.

### Training Stages

1. **Imitation learning from human games**
   - Export human decision points.
   - Train policy to predict selected command from legal commands.
   - Train value head from eventual game outcome.

2. **Self-play reinforcement learning**
   - Generate games between current model versions and baselines.
   - Train from improved targets, e.g. MCTS policy targets and final outcome.
   - Keep a pool of previous models to avoid overfitting to the latest self.

3. **Evaluation arena**
   - Run fixed deck matchups across many seeds.
   - Compare against random, scripted, search, previous neural models, and
     selected human Elo bands.
   - Promote only when win rate and regression checks pass.

4. **Deployment**
   - Register model metadata against `ruleset_id`.
   - Attach model version to an `AIPlayer` profile.
   - Let live PvE games call a model service through `ModelPolicy`.
   - Enforce decision time budgets and fallback to scripted/search policy.

## What Happens When Rules Or Content Change?

Treat every gameplay/content change as a new substrate version.

### Small Balance Changes

Examples: card cost changes, attack/health tweaks, hero health changes.

Flow:

1. Publish new title/card/hero versions.
2. Generate a new `ruleset_id`.
3. Mark previous models as "compatible but stale" only if schemas did not
   change.
4. Run evaluation against the new ruleset.
5. Fine-tune from the previous model using fresh self-play.
6. Promote if it beats the previous deployed model and baselines.

For pure numeric changes, warm-starting from the previous model should usually
work.

### New Cards Or Heroes

Flow:

1. Add content and generate a new `ruleset_id`.
2. Ensure the card/hero encoder can represent the new templates.
3. Generate targeted self-play with decks containing the new content.
4. Fine-tune or retrain.
5. Evaluate both old staple decks and new-content decks.
6. Promote a model for the new ruleset.

Semantic card features help the model make reasonable first guesses. Template
embeddings for new cards/heroes can start randomly initialized or copied from
similar cards.

### New Abilities Or Systems

Examples: a new trait type, new action type, new resource, simultaneous choice,
secret information mechanic, drafting, or nonstandard turn structure.

Flow:

1. Update Pydantic schemas, effect handlers, legal-action enumeration, and
   observation/action encoders.
2. Add simulator tests for the new mechanic.
3. Add legality tests that cover all new command choices and invalid cases.
4. Generate a new incompatible `ruleset_id`.
5. Retrain or heavily fine-tune; do not assume old models remain valid.
6. Run regression arenas across old and new mechanics.
7. Promote only after the model demonstrates competence with the new system.

When the action space or observation schema changes, previous checkpoints may be
useful as partial initialization but should not be treated as directly
compatible.

## Implementation Phases

### Phase 1: Make The Platform Agent-Ready

- Add `list_legal_commands`.
- Add `AgentObservation` and real hidden-information filtering.
- Add deterministic simulator and seeded game creation.
- Add state hashing.
- Change current AI to select `Command` objects, not `Effect` objects.
- Add unit tests comparing legal commands to accepted/rejected command behavior.

### Phase 2: Build A Strong Archetype Baseline

- Implement random and scripted legal-command policies.
- Implement a heuristic evaluator for Archetype/current engine.
- Add shallow search or MCTS.
- Add a self-play management command that runs without WebSockets.
- Track win rates across fixed deck matchups and seeds.

### Phase 3: Collect And Export Training Data

- Add `GameAction` logging for live games.
- Export human and self-play decision rows.
- Build a reproducible dataset format keyed by `ruleset_id`.
- Add replay verification that re-simulates command logs and checks state hashes.

### Phase 4: Train Neural Policy/Value Models

- Build an offline environment wrapper around the simulator.
- Train imitation-learning policy from human games.
- Add self-play reinforcement learning.
- Evaluate in an arena before promotion.
- Register and serve model versions.

### Phase 5: Generalize Beyond Archetype

- Confirm which DrawTwo titles stay inside the current card-game engine.
- Add title-level agent capability flags.
- Use semantic card/action encoding so models can transfer across title content.
- Train title-specific models first.
- Later explore multi-title models if titles share enough mechanics.

## Key Risks

- Hidden information is currently not enforced in `filter_state_for_side`; fix
  that before any deployed learned AI.
- If legal-action generation and command validation diverge, training will learn
  impossible moves. Tests should assert every listed legal command is accepted.
- If the simulator forks from live rules, evaluation results become misleading.
  The simulator must reuse live command/effect code.
- Python/Django object overhead may be too slow for large-scale self-play. Start
  with correctness, then profile. Only port hot paths after the rules are stable.
- Content changes can silently invalidate models unless every dataset, game, and
  checkpoint is tied to a `ruleset_id`.

## Near-Term Decision

Build Archetype AI first. Build it through generic agent interfaces in DrawTwo,
not through an Archetype-only side channel.

The first concrete milestone should be:

1. `list_legal_commands(state, side)`
2. `apply_command(state, side, command)`
3. seeded self-play between `RandomLegalPolicy` and the current scripted policy
4. replay/action logging with state hashes

After that, we can build a search engine and have a credible baseline before
spending time on neural training infrastructure.

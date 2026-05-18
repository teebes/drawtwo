# Live Model AI For PvE

This documents the first live-game bridge from a trained local checkpoint into
the existing PvE AI path.

## Current Shape

Normal PvE games still work exactly as before unless an AI player is explicitly
configured to use a model.

The switch lives in `AIPlayer.strategy_config`:

```json
{
  "policy": "linear_model",
  "model_path": "/app/ai/checkpoints/healer-vs-sniper-linear-stream-fullscan.json"
}
```

If `policy` is missing or set to `scripted`, the deck uses the existing
scripted AI. If the model file cannot be loaded, live games fall back to the
scripted AI instead of getting stuck.

## How A Live AI Move Works

1. `GameService.step()` finishes resolving queued effects.
2. If the active side is in `game.state["ai_sides"]`, it asks
   `AIMoveChooser.choose_decision()` for a command.
3. `AIMoveChooser` reads the active deck's `ai_player.strategy_config`.
4. For `policy=linear_model`, `LinearModelPolicy` loads the checkpoint and
   scores the legal commands from `list_legal_commands()`.
5. The selected command is compiled through the same `GameService.compile_cmd()`
   path used by human commands.
6. `GameAction.actor_kind` is recorded as `model_ai` for model decisions and
   `scripted_ai` for scripted or fallback decisions.

The model never invents arbitrary engine effects. It only ranks commands that
the platform has already declared legal.

## Configure A Local AI Deck

Pick an existing AI deck ID, then run:

```bash
docker-compose exec backend python manage.py set_ai_policy \
  --ai-deck-id AI_DECK_ID \
  --policy linear_model \
  --model /app/ai/checkpoints/healer-vs-sniper-linear-stream-fullscan.json
```

To revert that AI player to the scripted policy:

```bash
docker-compose exec backend python manage.py set_ai_policy \
  --ai-deck-id AI_DECK_ID \
  --policy scripted
```

`--ai-player-id` can be used instead of `--ai-deck-id` if you want to configure
the AI player directly.

## Production Note

Local development mounts `./ai` into `/app/ai`, so checkpoint files under
`ai/checkpoints/` are visible to the backend container.

Production currently pulls a backend image built from `backend/`, while the
training/model code lives in the repo-level `ai/` directory and generated
checkpoints are ignored by git. Before using model AI on prod, both the `ai/`
package and the checkpoint file need to be made available to the backend and
worker containers. The likely path is either mounting an AI artifact directory
or changing the production image build so it includes the runtime pieces of
`ai/` plus a separate model artifact deploy step.

## Current Limits

- This is a linear command ranker, not the future neural/RL engine.
- The live policy is only as broad as the self-play or replay data it was
  trained on.
- The current config is per `AIPlayer`, so all decks owned by that AI player
  share the same policy.
- There is no UI for selecting a checkpoint yet; configuration is via management
  command or admin JSON.

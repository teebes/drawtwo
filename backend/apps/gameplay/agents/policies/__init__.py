from apps.builder.schemas import DeckScript
from apps.gameplay.agents.policies.random import RandomLegalPolicy
from apps.gameplay.agents.policies.scripted import ScriptedPolicy
from apps.gameplay.agents.policies.smart import SmartPolicy


def policy_for_script(script: DeckScript | None = None):
    """Return the policy implementing the script's strategy."""
    script = script or DeckScript()
    if script.strategy == "smart":
        return SmartPolicy(script)
    return ScriptedPolicy(script)


__all__ = [
    "RandomLegalPolicy",
    "ScriptedPolicy",
    "SmartPolicy",
    "policy_for_script",
]

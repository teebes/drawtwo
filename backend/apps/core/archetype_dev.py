"""Development-only Archetype content bootstrap configuration."""

from pathlib import Path

ARCHETYPE_DEV_MANIFEST_PATH = (
    Path(__file__).resolve().parent / "dev_manifests" / "archetype.yaml"
)
ARCHETYPE_DEV_AUTHOR_EMAIL = "author@devdata.local"

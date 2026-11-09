"""Per-council settings (T-86). COUNCIL (environment) picks one; Kāpiti Coast is the default."""
import importlib, os

NAMES = ("kapiti", "porirua", "national")


def load(name=None):
    name = name or os.environ.get("COUNCIL", "kapiti")
    if name not in NAMES: raise SystemExit(f"unknown council {name!r}; known: {', '.join(NAMES)}")
    return importlib.import_module(f"councils.{name}")


COUNCIL = load()

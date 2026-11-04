from types import SimpleNamespace

from timesgate.render import Theme


def ctx(**secrets):
    return SimpleNamespace(theme=Theme(), secrets=secrets)

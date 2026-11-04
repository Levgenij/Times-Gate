import tempfile
from pathlib import Path
from types import SimpleNamespace

from timesgate.render import Theme


def ctx(root=None):
    return SimpleNamespace(theme=Theme(), root=Path(root or tempfile.gettempdir()))

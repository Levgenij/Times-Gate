import tempfile
from pathlib import Path
from types import SimpleNamespace

from timesgate.i18n import WORDS
from timesgate.render import Theme


def ctx(root=None, lang="uk"):
    return SimpleNamespace(theme=Theme(), root=Path(root or tempfile.gettempdir()), words=WORDS[lang])

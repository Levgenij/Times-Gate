import logging

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry


class ConfigError(ValueError):
    """Invalid config.toml."""


def with_retries(session):
    """After the PC sleeps, kept-alive connections are dead and the network may need ~10 s to come back.
    Retries: one on a dropped connection or read timeout (more would block a slot for minutes when an API hangs),
    up to 3 on "can't connect"; pauses 0, 4, 8 s."""
    adapter = HTTPAdapter(max_retries=Retry(total=3, read=1, backoff_factor=2))
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


class Widget:
    """One kind of screen content. Subclasses set `type`, `defaults` and implement `frames()`.

    Every key in `defaults` (plus `every`, `retry`, `align`) is a config.toml option and becomes an attribute.
    """
    type = ""       # name used in config.toml
    defaults = {}   # widget options and their default values
    speed = 100     # ms per frame when frames() returns an animation
    # Settings UI only (English; Ukrainian in i18n.UK): name, one-line description, per-option hints, drop-down values.
    label = ""
    about = ""
    help = {}
    choices = {}
    common_help = {
        "every": "How often to refresh, seconds",
        "retry": "Retry after an error, seconds (empty = same as every)",
        "align": "Refresh exactly on the interval boundary, e.g. at the start of a minute",
    }

    def __init__(self, ctx, **opts):
        allowed = {"every": 60, "retry": None, "align": False, **self.defaults}
        unknown = set(opts) - set(allowed)
        if unknown:
            raise ConfigError(f"{self.type}: unknown option(s) {', '.join(sorted(unknown))}; "
                              f"allowed: {', '.join(sorted(allowed))}")
        for key, value in {**allowed, **opts}.items():
            setattr(self, key, value)
        for key in ("every", "retry"):
            value = getattr(self, key)
            if value is not None and (not isinstance(value, (int, float)) or value <= 0):
                raise ConfigError(f"{self.type}: {key} must be a positive number of seconds")
        self.theme, self.root = ctx.theme, ctx.root  # root: folder of config.toml, for widget files
        self.words = ctx.words  # on-screen words of the configured language (i18n.WORDS)
        self.log = logging.getLogger(f"timesgate.{self.type}")
        self.http = with_retries(requests.Session())  # per widget: each widget runs only in its own slot thread
        self.setup()

    def setup(self):
        """Validate options / prepare state after they are set."""

    def frames(self):
        """List of 128x128 images to show (2+ = animation), or None for "nothing to show now".

        Raising keeps the previously returned frames on screen and retries after `retry` (or `every`) seconds.
        """
        raise NotImplementedError

    def get_json(self, url, **params):
        r = self.http.get(url, params=params, timeout=15)
        r.raise_for_status()
        return r.json()

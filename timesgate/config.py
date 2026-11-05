"""config.toml -> Device + Slots. Widget file paths (e.g. secrets/token_gmail.json) are relative to the config."""
import logging
import os
import shutil
import tomllib
from dataclasses import dataclass, fields
from pathlib import Path
from types import SimpleNamespace

import tomli_w
from PIL import ImageColor, ImageFont

from .device import Device
from .i18n import LANGUAGES, WORDS
from .render import Theme
from .runner import Slot
from .widgets import REGISTRY, ConfigError, GoogleWidget

# Project root, not the current folder: autostart launches with cwd = System32.
DEFAULT_PATH = Path(__file__).resolve().parents[1] / "config.toml"
UI_DEFAULTS = {"enabled": True, "port": 8765, "language": "en"}  # language: on-screen words + settings page


@dataclass
class Config:
    device: Device
    slots: list
    level: str
    ui: dict  # {"enabled": bool, "port": int}


def _section(raw, name, allowed):
    section = raw.get(name, {})
    if not isinstance(section, dict):
        raise ConfigError(f"[{name}] must be a table")
    unknown = set(section) - set(allowed)
    if unknown:
        raise ConfigError(f"[{name}]: unknown key(s) {', '.join(sorted(unknown))}; allowed: {', '.join(sorted(allowed))}")
    return section


def google_widgets(cfg):
    """One Google widget per token file (gmail, calendar, a second calendar with its own token...): one sign-in each."""
    found = {}
    for s in cfg.slots:
        for w in s.widgets:
            if isinstance(w, GoogleWidget):
                found.setdefault(w.token_path, w)
    return list(found.values())


def read(path):
    path = Path(path)
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ConfigError(f"{path} not found (copy config.example.toml to {path.name})") from None
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"{path}: {e}") from None


def load(path):
    return build(read(path), path)


def _drop_none(value):
    """TOML has no null: an option the UI left empty means "use the default"."""
    if isinstance(value, dict):
        return {k: _drop_none(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [_drop_none(v) for v in value]
    return value


def save(path, raw):
    """Validate, then replace config.toml atomically; the previous version is kept as config.toml.bak."""
    path, raw = Path(path), _drop_none(raw)
    build(raw, path)  # raises ConfigError: nothing is written
    tmp = path.with_suffix(".tmp")
    tmp.write_text(tomli_w.dumps(raw), encoding="utf-8")
    if path.exists():
        shutil.copy2(path, path.with_suffix(".toml.bak"))
    os.replace(tmp, path)


def build(raw, path):
    """Validated Config from a parsed config; `path` locates widget files (next to the config)."""
    path = Path(path)
    if not isinstance(raw, dict):
        raise ConfigError("config must be a table")
    unknown = set(raw) - {"device", "theme", "log", "ui", "screen"}
    if unknown:
        raise ConfigError(f"unknown section(s) {', '.join(sorted(unknown))}")

    dev = _section(raw, "device", ["ip", "port", "path", "timeout", "jpeg_quality", "on_exit"])
    if "ip" not in dev:
        raise ConfigError("[device]: ip is required")
    try:
        device = Device(**dev)
    except ValueError as e:
        raise ConfigError(f"[device]: {e}") from None
    theme = Theme(**_section(raw, "theme", [f.name for f in fields(Theme)]))
    for f in fields(Theme):  # a bad colour would otherwise fail every render on every screen
        if f.name != "cyrillic_font":
            try:
                ImageColor.getrgb(getattr(theme, f.name))
            except (ValueError, TypeError) as e:  # TypeError: not a string, e.g. muted = 123
                raise ConfigError(f"[theme]: {f.name}: {e}") from None
    try:  # fail at start, not as a blank clock: Segoe UI exists only on Windows
        ImageFont.truetype(theme.cyrillic_font, 10)
    except OSError:
        raise ConfigError(f"[theme]: cyrillic_font {theme.cyrillic_font!r} not found; "
                          "set it to a .ttf with Cyrillic, e.g. DejaVuSans.ttf") from None
    level = str(_section(raw, "log", ["level"]).get("level", "INFO")).upper()
    if not isinstance(logging.getLevelName(level), int):
        raise ConfigError(f"[log]: unknown level {level}")
    ui = {**UI_DEFAULTS, **_section(raw, "ui", list(UI_DEFAULTS))}
    if not isinstance(ui["port"], int) or not 1024 <= ui["port"] <= 65535:
        raise ConfigError("[ui]: port must be 1024-65535")
    if ui["language"] not in LANGUAGES:
        raise ConfigError(f"[ui]: language must be one of {', '.join(LANGUAGES)}")

    ctx = SimpleNamespace(theme=theme, root=path.resolve().parent, words=WORDS[ui["language"]])
    slots, seen = [], set()
    screens = raw.get("screen", [])
    if not isinstance(screens, list):
        raise ConfigError("use [[screen]] (double brackets) for each screen")
    for screen in screens:
        if not isinstance(screen, dict):
            raise ConfigError("each [[screen]] must be a table")
        number = screen.get("slot")
        if number not in range(1, 6):
            raise ConfigError(f"[[screen]]: slot must be 1-5, got {number!r}")
        if number in seen:
            raise ConfigError(f"[[screen]]: slot {number} is defined twice")
        seen.add(number)
        if set(screen) - {"slot", "widgets"}:
            raise ConfigError(f"slot {number}: only 'slot' and 'widgets' are allowed")
        specs = screen.get("widgets")
        if not isinstance(specs, list) or not specs:
            raise ConfigError(f"slot {number}: widgets must be a non-empty list")
        widgets = []
        for spec in specs:
            if not isinstance(spec, dict):
                raise ConfigError(f"slot {number}: each widget must be a table like {{ type = \"clock\" }}")
            spec = dict(spec)
            kind = spec.pop("type", None)
            if kind not in REGISTRY:
                raise ConfigError(f"slot {number}: unknown widget type {kind!r}; known: {', '.join(REGISTRY)}")
            widgets.append(REGISTRY[kind](ctx, **spec))
        slots.append(Slot(number, widgets))
    if not slots:
        raise ConfigError("no [[screen]] defined")
    return Config(device, slots, level, ui)

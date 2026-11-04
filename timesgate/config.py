"""config.toml -> Device + Slots. Widget files (e.g. the Gmail token) live next to the config."""
import logging
import tomllib
from dataclasses import dataclass, fields
from pathlib import Path
from types import SimpleNamespace

from PIL import ImageColor, ImageFont

from .device import Device
from .render import Theme
from .runner import Slot
from .widgets import REGISTRY, ConfigError


@dataclass
class Config:
    device: Device
    slots: list
    level: str


def _section(raw, name, allowed):
    section = raw.get(name, {})
    if not isinstance(section, dict):
        raise ConfigError(f"[{name}] must be a table")
    unknown = set(section) - set(allowed)
    if unknown:
        raise ConfigError(f"[{name}]: unknown key(s) {', '.join(sorted(unknown))}; allowed: {', '.join(sorted(allowed))}")
    return section


def load(path):
    path = Path(path)
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ConfigError(f"{path} not found (copy config.example.toml to {path.name})") from None
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"{path}: {e}") from None
    unknown = set(raw) - {"device", "theme", "log", "screen"}
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

    ctx = SimpleNamespace(theme=theme, root=path.resolve().parent)
    slots, seen = [], set()
    screens = raw.get("screen", [])
    if not isinstance(screens, list):
        raise ConfigError("use [[screen]] (double brackets) for each screen")
    for screen in screens:
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
    return Config(device, slots, level)

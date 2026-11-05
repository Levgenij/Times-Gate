"""Settings UI: one local page (timesgate/ui) and a JSON API over the running Runner. Listens on 127.0.0.1 only."""
import base64
import collections
import dataclasses
import inspect
import io
import json
import logging
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import config, i18n
from .device import Device
from .render import Theme
from .widgets import REGISTRY, ConfigError, Widget

log = logging.getLogger("timesgate.web")
UI = Path(__file__).with_name("ui")
STATIC = {"/": ("index.html", "text/html; charset=utf-8"),
          "/vue.js": ("vue.esm-browser.prod.js", "text/javascript; charset=utf-8")}
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
LAUNCHER = config.DEFAULT_PATH.with_name("timesgate.pyw")


class LogBuffer(logging.Handler):
    """The last log lines for the UI; the console or timesgate.log still gets everything."""

    def __init__(self, size=300):
        super().__init__()
        self.lines = collections.deque(maxlen=size)

    def emit(self, record):
        self.lines.append(self.format(record))


LOG = LogBuffer()


def png(img):
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def _kind(default, choices):
    if choices:
        return "choice"
    if isinstance(default, bool):
        return "bool"
    if default is None or isinstance(default, (int, float)):  # None: retry, "same as every"
        return "number"
    return "list" if isinstance(default, list) else "text"


def schema():
    """Everything the UI needs to draw forms: built from the widgets' own defaults, so new widgets just appear."""
    widgets = {}
    for name, cls in REGISTRY.items():
        hints = {**Widget.common_help, **cls.help}
        widgets[name] = {"label": cls.label or name, "about": cls.about, "options": [
            {"name": k, "default": v, "kind": _kind(v, cls.choices.get(k)), "choices": cls.choices.get(k),
             "help": hints.get(k, "")}
            for k, v in {"every": 60, "retry": None, "align": False, **cls.defaults}.items()]}
    device = {k: p.default for k, p in inspect.signature(Device).parameters.items() if k not in ("ip", "on_exit")}
    return {"widgets": widgets, "theme": dataclasses.asdict(Theme()), "device": device,
            "levels": ["DEBUG", "INFO", "WARNING", "ERROR"], "ui": config.UI_DEFAULTS,
            "languages": list(i18n.LANGUAGES), "uk": i18n.UK}  # the page translates its English texts itself


def autostart_command(path):
    pythonw = Path(sys.executable).with_name("pythonw.exe")  # no console window
    return f'"{pythonw}" "{LAUNCHER}" -c "{Path(path).resolve()}"'


def autostart(path, enable=None):
    """Read (enable=None) or switch the HKCU Run entry. True only if it starts this copy; None off Windows."""
    if sys.platform != "win32":
        return None
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ | winreg.KEY_SET_VALUE) as key:
        if enable:
            winreg.SetValueEx(key, "timesgate", 0, winreg.REG_SZ, autostart_command(path))
        elif enable is False:
            try:
                winreg.DeleteValue(key, "timesgate")
            except FileNotFoundError:
                pass
        try:
            return winreg.QueryValueEx(key, "timesgate")[0] == autostart_command(path)
        except FileNotFoundError:
            return False


def _errors(slot):
    return {w.type: e for w, e in zip(slot.widgets, slot.errors) if e}


def _google(cfg):
    """Sign-in state per Google token file, for the "Система" (System) tab."""
    # type(w).label: the instance attribute may be an option of the same name (gmail's `label` = "INBOX")
    return {w.token: {"label": type(w).label, "authorized": w.token_path.exists(), "active": w.session is not None}
            for w in config.google_widgets(cfg)}


def make_server(runner, path, port):
    """Bound but not yet serving; OSError if the port is taken (another copy is running)."""
    path = Path(path)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):  # the default writes to stderr, which is None under pythonw
            log.debug(fmt, *args)

        def reply(self, code, body, ctype="application/json"):
            if not isinstance(body, bytes):
                body = json.dumps(body, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def allowed(self):
            # Host: blocks DNS rebinding. JSON-only writes: another site's page cannot send them without a CORS
            # preflight, which this server never answers.
            host = self.headers.get("Host", "").rsplit(":", 1)[0]
            return host in ("127.0.0.1", "localhost") and (
                self.command == "GET" or self.headers.get_content_type() == "application/json")

        def body(self):
            try:
                return json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"null")
            except ValueError as e:  # also UnicodeDecodeError
                raise ConfigError(f"bad JSON: {e}") from None

        def do_GET(self):
            self.route()

        do_PUT = do_POST = do_GET

        def route(self):
            if not self.allowed():
                return self.reply(403, {"error": "forbidden"})
            url = self.path.split("?")[0]
            try:
                if self.command == "GET" and url in STATIC:
                    name, ctype = STATIC[url]
                    return self.reply(200, (UI / name).read_bytes(), ctype)
                # /api/<name>[/...] -> method <verb>_<name>, e.g. GET /api/screen/3.png -> get_screen
                name = url.removeprefix("/api/").split("/")[0].replace("-", "_")
                handler = getattr(self, f"{self.command.lower()}_{name}", None)
                if not url.startswith("/api/") or handler is None:
                    return self.reply(404, {"error": "not found"})
                handler(url)
            except ConfigError as e:
                self.reply(400, {"error": str(e)})
            except Exception as e:
                log.exception("%s %s", self.command, url)
                self.reply(500, {"error": f"{type(e).__name__}: {e}"})

        # --- API ---

        def get_config(self, url):
            self.reply(200, {"config": config.read(path), "schema": schema(), "path": str(path)})

        def put_config(self, url):
            config.save(path, self.body())
            runner.reload(config.load(path))
            self.reply(200, {"ok": True})

        def post_preview(self, url):
            """Draw one slot of an unsaved config; nothing is sent to the device."""
            req = self.body()
            cfg = config.build(req["config"], path)
            slot = next((s for s in cfg.slots if s.number == req["slot"]), None)
            if slot is None:
                return self.reply(200, {"widget": None, "frames": [], "errors": {}})
            widget, frames = slot.tick(time.time())
            self.reply(200, {"widget": widget and widget.type, "speed": widget and widget.speed,
                             "frames": [base64.b64encode(png(f)).decode() for f in frames or []],
                             "errors": _errors(slot)})

        def get_status(self, url):
            cfg = runner.cfg
            self.reply(200, {
                "device": {"online": cfg.device.down_until == 0, "url": cfg.device.url},
                "slots": [{"slot": s.number, "widget": s.sent and s.sent[0], "sent_at": s.sent and s.sent[2],
                           "errors": _errors(s)} for s in cfg.slots],
                "google": _google(cfg)})

        def get_screen(self, url):  # /api/screen/3.png: what the device shows on slot 3
            n = int(url.rsplit("/", 1)[-1].split(".")[0])
            slot = next((s for s in runner.cfg.slots if s.number == n and s.sent), None)
            if slot is None:
                return self.reply(404, {"error": "nothing sent yet"})
            self.reply(200, png(slot.sent[1][0]), "image/png")

        def get_autostart(self, url):
            self.reply(200, {"enabled": autostart(path), "command": autostart_command(path)})

        def put_autostart(self, url):
            self.reply(200, {"enabled": autostart(path, bool(self.body()["enabled"]))})

        def get_log(self, url):
            self.reply(200, {"lines": list(LOG.lines)})

        def post_google_auth(self, url):  # body {"token": "secrets/token_calendar.json"}
            token = (self.body() or {}).get("token")
            widget = next((w for w in config.google_widgets(runner.cfg) if w.token == token), None)
            if widget is None:
                raise ConfigError(f"no Google widget with token {token!r} in the config")

            def login():  # blocks until the browser consent finishes
                try:
                    log.info("%s: saved %s", widget.type, widget.authorize())
                    runner.reload(config.load(path))
                except Exception as e:
                    log.warning("%s sign-in failed: %s", widget.type, e)

            threading.Thread(target=login, name="google-auth", daemon=True).start()
            self.reply(202, {"started": True})

    return Server(("127.0.0.1", port), Handler)


class Server(ThreadingHTTPServer):
    allow_reuse_address = sys.platform != "win32"  # on Windows SO_REUSEADDR would let a 2nd copy share the port
    daemon_threads = True

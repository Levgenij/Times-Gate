"""python -m timesgate [-c config.toml] [--once | --preview DIR | --google-auth]"""
import argparse
import logging
import sys
import threading
import time
import urllib.request
import webbrowser
from logging.handlers import RotatingFileHandler
from pathlib import Path

from . import runner, tray, web
from .config import DEFAULT_PATH, google_widgets, load
from .widgets import ConfigError


def fail(msg):
    logging.critical(msg)  # sys.exit(msg) alone would be lost without a console
    if sys.stderr is None and sys.platform == "win32":
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, msg, "Times Gate", 0x10)  # MB_ICONERROR
    sys.exit(1)


def main(argv=None):
    p = argparse.ArgumentParser(prog="timesgate", description="Divoom Times Gate screens")
    p.add_argument("-c", "--config", type=Path, default=DEFAULT_PATH,
                   help="config file (default: config.toml in the project folder)")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--once", action="store_true", help="draw and send every slot once, then exit")
    mode.add_argument("--preview", metavar="DIR", help="save every slot as PNG into DIR, send nothing")
    mode.add_argument("--google-auth", action="store_true",
                      help="one-time Google login in the browser for each gmail / calendar widget")
    args = p.parse_args(argv)
    # configure before load(): widgets may log while being built; the level comes from the config
    handlers = [web.LOG]  # last lines for the settings page
    if sys.stderr is None:  # pythonw (timesgate.pyw, autostart) has no console: log next to the config instead
        handlers.append(RotatingFileHandler(args.config.resolve().with_name("timesgate.log"),
                                            maxBytes=1_000_000, backupCount=1, encoding="utf-8"))
    else:
        handlers.append(logging.StreamHandler())
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s",
                        datefmt="%d.%m %H:%M:%S", handlers=handlers)
    logging.getLogger("urllib3").setLevel(logging.WARNING)  # per-request lines drown DEBUG output
    try:
        cfg = load(args.config)
    except ConfigError as e:
        fail(f"config error: {e}")
    logging.getLogger().setLevel(cfg.level)

    if args.google_auth:
        widgets = google_widgets(cfg)
        if not widgets:
            sys.exit("no Google widget (gmail, calendar) in the config")
        for w in widgets:  # one browser consent per widget: each token has only its own scope
            print(f"{w.type} ({w.token}): sign in in the browser…")
            try:
                print(f"saved {w.authorize()}")
            except ConfigError as e:
                sys.exit(f"config error: {e}")
        print("restart timesgate (or tray -> Оновити екрани) to use it")
    elif args.preview:
        out = Path(args.preview)
        out.mkdir(parents=True, exist_ok=True)
        for slot in cfg.slots:
            widget, frames = slot.tick(time.time())
            for k, img in enumerate(frames or []):
                name = out / (f"slot{slot.number}.png" if len(frames) == 1 else f"slot{slot.number}-{k + 1}.png")
                img.save(name)
                print(f"{name}  ({widget.type})")
            if not frames:
                print(f"slot {slot.number}: nothing to show")
    elif args.once:
        for slot in cfg.slots:
            slot.step(cfg.device)
    else:
        serve(cfg, args.config)


def already_running(url):
    try:
        with urllib.request.urlopen(url + "api/status", timeout=3) as resp:
            return resp.status == 200
    except (OSError, ValueError):
        return False


def serve(cfg, path):
    r, icon = runner.Runner(), None
    if cfg.ui["enabled"]:
        url = f"http://127.0.0.1:{cfg.ui['port']}/"
        try:
            server = web.make_server(r, path, cfg.ui["port"])
        except OSError as e:
            if not already_running(url):  # the port belongs to some other program
                fail(f"settings port {cfg.ui['port']} is not available ({e}); set another [ui] port in {path}")
            logging.info("already running, opening %s", url)
            webbrowser.open(url)
            return
        r.start(cfg)
        threading.Thread(target=server.serve_forever, name="web", daemon=True).start()
        logging.info("settings: %s", url)
        icon = tray.start(url, r, lambda: load(path))
    else:
        r.start(cfg)
    try:
        runner.run(r)
    finally:
        if icon:  # after Ctrl+C too, or Windows keeps a dead icon until hovered
            icon.stop()


if __name__ == "__main__":
    main()

"""python -m timesgate [-c config.toml] [--once] [--preview DIR]"""
import argparse
import logging
import sys
import time
from pathlib import Path

from . import runner
from .config import load
from .widgets import ConfigError


def main(argv=None):
    p = argparse.ArgumentParser(prog="timesgate", description="Divoom Times Gate screens")
    p.add_argument("-c", "--config", default="config.toml", help="config file (default: config.toml)")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--once", action="store_true", help="draw and send every slot once, then exit")
    mode.add_argument("--preview", metavar="DIR", help="save every slot as PNG into DIR, send nothing")
    args = p.parse_args(argv)
    # configure before load(): widgets may log while being built; the level comes from the config
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s",
                        datefmt="%H:%M:%S")
    logging.getLogger("urllib3").setLevel(logging.WARNING)  # per-request lines drown DEBUG output
    try:
        cfg = load(args.config)
    except ConfigError as e:
        sys.exit(f"config error: {e}")
    logging.getLogger().setLevel(cfg.level)

    if args.preview:
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
        runner.run(cfg.slots, cfg.device)


if __name__ == "__main__":
    main()

"""Slot scheduling: each slot runs its widgets on their intervals and shows the first one that has frames."""
import hashlib
import logging
import signal
import sys
import threading
import time

from .device import DeviceDown, DeviceError

log = logging.getLogger("timesgate.runner")


def digest(frames, speed):
    h = hashlib.blake2b(str(speed).encode(), digest_size=16)
    for img in frames:
        h.update(img.tobytes())
    return h.digest()


def next_time(now, delay, align):
    return now - now % delay + delay if align else now + delay


class Slot:
    def __init__(self, number, widgets):
        self.number, self.widgets = number, widgets
        self.results = [None] * len(widgets)  # last frames each widget returned
        self.errors = [None] * len(widgets)   # last failure of each widget, for the UI
        self.due = [0.0] * len(widgets)
        self.shown = None  # digest of what the device shows on this slot
        self.sent = None   # (widget type, frames, time) last sent, for the UI

    def tick(self, now):
        """Run due widgets; return (widget, frames) of the highest-priority widget with frames, or (None, None)."""
        for i, w in enumerate(self.widgets):
            if now < self.due[i]:
                continue
            try:
                self.results[i], self.errors[i] = w.frames(), None
                delay = w.every
            # Long-running display: an API change or outage in one widget must not kill the slot.
            except Exception as e:
                log.warning("slot %d %s: %s (keeping last frames)", self.number, w.type, e)
                self.errors[i] = str(e) or type(e).__name__
                delay = w.retry or w.every
            self.due[i] = next_time(now, delay, w.align)
        return next(((w, r) for w, r in zip(self.widgets, self.results) if r), (None, None))

    def step(self, device, now=None):
        """One scheduling round; sends only if the picture changed. Returns when to run again."""
        now = time.time() if now is None else now
        widget, frames = self.tick(now)
        wake = min(self.due)
        if frames:
            key = digest(frames, widget.speed)
            if key != self.shown:
                try:
                    device.send(self.number, frames, widget.speed)
                    self.shown, self.sent = key, (widget.type, frames, now)
                    log.debug("slot %d: sent %s (%d frame(s))", self.number, widget.type, len(frames))
                except DeviceDown:  # logged once by Device
                    wake = min(wake, device.down_until)
                except DeviceError as e:
                    log.warning("slot %d %s: %s", self.number, widget.type, e)
                    wake = min(wake, now + device.RETRY)
        return wake

    def run(self, device, stop):
        while not stop.is_set():
            try:
                wake = self.step(device)
            except Exception:  # a bug here must not silently freeze one screen
                log.exception("slot %d crashed, restarting in 30 s", self.number)
                wake = time.time() + 30
            stop.wait(max(0.0, wake - time.time()))


_console_handler = None  # must stay referenced, or ctypes frees the callback


def on_console_close(callback):
    """Windows: call `callback` when the console window is closed; Windows waits ~5 s, then kills the process.

    Logoff / shutdown events never arrive: Windows skips them for processes that load user32/gdi32 (Pillow does).
    Ctrl+C is not handled here (it raises KeyboardInterrupt).
    """
    global _console_handler
    if sys.platform != "win32":
        return
    import ctypes

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_uint)
    def handler(event):
        if event == 2:  # CTRL_CLOSE_EVENT
            callback()
        return False  # continue with the default handling

    _console_handler = handler
    ctypes.windll.kernel32.SetConsoleCtrlHandler(handler, True)


class Runner:
    """Runs one Config's slots in threads; reload() swaps in a new Config without restarting the program."""

    def __init__(self):
        self.cfg = None
        self.done = threading.Event()  # set by stop(): the program should exit
        self._stop = None              # stop event of the current slot threads
        self._lock = threading.Lock()  # reload from the UI vs. the tray vs. stop

    def start(self, cfg):
        with self._lock:
            if self.done.is_set():
                return
            if self.cfg:  # the old Device stops sending before the new one starts; no on_exit in between
                self._stop.set()
                self.cfg.device.halt()
                # PicID must keep growing across Device objects, or the device drops the next uploads
                cfg.device._last_id = max(cfg.device._last_id, self.cfg.device._last_id)
            self.cfg, self._stop = cfg, threading.Event()
            logging.getLogger().setLevel(cfg.level)
            for s in cfg.slots:
                threading.Thread(target=s.run, args=(cfg.device, self._stop), name=f"slot{s.number}",
                                 daemon=True).start()
        log.info("running slots %s on %s", ", ".join(str(s.number) for s in cfg.slots), cfg.device.url)

    reload = start

    def stop(self):
        """Stop for good and send on_exit; safe to call more than once and from any thread."""
        with self._lock:
            self.done.set()
            if self.cfg:
                self._stop.set()
                self.cfg.device.close()


def run(runner):
    """Block until Ctrl+C, console close, SIGTERM or runner.stop() (tray "Exit")."""
    on_console_close(runner.stop)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))  # e.g. systemd stop on a Pi -> finally below
    try:
        while not runner.done.wait(1):  # short waits keep Ctrl+C responsive on Windows
            pass
    except KeyboardInterrupt:
        log.info("stopping")
    finally:
        runner.stop()

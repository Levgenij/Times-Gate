"""Slot scheduling: each slot runs its widgets on their intervals and shows the first one that has frames."""
import hashlib
import logging
import signal
import sys
import threading
import time

from .device import DeviceDown, DeviceError

log = logging.getLogger("timesgate.runner")
WAIT_STEP = 10  # seconds: how soon the screens catch up after the PC wakes from sleep


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
            # Short waits checked against the wall clock: Windows timers stop while the PC sleeps, so one long
            # wait would leave the screen stale after wake-up for up to `every` (15 min for the weather).
            # `due` too: Runner.resume() resets it to redraw now.
            while not stop.is_set() and time.time() < min(wake, *self.due):
                stop.wait(min(wake - time.time(), WAIT_STEP))


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

    def suspend(self):
        """The PC goes to sleep: hand the screens to the device (on_exit) and stop sending."""
        with self._lock:
            if self.cfg and not self.done.is_set():
                log.info("PC is going to sleep")
                self.cfg.device.pause()

    def resume(self):
        """The PC woke up: the device shows on_exit, so redraw every screen, even an unchanged one."""
        with self._lock:
            if self.cfg and not self.done.is_set():
                for s in self.cfg.slots:
                    s.shown, s.due = None, [0.0] * len(s.widgets)
                self.cfg.device.down_until = 0

    def stop(self):
        """Stop for good and send on_exit; safe to call more than once and from any thread."""
        with self._lock:
            self.done.set()
            if self.cfg:
                self._stop.set()
                self.cfg.device.close()


_power_params = None  # must stay referenced, like _console_handler


def on_sleep(suspend, resume):
    """Windows: call `suspend` when the PC goes to sleep (Windows waits ~2 s for it) and `resume` after wake-up.

    A callback registration, so it works without a window or console (pythonw).
    """
    global _power_params
    if sys.platform != "win32":
        return
    import ctypes
    from ctypes import wintypes

    @ctypes.WINFUNCTYPE(wintypes.ULONG, ctypes.c_void_p, wintypes.ULONG, ctypes.c_void_p)
    def callback(context, event, setting):
        try:
            if event == 4:  # PBT_APMSUSPEND
                suspend()
            elif event == 0x12:  # PBT_APMRESUMEAUTOMATIC: every wake-up, also with nobody at the PC
                resume()
        except Exception:  # an exception must not cross into Windows
            log.exception("sleep/wake handler failed")
        return 0

    class Params(ctypes.Structure):  # DEVICE_NOTIFY_SUBSCRIBE_PARAMETERS
        _fields_ = [("callback", type(callback)), ("context", ctypes.c_void_p)]

    _power_params = Params(callback, None)
    handle = ctypes.c_void_p()
    err = ctypes.windll.powrprof.PowerRegisterSuspendResumeNotification(  # 2 = DEVICE_NOTIFY_CALLBACK
        2, ctypes.byref(_power_params), ctypes.byref(handle))
    if err:
        log.warning("no sleep/wake notifications (error %d): on_exit is not sent on sleep", err)


def run(runner):
    """Block until Ctrl+C, console close, SIGTERM or runner.stop() (tray "Exit")."""
    on_console_close(runner.stop)
    on_sleep(runner.suspend, runner.resume)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))  # e.g. systemd stop on a Pi -> finally below
    try:
        while not runner.done.wait(1):  # short waits keep Ctrl+C responsive on Windows
            pass
    except KeyboardInterrupt:
        log.info("stopping")
    finally:
        runner.stop()

"""Tray icon: open settings, redraw the screens, exit (sends on_exit)."""
import logging
import threading
import webbrowser

from PIL import Image, ImageDraw

from .widgets import ConfigError

log = logging.getLogger("timesgate.tray")


def icon_image():
    """Five panels in a row, like the device."""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 18, 63, 46], radius=6, fill="#1f2329")
    for i in range(5):
        x = 4 + i * 12
        d.rounded_rectangle([x, 23, x + 8, 41], radius=2, fill="#e8b04b" if i == 2 else "#8a9099")
    return img


def start(url, runner, load):
    """Show the icon in its own thread and return it; None where there is no tray (e.g. a Pi without a desktop)."""
    try:
        import pystray

        def redraw():  # re-reads config.toml and resends every screen, e.g. after the device's mode button
            try:
                runner.reload(load())
            except ConfigError as e:
                log.error("config error: %s", e)

        icon = pystray.Icon("timesgate", icon_image(), "Times Gate", pystray.Menu(
            pystray.MenuItem("Налаштування", lambda: webbrowser.open(url), default=True),
            pystray.MenuItem("Оновити екрани", redraw),
            pystray.MenuItem("Вихід", runner.stop)))  # __main__ then removes the icon
    except Exception as e:  # no display / backend: run without a tray
        log.info("no tray icon: %s", e)
        return None
    threading.Thread(target=icon.run, name="tray", daemon=True).start()
    return icon

import time

from ..render import SIZE, canvas, font
from .base import ConfigError, Widget


class Clock(Widget):
    """24-hour HH:MM with an optional blinking colon and the date with a weekday in the configured language."""
    type = "clock"
    defaults = {
        "every": 60, "align": True,  # redraw on each minute boundary
        "blink": True, "date": True, "date_format": "%d.%m",
        "weekdays": [],  # empty = the configured language's names (i18n.WORDS)
        "time_size": 42, "date_size": 14,
    }
    label, about = "Clock", "24-hour time and the date with the weekday"
    help = {"blink": "The colon blinks (a 2-frame animation the device loops by itself)",
            "date": "Show the date below the time", "date_format": "strftime format, e.g. %d.%m",
            "weekdays": "7 names starting with Monday (empty = the language's own)",
            "time_size": "Size of the time digits, px", "date_size": "Size of the date, px"}

    def setup(self):
        self.weekdays = self.weekdays or self.words["weekdays"]
        if len(self.weekdays) != 7:
            raise ConfigError("clock: weekdays needs 7 names, Monday first")
        # Blink = a 2-frame loop the device plays itself, sent once a minute (colon on 0.5 s, off 0.5 s).
        # Sending a frame every second instead still showed the device's "loading" icon at times.
        self.speed = 500 if self.blink else 100

    def render(self, now, colon=True):
        img, d = canvas(self.theme)
        f = font(self.time_size)
        # digits sit around a fixed colon slot so they don't move when the colon is hidden
        c, y, gap = SIZE // 2, 56 if self.date else SIZE // 2, f.getlength(":") / 2
        d.text((c - gap, y), time.strftime("%H", now), fill=self.theme.text, font=f, anchor="rm")
        d.text((c + gap, y), time.strftime("%M", now), fill=self.theme.text, font=f, anchor="lm")
        if colon:
            d.text((c, y), ":", fill=self.theme.text, font=f, anchor="mm")
        if self.date:
            d.text((c, 92), f"{self.weekdays[now.tm_wday]} {time.strftime(self.date_format, now)}",
                   fill=self.theme.muted, font=font(self.date_size, self.theme.cyrillic_font), anchor="mm")
        return img

    def frames(self):
        now = time.localtime()
        return [self.render(now), self.render(now, colon=False)] if self.blink else [self.render(now)]

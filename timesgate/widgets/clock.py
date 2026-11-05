import time

from ..render import SIZE, canvas, font
from .base import ConfigError, Widget


class Clock(Widget):
    """24-hour HH:MM with an optional blinking colon and date with a Ukrainian weekday."""
    type = "clock"
    defaults = {
        "every": 60, "align": True,  # redraw on each minute boundary
        "blink": True, "date": True, "date_format": "%d.%m",
        "weekdays": ["Пон", "Вів", "Сер", "Чет", "П’ят", "Суб", "Нед"],  # Monday first
        "time_size": 42, "date_size": 14,
    }
    label, about = "Годинник", "24-годинний час і дата з днем тижня"
    help = {"blink": "Двокрапка блимає (анімація з 2 кадрів, яку крутить сам пристрій)",
            "date": "Показувати дату під часом", "date_format": "Формат strftime, напр. %d.%m",
            "weekdays": "7 назв, починаючи з понеділка", "time_size": "Розмір цифр часу, px",
            "date_size": "Розмір дати, px"}

    def setup(self):
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

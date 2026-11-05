from datetime import date
from typing import NamedTuple

from ..render import SIZE, WEEKDAYS, canvas, font
from . import icons
from .base import Widget

URL = "https://api.open-meteo.com/v1/forecast"  # free, no API key
# WMO weather codes -> (short label, icon kind); labels in English: the default font has no Cyrillic
WMO = [((0,), "Clear", "clear"), ((1,), "Mostly clear", "mostly_clear"), ((2,), "Partly cloudy", "partly"),
       ((3,), "Overcast", "overcast"), ((45, 48), "Fog", "fog"), (range(51, 58), "Drizzle", "drizzle"),
       (range(61, 68), "Rain", "rain"), (range(71, 78), "Snow", "snow"), (range(80, 83), "Showers", "showers"),
       ((85, 86), "Snow showers", "snow"), (range(95, 100), "Thunderstorm", "thunder")]


def lookup(code):
    """(label, icon kind) for a WMO code; unknown code -> no label, overcast icon."""
    return next(((label, kind) for codes, label, kind in WMO if code in codes), ("", "overcast"))


def deg(t):
    return f"{round(t)}°"  # round() gives 0, not "-0", for -0.3


class Layout(NamedTuple):
    place: int       # y of the place name
    icon: tuple      # (size, x, y) of the sky icon
    temp: tuple      # (x, y, size, size for "-12°") next to the icon
    alone: tuple     # (y, size) of the temperature when icon = false
    label: tuple     # (y, size) of the sky label
    hilo: tuple      # (y, size) of today's max / min


FULL = Layout(11, (52, 6, 22), (92, 49, 34, 28), (50, 44), (92, 15), (114, 12))
COMPACT = Layout(8, (44, 6, 15), (90, 37, 32, 26), (38, 38), (67, 13), (81, 11))  # leaves room for the forecast


class Weather(Widget):
    """Icon, current temperature, sky and today's max / min from Open-Meteo, plus the next 2 days."""
    type = "weather"
    # Open-Meteo refreshes "current" every 15 min
    defaults = {"every": 900, "place": "LONDON", "lat": 51.5074, "lon": -0.1278, "timezone": "Europe/London",
                "icon": True, "forecast": True}
    label, about = "Погода", "Температура, небо, денні макс./мін. і прогноз на 2 дні з Open-Meteo"
    help = {"place": "Назва над температурою (латиницею: стандартний шрифт без кирилиці)",
            "lat": "Широта", "lon": "Довгота", "timezone": "Часовий пояс, напр. Europe/London",
            "icon": "Іконка неба біля температури", "forecast": "Унизу завтра й післязавтра: іконка, макс./мін."}

    def fetch(self):
        data = self.get_json(URL, latitude=self.lat, longitude=self.lon, timezone=self.timezone,
                             forecast_days=3 if self.forecast else 1,
                             current="temperature_2m,weather_code,is_day",
                             daily="weather_code,temperature_2m_max,temperature_2m_min")
        cur, day = data["current"], data["daily"]
        days = [(date.fromisoformat(day["time"][i]).weekday(), day["weather_code"][i],
                 day["temperature_2m_max"][i], day["temperature_2m_min"][i])
                for i in range(1, len(day["time"]))] if self.forecast else []
        return (cur["temperature_2m"], cur["weather_code"], bool(cur.get("is_day", 1)),
                day["temperature_2m_max"][0], day["temperature_2m_min"][0], days[:2])

    def render(self, temp, code, is_day, hi, lo, days=()):
        """`days`: [(weekday 0=Monday, WMO code, max, min), ...] for tomorrow and the day after."""
        t = self.theme
        img, d = canvas(t)
        label, kind = lookup(code)
        lay = COMPACT if days else FULL
        d.text((SIZE // 2, lay.place), self.place, fill=t.muted, font=font(12 if lay is FULL else 11), anchor="mm")
        if self.icon:
            size, x, y = lay.icon
            ico = icons.draw(kind, is_day, size)
            img.paste(ico, (x, y), ico)
            text = deg(temp)
            tx, ty, big, small = lay.temp
            # "-12°" next to the icon needs a smaller size to keep a margin to the edge
            d.text((tx, ty), text, fill=t.text, font=font(big if len(text) <= 3 else small), anchor="mm")
        else:
            d.text((SIZE // 2, lay.alone[0]), deg(temp), fill=t.text, font=font(lay.alone[1]), anchor="mm")
        d.text((SIZE // 2, lay.label[0]), label, fill=t.text, font=font(lay.label[1]), anchor="mm")
        d.text((SIZE // 2, lay.hilo[0]), f"{deg(hi)} / {deg(lo)}", fill=t.muted, font=font(lay.hilo[1]), anchor="mm")
        if days:
            d.line([(10, 91), (SIZE - 10, 91)], fill=t.dim)
            for (weekday, fcode, fhi, flo), cx in zip(days, (SIZE // 4, SIZE * 3 // 4)):
                d.text((cx, 100), WEEKDAYS[weekday], fill=t.muted, font=font(11, t.cyrillic_font), anchor="mm")
                text = f"{round(fhi)}/{round(flo)}°"
                f = font(11) if font(11).getlength(text) <= 32 else font(9)  # "-12/-15°" must stay in its half
                x = round(cx - (20 + 3 + f.getlength(text)) / 2)  # icon + gap + text, centred in the half
                ico = icons.draw(lookup(fcode)[1], True, 20)
                img.paste(ico, (x, 107), ico)
                d.text((x + 23, 117), text, fill=t.text, font=f, anchor="lm")
        return img

    def frames(self):
        return [self.render(*self.fetch())]

from ..render import SIZE, canvas, font
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


class Weather(Widget):
    """Icon, current temperature, sky and today's max / min from Open-Meteo."""
    type = "weather"
    # Open-Meteo refreshes "current" every 15 min
    defaults = {"every": 900, "place": "LONDON", "lat": 51.5074, "lon": -0.1278, "timezone": "Europe/London",
                "icon": True}

    def fetch(self):
        data = self.get_json(URL, latitude=self.lat, longitude=self.lon, timezone=self.timezone, forecast_days=1,
                             current="temperature_2m,weather_code,is_day",
                             daily="temperature_2m_max,temperature_2m_min")
        cur, day = data["current"], data["daily"]
        return (cur["temperature_2m"], cur["weather_code"], bool(cur.get("is_day", 1)),
                day["temperature_2m_max"][0], day["temperature_2m_min"][0])

    def render(self, temp, code, is_day, hi, lo):
        t = self.theme
        img, d = canvas(t)
        label, kind = lookup(code)
        d.text((SIZE // 2, 11), self.place, fill=t.muted, font=font(12), anchor="mm")
        if self.icon:
            ico = icons.draw(kind, is_day, 52)
            img.paste(ico, (6, 22), ico)
            text = deg(temp)
            # "-12°" next to the icon needs a smaller size to keep a margin to the edge
            d.text((92, 49), text, fill=t.text, font=font(34 if len(text) <= 3 else 28), anchor="mm")
        else:
            d.text((SIZE // 2, 50), deg(temp), fill=t.text, font=font(44), anchor="mm")
        d.text((SIZE // 2, 92), label, fill=t.text, font=font(15), anchor="mm")
        d.text((SIZE // 2, 114), f"{deg(hi)} / {deg(lo)}", fill=t.muted, font=font(12), anchor="mm")
        return img

    def frames(self):
        return [self.render(*self.fetch())]

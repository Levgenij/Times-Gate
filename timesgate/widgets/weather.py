from ..render import SIZE, canvas, font
from .base import Widget

URL = "https://api.open-meteo.com/v1/forecast"  # free, no API key
# WMO weather codes -> short label (default font has no Cyrillic)
WMO = [((0,), "Clear"), ((1,), "Mostly clear"), ((2,), "Partly cloudy"), ((3,), "Overcast"),
       ((45, 48), "Fog"), (range(51, 58), "Drizzle"), (range(61, 68), "Rain"), (range(71, 78), "Snow"),
       (range(80, 83), "Showers"), ((85, 86), "Snow showers"), (range(95, 100), "Thunderstorm")]


def describe(code):
    return next((label for codes, label in WMO if code in codes), "")


class Weather(Widget):
    """Current temperature, sky and today's max / min from Open-Meteo."""
    type = "weather"
    # Open-Meteo refreshes "current" every 15 min
    defaults = {"every": 900, "place": "LONDON", "lat": 51.5074, "lon": -0.1278, "timezone": "Europe/London"}

    def frames(self):
        data = self.get_json(URL, latitude=self.lat, longitude=self.lon, timezone=self.timezone, forecast_days=1,
                             current="temperature_2m,weather_code", daily="temperature_2m_max,temperature_2m_min")
        cur, day = data["current"], data["daily"]
        t = self.theme
        img, d = canvas(t)
        d.text((SIZE // 2, 12), self.place, fill=t.muted, font=font(12), anchor="mm")
        d.text((SIZE // 2, 52), f"{cur['temperature_2m']:.0f}°", fill=t.text, font=font(44), anchor="mm")
        d.text((SIZE // 2, 90), describe(cur["weather_code"]), fill=t.text, font=font(15), anchor="mm")
        d.text((SIZE // 2, 114), f"{day['temperature_2m_max'][0]:.0f}° / {day['temperature_2m_min'][0]:.0f}°",
               fill=t.muted, font=font(12), anchor="mm")
        return [img]

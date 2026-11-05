"""Widget registry: the `type` used in config.toml -> class. Add a new widget here."""
from .base import ConfigError, Widget
from .gcalendar import Calendar
from .chart import Chart
from .clock import Clock
from .gmail import Gmail
from .prices import Prices
from .rates import Rates
from .text import Text
from .google import GoogleWidget
from .weather import Weather

REGISTRY = {cls.type: cls for cls in (Text, Clock, Rates, Prices, Chart, Weather, Gmail, Calendar)}

__all__ = ["REGISTRY", "ConfigError", "GoogleWidget", "Widget"]

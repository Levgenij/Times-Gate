from ..render import SIZE, canvas, fmt, font
from .base import ConfigError, Widget

KLINES = {
    "futures": "https://fapi.binance.com/fapi/v1/klines",
    "spot": "https://api.binance.com/api/v3/klines",
}
TOP, BOTTOM, LEFT, RIGHT = 44, 122, 4, SIZE - 4  # chart area


def points(values):
    """Map values to (x, y) inside the chart area; max at TOP, min at BOTTOM."""
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1  # flat series: draw along the bottom
    step = (RIGHT - LEFT) / max(len(values) - 1, 1)
    return [(LEFT + i * step, BOTTOM - (v - lo) / span * (BOTTOM - TOP)) for i, v in enumerate(values)]


class Chart(Widget):
    """Line chart of Binance candle closes, change % and last price; green if up, red if down."""
    type = "chart"
    defaults = {"every": 300, "market": "futures", "symbol": "BTCUSDT",
                "interval": "15m", "candles": 96, "title": "BTC 24h"}  # 96 x 15m = 24 h
    label, about = "Chart", "Binance candle closes, change in % and the last price"
    choices = {"market": list(KLINES),
               "interval": ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w"]}
    help = {"market": "futures = USDⓈ-M perpetual futures, spot = spot",
            "symbol": "The full pair, e.g. BTCUSDT", "interval": "Length of one candle",
            "candles": "Number of candles, 2–1000 (96 × 15m = a day)", "title": "Caption above the chart"}

    def setup(self):
        if self.market not in KLINES:
            raise ConfigError(f"chart: market must be one of {', '.join(KLINES)}")
        if not 2 <= self.candles <= 1000:  # Binance returns at most 1000 (spot) / 1500 (futures)
            raise ConfigError("chart: candles must be 2-1000")

    def frames(self):
        candles = self.get_json(KLINES[self.market], symbol=self.symbol, interval=self.interval, limit=self.candles)
        first_open, closes = float(candles[0][1]), [float(c[4]) for c in candles]
        change = (closes[-1] / first_open - 1) * 100
        t = self.theme
        line, fill = (t.up, t.up_fill) if change >= 0 else (t.down, t.down_fill)
        img, d = canvas(t)
        d.text((6, 10), self.title, fill=t.muted, font=font(12), anchor="lm")
        d.text((SIZE - 6, 10), f"{change:+.1f}%", fill=line, font=font(12), anchor="rm")
        d.text((SIZE // 2, 29), fmt(closes[-1]), fill=t.text, font=font(19), anchor="mm")
        pts = points(closes)
        d.polygon(pts + [(RIGHT, BOTTOM), (LEFT, BOTTOM)], fill=fill)
        d.line(pts, fill=line, width=2)
        return [img]

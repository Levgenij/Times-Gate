import time

from ..render import SIZE, canvas, fmt, font
from .base import ConfigError, Widget

# One request returns every symbol of the market (no API key needed).
TICKERS = {
    "futures": "https://fapi.binance.com/fapi/v1/ticker/price",  # USDⓈ-M perpetuals
    "spot": "https://api.binance.com/api/v3/ticker/price",
}


class Prices(Widget):
    """Up to 4 Binance last prices, with the time of the update."""
    type = "prices"
    # ALCH / SPY / BSB exist on Binance only as futures, not spot
    defaults = {"every": 300, "market": "futures", "quote": "USDT", "symbols": ["BTC", "ALCH", "SPY", "BSB"]}

    def setup(self):
        if self.market not in TICKERS:
            raise ConfigError(f"prices: market must be one of {', '.join(TICKERS)}")
        if not 1 <= len(self.symbols) <= 4:
            raise ConfigError("prices: symbols takes 1-4 tickers (the screen fits four rows)")

    def frames(self):
        every = {p["symbol"]: float(p["price"]) for p in self.get_json(TICKERS[self.market])}
        img, d = canvas(self.theme)
        small, big = font(12), font(17)
        for i, symbol in enumerate(self.symbols):
            y = 14 + i * 27
            d.text((6, y), symbol, fill=self.theme.muted, font=small, anchor="lm")
            # a symbol missing on the market is shown as --
            d.text((SIZE - 6, y), fmt(every.get(symbol + self.quote)), fill=self.theme.text, font=big, anchor="rm")
        d.text((SIZE // 2, 118), time.strftime("%H:%M"), fill=self.theme.dim, font=small, anchor="mm")
        return [img]

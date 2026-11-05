import time

import requests

from ..render import SIZE, canvas, fmt, font
from .base import ConfigError, Widget

# Last price and rolling 24 h change of one pair (no API key needed). One small request per pair: without
# `symbol` the endpoint returns the whole market (futures ~300 KB, spot ~1.9 MB) for the 4 rows shown.
TICKERS = {
    "futures": "https://fapi.binance.com/fapi/v1/ticker/24hr",  # USDⓈ-M perpetuals
    "spot": "https://api.binance.com/api/v3/ticker/24hr",
}


class Prices(Widget):
    """Up to 4 Binance last prices with their 24 h change, and the time of the update."""
    type = "prices"
    # ALCH / SPY / BSB exist on Binance only as futures, not spot
    defaults = {"every": 300, "market": "futures", "quote": "USDT", "symbols": ["BTC", "ALCH", "SPY", "BSB"]}
    label, about = "Prices", "Latest Binance prices and 24 h change, up to 4 rows"
    choices = {"market": list(TICKERS)}
    help = {"market": "futures = USDⓈ-M perpetual futures, spot = spot", "quote": "Quote currency",
            "symbols": "Tickers without the quote currency, 1–4"}

    def setup(self):
        if self.market not in TICKERS:
            raise ConfigError(f"prices: market must be one of {', '.join(TICKERS)}")
        if not 1 <= len(self.symbols) <= 4:
            raise ConfigError("prices: symbols takes 1-4 tickers (the screen fits four rows)")

    def ticker(self, pair):
        """(last price, 24 h change %), or (None, None) if the market has no such pair."""
        try:
            p = self.get_json(TICKERS[self.market], symbol=pair)
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 400:  # Binance -1121 "Invalid symbol."
                return None, None
            raise
        return float(p["lastPrice"]), float(p["priceChangePercent"])

    def frames(self):
        t = self.theme
        img, d = canvas(t)
        small, big = font(12), font(17)
        for i, symbol in enumerate(self.symbols):
            y = 14 + i * 27
            price, change = self.ticker(symbol + self.quote)  # missing on the market: shown as --
            d.text((6, y - 6), symbol, fill=t.muted, font=small, anchor="lm")
            if change is not None:  # the same +x.x% as the chart, green / red
                d.text((6, y + 7), f"{change:+.1f}%", fill=t.up if change >= 0 else t.down, font=small, anchor="lm")
            d.text((SIZE - 6, y), fmt(price), fill=t.text, font=big, anchor="rm")
        d.text((SIZE // 2, 118), time.strftime("%H:%M"), fill=t.dim, font=small, anchor="mm")
        return [img]

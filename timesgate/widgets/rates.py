import time

from ..render import SIZE, canvas, font
from .base import ConfigError, Widget

URL = "https://api.privatbank.ua/p24api/exchange_rates"


def parse(data, currencies):
    """{'USD': (buy, sell), ...} or None if the day has no bank rates yet."""
    rows = {r["currency"]: r for r in data.get("exchangeRate", [])}
    if not all("saleRate" in rows.get(c, {}) for c in currencies):
        return None
    return {c: (rows[c]["purchaseRate"], rows[c]["saleRate"]) for c in currencies}


class Rates(Widget):
    """PrivatBank buy / sell rates to UAH, with the date they are for."""
    type = "rates"
    defaults = {"every": 5 * 3600, "retry": 300, "currencies": ["USD", "EUR"]}
    label, about = "Курси валют", "Купівля / продаж у ПриватБанку до гривні"
    help = {"currencies": "Коди валют, 1–2, напр. USD, EUR"}

    def setup(self):
        if not 1 <= len(self.currencies) <= 2:
            raise ConfigError("rates: currencies takes 1-2 codes (the screen fits two rows)")

    def fetch(self):
        for days_back in (0, 1):  # today's rates may not be published yet
            day = time.strftime("%d.%m.%Y", time.localtime(time.time() - days_back * 86400))
            rates = parse(self.get_json(f"{URL}?json&date={day}"), self.currencies)  # API needs a date
            if rates:
                return rates, day
        raise RuntimeError(f"no {'/'.join(self.currencies)} rates for today or yesterday")

    def frames(self):
        rates, day = self.fetch()
        img, d = canvas(self.theme)
        small, big = font(12), font(19)
        for y, (cur, (buy, sell)) in zip((24, 70), rates.items()):
            d.text((SIZE // 2, y), f"{cur} / UAH", fill=self.theme.muted, font=small, anchor="mm")
            d.text((SIZE // 2, y + 20), f"{buy:.2f}  {sell:.2f}", fill=self.theme.text, font=big, anchor="mm")
        d.text((SIZE // 2, 118), day, fill=self.theme.dim, font=small, anchor="mm")
        return [img]

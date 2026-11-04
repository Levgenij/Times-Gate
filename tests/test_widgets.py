import time
import unittest
from unittest.mock import patch

from PIL import ImageChops

from helpers import ctx
from timesgate.render import fmt
from timesgate.widgets import ConfigError
from timesgate.widgets.chart import BOTTOM, LEFT, RIGHT, TOP, points
from timesgate.widgets.clock import Clock
from timesgate.widgets.gmail import Gmail, decide, plural
from timesgate.widgets.prices import Prices
from timesgate.widgets.rates import parse
from timesgate.widgets.weather import describe


class RatesTest(unittest.TestCase):
    def test_picks_bank_rates(self):
        data = {"exchangeRate": [
            {"currency": "EUR", "saleRateNB": 51.05, "purchaseRateNB": 51.05, "saleRate": 51.7, "purchaseRate": 50.7},
            {"currency": "USD", "saleRateNB": 45.66, "purchaseRateNB": 45.66, "saleRate": 46.1, "purchaseRate": 45.5},
            {"currency": "NOK", "saleRateNB": 4.94, "purchaseRateNB": 4.94},
        ]}
        self.assertEqual(parse(data, ["USD", "EUR"]), {"USD": (45.5, 46.1), "EUR": (50.7, 51.7)})

    def test_not_published_yet(self):
        self.assertIsNone(parse({"exchangeRate": []}, ["USD"]))
        # only NBU rate, no bank rate for USD
        self.assertIsNone(parse({"exchangeRate": [
            {"currency": "USD", "saleRateNB": 45.66, "purchaseRateNB": 45.66},
            {"currency": "EUR", "saleRate": 51.7, "purchaseRate": 50.7}]}, ["USD", "EUR"]))


class FmtTest(unittest.TestCase):
    def test_ranges(self):
        self.assertEqual(fmt(79920), "79,920")
        self.assertEqual(fmt(767.495), "767.50")
        self.assertEqual(fmt(0.03820055), "0.0382")
        self.assertEqual(fmt(0.089983), "0.08998")
        self.assertEqual(fmt(None), "--")


class ChartTest(unittest.TestCase):
    def test_scales_into_chart_area(self):
        pts = points([10, 30, 20])
        self.assertEqual(pts[0], (LEFT, BOTTOM))   # min at the bottom-left
        self.assertEqual(pts[1][1], TOP)           # max at the top
        self.assertEqual(pts[-1][0], RIGHT)        # last point at the right edge

    def test_flat_series(self):
        self.assertTrue(all(y == BOTTOM for _, y in points([5, 5, 5])))


class WeatherTest(unittest.TestCase):
    def test_codes(self):
        self.assertEqual(describe(0), "Clear")
        self.assertEqual(describe(3), "Overcast")
        self.assertEqual(describe(63), "Rain")
        self.assertEqual(describe(99), "Thunderstorm")
        self.assertEqual(describe(42), "")  # unknown code: no label rather than a crash


class GmailTest(unittest.TestCase):
    def test_decide_sequence(self):
        showing, prev = False, 0
        expected = [(0, False), (3, True), (3, True), (5, True), (4, False), (4, False), (6, True), (0, False)]
        for count, want in expected:
            showing, prev = decide(prev, count, showing), count
            self.assertEqual(showing, want, f"count={count}")

    def test_plural(self):
        forms = ["непрочитаний", "непрочитані", "непрочитаних"]
        for n, want in [(1, 0), (21, 0), (101, 0), (2, 1), (4, 1), (23, 1), (5, 2), (0, 2),
                        (11, 2), (12, 2), (14, 2), (111, 2), (112, 2)]:
            self.assertEqual(plural(n, forms), forms[want], f"n={n}")

    def test_unread_parses_status_and_quotes_folder(self):
        g = Gmail(ctx(GMAIL_USER="a@b.c", GMAIL_APP_PASSWORD="pw"), folder="[Gmail]/All Mail")
        with patch("timesgate.widgets.gmail.imaplib.IMAP4_SSL") as ssl:
            imap = ssl.return_value.__enter__.return_value
            imap.status.return_value = ("OK", [b'"[Gmail]/All Mail" (UNSEEN 7)'])
            self.assertEqual(g.unread(), 7)
        imap.status.assert_called_once_with('"[Gmail]/All Mail"', "(UNSEEN)")

    def test_disabled_without_credentials_yields(self):
        with self.assertLogs("timesgate.gmail", "WARNING"):
            g = Gmail(ctx())
        self.assertIsNone(g.frames())


class ClockTest(unittest.TestCase):
    def test_blink_frames_differ_only_by_colon(self):
        c = Clock(ctx())
        now = time.strptime("2026-11-04 22:07", "%Y-%m-%d %H:%M")
        on, off = c.render(now), c.render(now, colon=False)
        x0, _, x1, _ = ImageChops.difference(on, off).getbbox()
        self.assertLess(x1 - x0, 10)  # just the colon column, digits did not move
        self.assertEqual(c.speed, 500)

    def test_weekdays(self):
        c = Clock(ctx())
        self.assertEqual(c.weekdays[time.strptime("2026-11-04", "%Y-%m-%d").tm_wday], "Сер")
        self.assertEqual(c.weekdays[time.strptime("2026-11-08", "%Y-%m-%d").tm_wday], "Нед")

    def test_no_blink_single_frame(self):
        self.assertEqual(len(Clock(ctx(), blink=False).frames()), 1)


class OptionsTest(unittest.TestCase):
    def test_unknown_option(self):
        with self.assertRaisesRegex(ConfigError, "unknown option"):
            Clock(ctx(), blnk=True)

    def test_bad_values(self):
        with self.assertRaises(ConfigError):
            Prices(ctx(), market="margin")
        with self.assertRaises(ConfigError):
            Prices(ctx(), symbols=["A", "B", "C", "D", "E"])
        with self.assertRaises(ConfigError):
            Clock(ctx(), every=0)
        with self.assertRaises(ConfigError):
            Clock(ctx(), weekdays=["Mon"])


if __name__ == "__main__":
    unittest.main()

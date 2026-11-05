import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from google.auth.exceptions import RefreshError
from PIL import ImageChops

from helpers import ctx
from timesgate.render import fmt
from timesgate.widgets import ConfigError
from timesgate.widgets.chart import BOTTOM, LEFT, RIGHT, TOP, points
from timesgate.widgets.clock import Clock
from timesgate.widgets.gmail import SCOPES, Gmail, decide, plural
from timesgate.widgets.prices import Prices
from timesgate.widgets.rates import parse
from timesgate.widgets import icons
from timesgate.widgets.weather import Weather, deg, lookup


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
        self.assertEqual(lookup(0), ("Clear", "clear"))
        self.assertEqual(lookup(3), ("Overcast", "overcast"))
        self.assertEqual(lookup(63), ("Rain", "rain"))
        self.assertEqual(lookup(99), ("Thunderstorm", "thunder"))
        self.assertEqual(lookup(42), ("", "overcast"))  # unknown code: no label rather than a crash

    def test_every_code_has_a_drawable_icon(self):
        for code in [0, 1, 2, 3, 45, 48, *range(51, 58), *range(61, 68), *range(71, 78), 80, 81, 82, 85, 86,
                     95, 96, 99, 42]:
            kind = lookup(code)[1]
            self.assertIn(kind, icons.KINDS, f"code={code}")
            for day in (True, False):
                self.assertIsNotNone(icons.draw(kind, day).getbbox(), f"{kind} day={day} is empty")

    def test_no_negative_zero(self):
        self.assertEqual(deg(-0.3), "0°")
        self.assertEqual(deg(-0.6), "-1°")

    def test_render_fits_long_temperature(self):
        img = Weather(ctx()).render(-12.4, 73, True, -3, -15)
        self.assertEqual(img.size, (128, 128))


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

    def gmail(self, **opts):
        with tempfile.TemporaryDirectory() as d, self.assertLogs("timesgate.gmail", "WARNING"):
            return Gmail(ctx(d), **opts)  # no token.json there: disabled

    def test_without_token_yields(self):
        self.assertIsNone(self.gmail().frames())

    def test_unread_reads_label_count(self):
        g = self.gmail(label="CATEGORY_PERSONAL")
        g.session = MagicMock()
        g.session.get.return_value.json.return_value = {"id": "CATEGORY_PERSONAL", "messagesUnread": 7}
        self.assertEqual(g.unread(), 7)
        self.assertTrue(g.session.get.call_args.args[0].endswith("/users/me/labels/CATEGORY_PERSONAL"))
        self.assertIsNotNone(g.frames())  # 0 -> 7 grew: shown

    def test_rejected_token_disables(self):
        g = self.gmail()
        g.session = MagicMock()
        g.session.get.side_effect = RefreshError("invalid_grant")
        with self.assertRaisesRegex(RuntimeError, "--gmail-auth"):
            g.frames()
        self.assertIsNone(g.frames())  # no more calls to Google

    def test_token_file_is_loaded(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "token.json").write_text(json.dumps({
                "token": "a", "refresh_token": "r", "client_id": "c", "client_secret": "s",
                "token_uri": "https://oauth2.googleapis.com/token", "scopes": SCOPES}), encoding="utf-8")
            self.assertIsNotNone(Gmail(ctx(d)).session)


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

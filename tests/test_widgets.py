import json
import tempfile
import time
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

import requests
from google.auth.exceptions import RefreshError
from PIL import ImageChops, ImageColor

from helpers import ctx
from timesgate.i18n import WORDS
from timesgate.render import fit, fmt, font
from timesgate.widgets import ConfigError
from timesgate.widgets import gcalendar
from timesgate.widgets.gcalendar import ROW, Calendar, Item, when
from timesgate.widgets.chart import BOTTOM, LEFT, RIGHT, TOP, points
from timesgate.widgets.clock import Clock
from timesgate.widgets.gmail import SCOPES, Gmail, decide, top
from timesgate.widgets.google import google_error
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
        img = Weather(ctx()).render(-12.4, 73, True, -3, -15, [(6, 95, -12, -15), (0, 3, 2, -8)])
        self.assertEqual(img.size, (128, 128))

    def test_forecast_parses_next_two_days(self):
        w = Weather(ctx())
        w.get_json = MagicMock(return_value={
            "current": {"temperature_2m": 18.4, "weather_code": 2, "is_day": 0},
            "daily": {"time": ["2026-11-05", "2026-11-06", "2026-11-07"], "weather_code": [2, 61, 0],
                      "temperature_2m_max": [21, 19, 23], "temperature_2m_min": [12, 11, 13]}})
        temp, code, is_day, hi, lo, days = w.fetch()
        self.assertEqual((temp, code, is_day, hi, lo), (18.4, 2, False, 21, 12))
        self.assertEqual(days, [(4, 61, 19, 11), (5, 0, 23, 13)])  # Fri, Sat
        self.assertEqual(w.get_json.call_args.kwargs["forecast_days"], 3)

    def test_forecast_off_keeps_today_only(self):
        w = Weather(ctx(), forecast=False)
        w.get_json = MagicMock(return_value={
            "current": {"temperature_2m": 5, "weather_code": 3},
            "daily": {"time": ["2026-11-05"], "weather_code": [3], "temperature_2m_max": [7],
                      "temperature_2m_min": [1]}})
        self.assertEqual(w.fetch()[-1], [])
        self.assertEqual(w.get_json.call_args.kwargs["forecast_days"], 1)


class GmailTest(unittest.TestCase):
    def test_decide_sequence(self):
        showing, prev = False, 0
        expected = [(0, False), (3, True), (3, True), (5, True), (4, False), (4, False), (6, True), (0, False)]
        for count, want in expected:
            showing, prev = decide(prev, count, showing), count
            self.assertEqual(showing, want, f"count={count}")

    def test_top_rows(self):
        counts = [("Inbox", 2), ("Work", 5), ("Bank", 0), ("A", 1), ("B", 3), ("C", 1)]
        self.assertEqual(top(counts), [("Work", 5), ("B", 3), ("Inbox", 2), ("A", 1)])  # no zero, at most 4

    def test_rows_are_inbox_and_own_labels(self):
        g = self.gmail()
        g.session = MagicMock()
        labels = [{"id": "INBOX", "name": "INBOX", "type": "system"}, {"id": "SPAM", "name": "SPAM", "type": "system"},
                  {"id": "CATEGORY_SOCIAL", "name": "CATEGORY_SOCIAL", "type": "system"},
                  {"id": "Label_1", "name": "Work", "type": "user"}, {"id": "Label_2", "name": "Bank", "type": "user"}]
        unread = {"UNREAD": 9, "INBOX": 4, "SPAM": 7, "CATEGORY_SOCIAL": 8, "Label_1": 2, "Label_2": 0}

        def get(url, **_):
            r = MagicMock(ok=True)
            last = url.rsplit("/", 1)[-1]
            r.json.return_value = {"labels": labels} if last == "labels" else {"messagesUnread": unread[last]}
            return r
        g.session.get.side_effect = get
        self.assertEqual(g.rows(), [("Вхідні", 4), ("Work", 2)])  # no SPAM / categories, no empty labels
        (img,) = g.frames()  # total UNREAD 0 -> 9 grew: shown
        self.assertEqual(img.size, (128, 128))

    def test_no_label_rows_shows_big_number(self):
        g = self.gmail()
        line = (60, 31)  # the divider under Total, drawn only above label rows
        self.assertNotEqual(g.render(3, [("Work", 3)]).getpixel(line), (0, 0, 0))
        big = g.render(3, [])
        self.assertEqual(big.getpixel(line), (0, 0, 0))
        _, top_y, _, bottom_y = ImageChops.difference(big, g.render(4, [])).getbbox()
        self.assertGreater(bottom_y - top_y, 30)  # only the number changed, and it is tall
        left, _, right, _ = g.render(18888, []).getbbox()
        self.assertGreater(left, 0)  # 5 digits get a smaller font instead of being clipped
        self.assertLess(right, 128)

    def gmail(self, **opts):
        with tempfile.TemporaryDirectory() as d, self.assertLogs("timesgate.gmail", "WARNING"):
            return Gmail(ctx(d), **opts)  # no token there: disabled

    def test_without_token_yields(self):
        self.assertIsNone(self.gmail().frames())

    def test_unread_reads_label_count(self):
        g = self.gmail(label="CATEGORY_PERSONAL")
        g.session = MagicMock()
        g.session.get.return_value.json.return_value = {"id": "CATEGORY_PERSONAL", "messagesUnread": 7}
        self.assertEqual(g.unread(), 7)
        self.assertTrue(g.session.get.call_args.args[0].endswith("/users/me/labels/CATEGORY_PERSONAL"))
        g.session.get.return_value.json.return_value = {"messagesUnread": 0}
        self.assertIsNone(g.frames())  # nothing unread: no label requests, the slot falls through
        self.assertEqual(g.session.get.call_count, 2)

    def test_rejected_token_disables(self):
        g = self.gmail()
        g.session = MagicMock()
        g.session.get.side_effect = RefreshError("invalid_grant")
        with self.assertRaisesRegex(RuntimeError, "--google-auth"):
            g.frames()
        self.assertIsNone(g.frames())  # no more calls to Google

    def test_token_file_is_loaded(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "secrets").mkdir()
            Path(d, "secrets", "token_gmail.json").write_text(json.dumps({
                "token": "a", "refresh_token": "r", "client_id": "c", "client_secret": "s",
                "token_uri": "https://oauth2.googleapis.com/token", "scopes": SCOPES}), encoding="utf-8")
            self.assertIsNotNone(Gmail(ctx(d)).session)


UK = WORDS["uk"]


class CalendarTest(unittest.TestCase):
    NOW = datetime(2026, 11, 5, 12, 0).astimezone()  # Thursday noon, local time

    def test_parse(self):
        events = gcalendar.parse([
            {"summary": "Дзвінок", "start": {"dateTime": "2026-11-05T10:00:00Z"}, "end": {"dateTime": "2026-11-05T11:00:00Z"}},
            {"summary": "Відхилено", "start": {"dateTime": "2026-11-05T13:00:00+02:00"},
             "end": {"dateTime": "2026-11-05T14:00:00+02:00"},
             "attendees": [{"self": True, "responseStatus": "declined"}]},
            {"start": {"date": "2026-11-06"}, "end": {"date": "2026-11-07"}},
        ])
        self.assertEqual(len(events), 2)  # the declined one is skipped
        start, end, title, all_day, task = events[0]
        self.assertEqual(start, datetime(2026, 11, 5, 10, 0, tzinfo=timezone.utc))
        self.assertEqual(start.utcoffset(), self.NOW.utcoffset())  # shown in the PC's zone
        self.assertEqual((title, all_day, task), ("Дзвінок", False, False))
        self.assertEqual(events[1], Item(date(2026, 11, 6), date(2026, 11, 7), "(untitled)", True))

    def test_parse_tasks(self):
        tasks = gcalendar.parse_tasks([
            {"title": "Оплатити інтернет", "status": "needsAction", "due": "2026-11-06T00:00:00.000Z"},
            {"title": "Без дати", "status": "needsAction"},
            {"title": "Здати звіт", "status": "completed", "due": "2026-11-05T00:00:00.000Z",
             "completed": "2026-11-05T09:15:00.000Z"},
        ])
        self.assertEqual(tasks, [Item(date(2026, 11, 6), date(2026, 11, 7), "Оплатити інтернет", True, True),
                                 Item(None, None, "Без дати", True, True)])  # the completed one is not shown

    def test_when(self):
        now, h, today, day = self.NOW, timedelta(hours=1), self.NOW.date(), timedelta(days=1)
        ev = lambda s, e, all_day=False: when(Item(s, e, "x", all_day), now, UK)  # noqa: E731
        self.assertEqual(ev(now - h, now + h), f"Зараз · до {now + h:%H:%M}")
        self.assertEqual(ev(now + 2 * h, now + 3 * h), f"Сьогодні {now + 2 * h:%H:%M}")
        self.assertEqual(ev(now + day, now + day + h), "Завтра 12:00")
        self.assertEqual(ev(now + 3 * day, now + 3 * day + h), "Нед 08.11 12:00")
        self.assertEqual(ev(today, today + day, True), "Сьогодні · весь день")
        self.assertEqual(ev(today + day, today + 2 * day, True), "Завтра · весь день")
        self.assertEqual(ev(today + 2 * day, today + 3 * day, True), "Суб 07.11")
        task = lambda due: when(Item(due, due and due + day, "x", True, True), now, UK)  # noqa: E731
        self.assertEqual(task(today), "Сьогодні · завдання")
        self.assertEqual(task(today + day), "Завтра · завдання")
        self.assertEqual(task(today - 2 * day), "Прострочено · 03.11")
        self.assertEqual(task(None), "Завдання")
        self.assertEqual(when(Item(now - h, now + h, "x", False), now, WORDS["en"]), f"Now · until {now + h:%H:%M}")
        self.assertEqual(when(Item(today - 2 * day, today - day, "x", True, True), now, WORDS["en"]), "Overdue · 03.11")

    def test_pick_finished_above_coming(self):
        now, h = self.NOW, timedelta(hours=1)
        ev = lambda a, b: Item(now + a * h, now + b * h, f"{a}", False)  # noqa: E731
        early, late, live, soon, later, tomorrow = ev(-5, -4), ev(-3, -2), ev(-1, 1), ev(2, 3), ev(4, 5), ev(24, 25)
        allday = Item(now.date(), now.date() + timedelta(days=1), "allday", True)  # today, all day: still on
        events = [early, late, allday, live, soon, later, tomorrow]
        self.assertEqual(gcalendar.pick(events, now, 4, 1), ([late], [allday, live, soon]))  # the latest finished one
        self.assertEqual(gcalendar.pick(events, now, 4, 0), ([], [allday, live, soon, later]))
        self.assertEqual(gcalendar.pick([early, late, soon], now, 4, 1), ([early, late], [soon]))  # few coming: more past
        self.assertEqual(gcalendar.pick([early], now, 4, 1), ([early], []))
        self.assertEqual(gcalendar.pick([], now, 4, 1), ([], []))

    def test_tasks_mix_in_order(self):
        now, h, today = self.NOW, timedelta(hours=1), self.NOW.date()
        overdue = Item(today - timedelta(days=2), today - timedelta(days=1), "overdue", True, True)
        meeting = Item(now - 5 * h, now - 4 * h, "meeting", False)  # 07:00-08:00, finished
        due_tomorrow = Item(today + timedelta(days=1), today + timedelta(days=2), "tomorrow", True, True)
        soon = Item(now + h, now + 2 * h, "soon", False)
        undated_a, undated_b = Item(None, None, "a", True, True), Item(None, None, "b", True, True)
        items = sorted([undated_a, due_tomorrow, soon, undated_b, meeting, overdue], key=gcalendar.order)
        # an overdue task stays "coming" (first); tasks without a date last, in their Google Tasks order
        self.assertEqual(items, [overdue, meeting, soon, due_tomorrow, undated_a, undated_b])
        self.assertEqual(gcalendar.pick(items, now, 4, 1), ([meeting], [overdue, soon, due_tomorrow]))

    def test_render_marks_now_line(self):
        now, h = self.NOW, timedelta(hours=1)
        c = Calendar(ctx())
        img = c.render([Item(now - 2 * h, now - h, "Минула", False)],
                       [Item(now.date(), now.date() + timedelta(days=1), "Завдання", True, True)], now)
        self.assertEqual(img.getpixel((60, ROW - 1)), ImageColor.getrgb(c.theme.down))  # red "now" line under row 1
        self.assertEqual(img.getpixel((6, ROW + 19)), ImageColor.getrgb(c.theme.muted))  # task checkbox, left edge

    def calendar(self, items, tasks=(), denied=None):
        with tempfile.TemporaryDirectory() as d, self.assertLogs("timesgate.calendar", "WARNING"):
            c = Calendar(ctx(d))  # no token there: disabled
        self.assertIsNone(c.frames())  # no token: the slot falls through to the next widget
        c.session = MagicMock()

        def get(url, **_):  # events for the calendar URL, `tasks` (or Google's error body `denied`) for the Tasks URL
            r = MagicMock(ok=True, status_code=200)
            r.json.return_value = {"items": items if "/calendars/" in url else tasks}
            if denied and "/tasks" in url:
                r.ok, r.status_code, r.json.return_value = False, 403, denied
            return r
        c.session.get.side_effect = get
        return c

    def test_frames(self):
        item = {"summary": "Дуже довга назва зустрічі, що не влазить у рядок", "start": {"dateTime": "2026-11-05T10:00:00Z"},
                "end": {"dateTime": "2099-11-05T11:00:00Z"}}
        c = self.calendar([item] * 5)
        (img,) = c.frames()
        self.assertEqual(img.size, (128, 128))
        events_call, open_call = c.session.get.call_args_list  # completed tasks are not requested
        self.assertTrue(events_call.args[0].endswith("/calendars/primary/events"))
        self.assertEqual((events_call.kwargs["params"]["singleEvents"], events_call.kwargs["params"]["orderBy"]),
                         ("true", "startTime"))
        self.assertTrue(open_call.args[0].endswith("/lists/%40default/tasks"))
        self.assertEqual(open_call.kwargs["params"]["showCompleted"], "false")
        self.assertNotIn("dueMax", open_call.kwargs["params"])  # it would drop the tasks without a date

    def test_tasks_off_and_scopes(self):
        self.assertEqual(Calendar(ctx()).scopes, [gcalendar.EVENTS_SCOPE, gcalendar.TASKS_SCOPE])
        c = self.calendar([])
        c.tasks = False
        c.frames()
        self.assertEqual(c.session.get.call_count, 1)  # events only
        self.assertEqual(Calendar(ctx(), tasks=False).scopes, [gcalendar.EVENTS_SCOPE])

    def test_google_reason_is_shown(self):
        disabled = {"error": {"code": 403, "message": "Google Tasks API has not been used in project 1 before or it is "
                              "disabled. Enable it by visiting https://console.developers.google.com/apis/api/x",
                              "details": [{"@type": "type.googleapis.com/google.rpc.ErrorInfo",
                                           "reason": "SERVICE_DISABLED"}]}}
        with self.assertRaisesRegex(RuntimeError, r"HTTP 403 SERVICE_DISABLED: Google Tasks API .* Enable it"):
            self.calendar([], denied=disabled).frames()

    def test_google_error_text(self):
        def resp(status, body):
            r = MagicMock(status_code=status)
            r.json.side_effect = body if isinstance(body, Exception) else None
            r.json.return_value = body
            return r
        scope = {"error": {"message": "Request had insufficient authentication scopes.",
                           "errors": [{"reason": "insufficientPermissions"}]}}
        self.assertIn("--google-auth", google_error(resp(403, scope)))  # missing permission: sign in again
        self.assertEqual(google_error(resp(500, ValueError("not json"))), "HTTP 500")

    def test_tasks_read_every_page(self):
        c = self.calendar([])
        pages = {None: {"items": [{"title": "1", "status": "needsAction"}], "nextPageToken": "p2"},
                 "p2": {"items": [{"title": "2", "status": "needsAction"}]}}

        def get(url, params, **_):
            r = MagicMock()
            r.json.return_value = pages[params.get("pageToken")]
            return r
        c.session.get.side_effect = get
        tasks = c.fetch_tasks(self.NOW + timedelta(days=7))
        self.assertEqual([t.title for t in tasks], ["1", "2"])  # the 2nd page is not lost

    def test_undated_tasks_kept_far_ones_dropped(self):
        c = self.calendar([], tasks=[{"title": "Колись", "status": "needsAction"},
                                     {"title": "Далеко", "status": "needsAction", "due": "2099-01-01T00:00:00.000Z"}])
        tasks = c.fetch_tasks(self.NOW + timedelta(days=7))
        self.assertEqual([t.title for t in tasks], ["Колись"])  # due beyond `days`: dropped; no date: kept
        self.assertIsNotNone(c.frames())  # an undated task alone still counts as coming

    def test_no_events_falls_through(self):
        self.assertIsNone(self.calendar([]).frames())
        finished = {"summary": "Стендап", "start": {"dateTime": "2000-01-01T09:00:00Z"},
                    "end": {"dateTime": "2000-01-01T10:00:00Z"}}
        self.assertIsNone(self.calendar([finished]).frames())  # only finished ones: nothing coming -> next widget

    def test_show_if(self):
        today = self.NOW.date()
        h = timedelta(hours=1)
        meeting = Item(self.NOW + 26 * h, self.NOW + 27 * h, "Завтра", False)  # a datetime: compared by its day
        task = Item(today - timedelta(days=3), today, "Прострочене", True, True)
        undated = Item(None, None, "Колись", True, True)
        self.assertFalse(gcalendar.due_by([meeting, undated], today))
        self.assertTrue(gcalendar.due_by([meeting], today + timedelta(days=1)))
        self.assertTrue(gcalendar.due_by([task], today))  # overdue counts as today
        c = self.calendar([], tasks=[{"title": "Колись", "status": "needsAction"}])
        c.show_if = "today"
        self.assertIsNone(c.frames())  # only an undated task: next widget

    def test_bad_options(self):
        with self.assertRaises(ConfigError):
            Calendar(ctx(), show_if="week")
        with self.assertRaises(ConfigError):
            Calendar(ctx(), count=5)
        with self.assertRaises(ConfigError):
            Calendar(ctx(), days=0)
        with self.assertRaises(ConfigError):
            Calendar(ctx(), count=2, past=2)  # no row left for coming events


class FitTest(unittest.TestCase):
    def test_cuts_with_ellipsis(self):
        f = font(13)
        self.assertEqual(fit("short", f, 116), "short")
        cut = fit("a very long event title that does not fit", f, 60)
        self.assertTrue(cut.endswith("…"))
        self.assertLessEqual(f.getlength(cut), 60)


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


class PricesTest(unittest.TestCase):
    def test_change_is_green_up_red_down(self):
        w = Prices(ctx(), symbols=["BTC", "ALCH", "NOPE"])
        rows = {"BTCUSDT": {"lastPrice": "79578.1", "priceChangePercent": "1.62"},
                "ALCHUSDT": {"lastPrice": "0.0382", "priceChangePercent": "-4.10"}}

        def get_json(url, symbol):  # Binance answers 400 for a pair the market does not have
            if symbol not in rows:
                raise requests.HTTPError(response=MagicMock(status_code=400))
            return rows[symbol]
        w.get_json = MagicMock(side_effect=get_json)
        (img,) = w.frames()  # NOPE is not on the market: "--", no crash
        def tint(y0, y1):  # anti-aliased text: count clearly green / red pixels in the left column of a row
            px = [img.getpixel((x, y)) for x in range(6, 50) for y in range(y0, y1)]
            return sum(g > r + 60 for r, g, b in px), sum(r > g + 60 for r, g, b in px)
        green, red = tint(16, 27)
        self.assertTrue(green > 10 and red == 0)   # BTC +1.6% under the ticker, row 1
        green, red = tint(43, 54)
        self.assertTrue(red > 10 and green == 0)   # ALCH -4.1%, row 2
        self.assertEqual(tint(70, 81), (0, 0))     # NOPE: no change shown
        self.assertTrue(w.get_json.call_args.args[0].endswith("/ticker/24hr"))
        # one small request per shown pair, never the whole market
        self.assertEqual([c.kwargs["symbol"] for c in w.get_json.call_args_list], ["BTCUSDT", "ALCHUSDT", "NOPEUSDT"])

    def test_other_errors_are_not_hidden(self):
        w = Prices(ctx(), symbols=["BTC"])
        w.get_json = MagicMock(side_effect=requests.HTTPError(response=MagicMock(status_code=429)))
        with self.assertRaises(requests.HTTPError):  # rate limit: keep the last frame, retry later
            w.frames()


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

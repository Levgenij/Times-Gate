from datetime import date, datetime, time, timedelta
from typing import NamedTuple
from urllib.parse import quote

from ..render import SIZE, WEEKDAYS, canvas, fit, font
from .base import ConfigError
from .google import GoogleWidget

# Read-only: this token cannot change, create or delete events or tasks.
EVENTS_SCOPE = "https://www.googleapis.com/auth/calendar.events.readonly"
TASKS_SCOPE = "https://www.googleapis.com/auth/tasks.readonly"
EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/{}/events"
TASKS_URL = "https://tasks.googleapis.com/tasks/v1/lists/{}/tasks"
ROW = 32  # 4 rows x 32 px = the whole 128 px screen


class Item(NamedTuple):
    """One row: a calendar event or a Google Tasks task."""
    start: date      # datetime for timed events; date for all-day events and tasks (due day; None = no due date)
    end: date        # events: end (all-day: exclusive date); task: due + 1 day
    title: str
    all_day: bool
    task: bool = False


def parse(items):
    """Calendar API items -> [Item]; times in the PC's local zone, declined events skipped."""
    events = []
    for it in items:
        if any(a.get("self") and a.get("responseStatus") == "declined" for a in it.get("attendees", [])):
            continue
        s, e = it["start"], it["end"]
        if "dateTime" in s:
            start, end, all_day = (datetime.fromisoformat(s["dateTime"]).astimezone(),
                                   datetime.fromisoformat(e["dateTime"]).astimezone(), False)
        else:  # all-day: dates, end exclusive
            start, end, all_day = date.fromisoformat(s["date"]), date.fromisoformat(e["date"]), True
        events.append(Item(start, end, it.get("summary") or "(без назви)", all_day))
    return events


def parse_tasks(items):
    """Tasks API items -> [Item] of open tasks; a task without a due date gets start None."""
    tasks = []
    for t in items:
        if t.get("status") == "completed":
            continue
        # the API keeps only the date: "2026-11-06T00:00:00.000Z"
        due = date.fromisoformat(t["due"][:10]) if "due" in t else None
        tasks.append(Item(due, due and due + timedelta(days=1), t.get("title") or "(без назви)", True, True))
    return tasks


def ended(item, now):
    if item.task:
        return False  # an open task stays "coming" even when overdue
    return item.end <= now.date() if item.all_day else item.end <= now


def order(item):
    """Sort key: start time (a day = its midnight); tasks without a due date last, keeping their order from
    Google Tasks (sorted() is stable)."""
    at = item.start
    if at is None:
        return 1, 0
    return 0, at if isinstance(at, datetime) else datetime.combine(at, time.min).astimezone()


def day_name(day, today):
    if day == today:
        return "Сьогодні"
    if day == today + timedelta(days=1):
        return "Завтра"
    return f"{WEEKDAYS[day.weekday()]} {day:%d.%m}"


def when(item, now):
    """Short time line for a row, relative to `now` (aware local datetime)."""
    start, end, _, all_day, task = item
    today = now.date()
    if task:
        if start is None:
            return "Завдання"
        return f"Прострочено · {start:%d.%m}" if start < today else f"{day_name(start, today)} · завдання"
    if all_day:
        if start <= today < end:
            return "Сьогодні · весь день"
        name = day_name(start, today)
        return f"{name} · весь день" if name == "Завтра" else name  # other days: a date without a time = all day
    if start <= now < end:
        return f"Зараз · до {end:%H:%M}"
    return f"{day_name(start.date(), today)} {start:%H:%M}"


def pick(items, now, count, past):
    """(finished, coming) rows: up to `past` of today's finished items, more if few are coming; ongoing = coming."""
    done = [e for e in items if ended(e, now)]
    ahead = [e for e in items if not ended(e, now)]
    n_done = min(len(done), max(past, count - len(ahead)))
    return done[len(done) - n_done:], ahead[:count - n_done]  # the latest finished ones, the nearest coming ones


class Calendar(GoogleWidget):
    """Google Calendar events and open Google Tasks: today's last finished events (grey) above a "now" line, then the
    next ones; nothing coming within `days` -> nothing to show (falls through to the slot's next widget)."""
    type = "calendar"
    defaults = {
        "every": 300,
        "calendar": "primary",
        "tasks": True,          # also open Google Tasks; completed ones are not shown
        "tasklist": "@default",  # "My Tasks"
        "days": 7,       # look this far ahead
        "count": 4,
        "past": 1,       # today's finished events kept on top, greyed out
        "client_secret": "secrets/client_secret*.json",
        "token": "secrets/token_calendar.json",  # its own token: Gmail keeps working, access revocable separately
    }
    label, about = "Календар", "Події й завдання Google: сьогоднішні минулі події сірим, далі найближчі"
    help = {**GoogleWidget.help, "calendar": "Id календаря: primary — основний, інші в налаштуваннях Google Calendar",
            "tasks": "Показувати й невиконані завдання Google Tasks; без дати — в кінці (потрібен вхід із дозволом "
                     "на завдання)",
            "tasklist": "Список завдань: @default — «Мої завдання»",
            "days": "На скільки днів уперед шукати", "count": "Скільки рядків показати, 1–4",
            "past": "Скільки сьогоднішніх минулих подій лишати зверху сірим (менше за count)"}

    def setup(self):
        if not 1 <= self.count <= 4:
            raise ConfigError("calendar: count takes 1-4 (the screen fits four rows)")
        if not isinstance(self.days, (int, float)) or self.days <= 0:
            raise ConfigError("calendar: days must be a positive number")
        if not isinstance(self.past, int) or not 0 <= self.past < self.count:
            raise ConfigError("calendar: past takes 0 to count-1, so at least one row is left for coming events")
        self.scopes = [EVENTS_SCOPE] + ([TASKS_SCOPE] if self.tasks else [])  # sign-in asks for exactly these
        super().setup()

    def fetch_events(self, midnight, until):
        data = self.api_json(EVENTS_URL.format(quote(self.calendar, safe="")),
                             timeMin=midnight.isoformat(), timeMax=until.isoformat(),  # from today's start: finished too
                             singleEvents="true", orderBy="startTime",
                             maxResults=50,  # today's finished events come first; room for those and declined ones
                             fields="items(summary,start,end,attendees(self,responseStatus))")
        return parse(data.get("items", []))

    def fetch_tasks(self, until):
        """Open tasks due by `until` or without a due date; completed ones are not shown."""
        url, items, page = TASKS_URL.format(quote(self.tasklist, safe="")), [], None
        while True:  # the API returns at most 100 tasks per page
            # no dueMax: it would drop the tasks without a due date, which go last in the list
            data = self.api_json(url, showCompleted="false", maxResults=100, pageToken=page,  # requests drops None
                                 fields="nextPageToken,items(title,status,due)")
            items += data.get("items", [])
            page = data.get("nextPageToken")
            if not page:
                return [t for t in parse_tasks(items) if t.start is None or t.start <= until.date()]

    def render(self, done, ahead, now):
        t = self.theme
        img, d = canvas(t)
        small, big = font(11, t.cyrillic_font), font(13, t.cyrillic_font)
        rows = [(e, True) for e in done] + [(e, False) for e in ahead]
        for i, (item, finished) in enumerate(rows):
            y = i * ROW
            live = not finished and not item.all_day and item.start <= now < item.end
            overdue = item.task and item.start is not None and item.start < now.date()
            d.text((6, y + 7), when(item, now), font=small, anchor="lm",
                   fill=t.dim if finished else t.up if live else t.down if overdue else t.muted)
            x = 6
            if item.task:  # checkbox before the title
                d.rectangle([6, y + 15, 14, y + 23], outline=t.down if overdue else t.muted)
                x = 19
            d.text((x, y + 20), fit(item.title, big, SIZE - 6 - x), fill=t.muted if finished else t.text,
                   font=big, anchor="lm")
            if i < len(rows) - 1 and i != len(done) - 1:
                d.line([(6, y + ROW - 1), (SIZE - 6, y + ROW - 1)], fill=t.dim)
        if done:  # "now" line between finished and coming rows, like Google Calendar's red time marker
            y = len(done) * ROW - 1
            d.line([(8, y), (SIZE - 6, y)], fill=t.down)
            d.ellipse([3, y - 2, 7, y + 2], fill=t.down)
        return img

    def frames(self):
        if self.session is None:
            return None
        now = datetime.now().astimezone()
        midnight, until = now.replace(hour=0, minute=0, second=0, microsecond=0), now + timedelta(days=self.days)
        items = self.fetch_events(midnight, until) + (self.fetch_tasks(until) if self.tasks else [])
        done, ahead = pick(sorted(items, key=order), now, self.count, self.past)
        return [self.render(done, ahead, now)] if ahead else None  # only finished ones left: show the next widget

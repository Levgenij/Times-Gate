import imaplib

from ..render import SIZE, canvas, font
from .base import ConfigError, Widget


def decide(prev, count, showing):
    """Show when the unread count grows, hide when it drops or hits zero, else keep."""
    if count > prev:
        return True
    if count < prev or count == 0:
        return False
    return showing


def plural(n, forms):
    """Ukrainian form for n: (1 непрочитаний, 2-4 непрочитані, 5+ / 11-14 непрочитаних)."""
    if n % 10 == 1 and n % 100 != 11:
        return forms[0]
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return forms[1]
    return forms[2]


class Gmail(Widget):
    """Unread count, shown only after new mail arrives; otherwise yields to the next widget in the slot.

    Needs GMAIL_USER and GMAIL_APP_PASSWORD (Google app password) in .env or the environment.
    """
    type = "gmail"
    defaults = {"every": 60, "host": "imap.gmail.com", "folder": "INBOX",
                "forms": ["непрочитаний", "непрочитані", "непрочитаних"]}  # for 1 / 2-4 / 5+

    def setup(self):
        if len(self.forms) != 3:
            raise ConfigError("gmail: forms needs 3 words, for 1 / 2-4 / 5+ messages")
        self.user = self.secrets.get("GMAIL_USER")
        self.password = (self.secrets.get("GMAIL_APP_PASSWORD") or "").replace(" ", "")
        self.enabled = bool(self.user and self.password)
        if not self.enabled:
            self.log.warning("GMAIL_USER / GMAIL_APP_PASSWORD not set (.env), gmail widget disabled")
        self.prev, self.showing = 0, False

    def unread(self):
        """Unread messages in the folder (all Gmail tabs). STATUS does not mark anything as read."""
        with imaplib.IMAP4_SSL(self.host, timeout=20) as imap:
            try:
                imap.login(self.user, self.password)
            except imaplib.IMAP4.error as e:
                self.enabled = False  # don't retry a bad password every minute and get the account locked
                raise RuntimeError(f"login failed, gmail disabled until restart: {e}") from e
            _, data = imap.status(f'"{self.folder}"', "(UNSEEN)")  # quoted: names like "[Gmail]/All Mail"
        return int(data[0].split(b"UNSEEN")[1].strip(b" )"))

    def frames(self):
        if not self.enabled:
            return None
        count = self.unread()
        self.showing, self.prev = decide(self.prev, count, self.showing), count
        if not self.showing:
            return None
        t = self.theme
        img, d = canvas(t)
        d.text((SIZE // 2, 16), "Gmail", fill=t.muted, font=font(13), anchor="mm")
        d.text((SIZE // 2, 62), str(count), fill=t.text, font=font(52), anchor="mm")
        d.text((SIZE // 2, 106), plural(count, self.forms), fill=t.muted, font=font(14, t.cyrillic_font), anchor="mm")
        return [img]

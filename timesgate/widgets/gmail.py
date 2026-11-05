from ..render import SIZE, canvas, font
from .base import ConfigError
from .google import GoogleWidget

# Labels and their counts only: this token cannot read, send or delete mail.
SCOPES = ["https://www.googleapis.com/auth/gmail.labels"]
LABEL_URL = "https://gmail.googleapis.com/gmail/v1/users/me/labels/{}"


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


class Gmail(GoogleWidget):
    """Unread count via the Gmail API, shown only after new mail arrives; otherwise yields to the next widget."""
    type = "gmail"
    scopes = SCOPES
    defaults = {
        "every": 60,
        "label": "INBOX",                        # CATEGORY_PERSONAL = the "Primary" tab only
        "client_secret": "client_secret*.json",  # glob, next to config.toml
        "token": "token.json",                   # written by "sign in", next to config.toml
        "forms": ["непрочитаний", "непрочитані", "непрочитаних"],  # for 1 / 2-4 / 5+
    }
    label, about = "Gmail", "Кількість непрочитаних; показується, лише коли їх стало більше"
    help = {**GoogleWidget.help, "label": "INBOX — усі вкладки, CATEGORY_PERSONAL — лише «Основні»",
            "forms": "Слово для 1 / 2–4 / 5+ листів"}

    def setup(self):
        if len(self.forms) != 3:
            raise ConfigError("gmail: forms needs 3 words, for 1 / 2-4 / 5+ messages")
        self.prev, self.showing = 0, False
        super().setup()

    def unread(self):
        return self.api_json(LABEL_URL.format(self.label))["messagesUnread"]

    def frames(self):
        if self.session is None:
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

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import AuthorizedSession
from google.oauth2.credentials import Credentials

from ..render import SIZE, canvas, font
from .base import ConfigError, Widget

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


class Gmail(Widget):
    """Unread count via the Gmail API, shown only after new mail arrives; otherwise yields to the next widget.

    One-time setup: `python -m timesgate --gmail-auth` (opens a browser, writes `token`).
    """
    type = "gmail"
    defaults = {
        "every": 60,
        "label": "INBOX",                        # CATEGORY_PERSONAL = the "Primary" tab only
        "client_secret": "client_secret*.json",  # glob, next to config.toml
        "token": "token.json",                   # written by --gmail-auth, next to config.toml
        "forms": ["непрочитаний", "непрочитані", "непрочитаних"],  # for 1 / 2-4 / 5+
    }

    def setup(self):
        if len(self.forms) != 3:
            raise ConfigError("gmail: forms needs 3 words, for 1 / 2-4 / 5+ messages")
        self.token_path = self.root / self.token
        self.prev, self.showing, self.session = 0, False, None
        if self.token_path.exists():
            creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
            self.session = AuthorizedSession(creds)  # refreshes the hourly access token by itself
        else:
            self.log.warning("%s not found, gmail widget disabled; run: python -m timesgate --gmail-auth",
                             self.token_path.name)

    def authorize(self):
        """Interactive one-time OAuth consent in the browser; saves the refresh token."""
        from google_auth_oauthlib.flow import InstalledAppFlow  # only needed here
        found = sorted(self.root.glob(self.client_secret))
        if not found:
            raise ConfigError(f"gmail: no {self.client_secret} next to the config; download the OAuth "
                              "client (type Desktop app) from Google Cloud Console")
        creds = InstalledAppFlow.from_client_secrets_file(found[0], SCOPES).run_local_server(port=0)
        self.token_path.write_text(creds.to_json(), encoding="utf-8")
        return self.token_path

    def unread(self):
        try:
            r = self.session.get(LABEL_URL.format(self.label), timeout=15)
        except RefreshError as e:
            self.session = None  # revoked or expired: stop retrying every minute
            raise RuntimeError(f"token rejected, gmail disabled; run: python -m timesgate --gmail-auth ({e})") from e
        r.raise_for_status()
        return r.json()["messagesUnread"]

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

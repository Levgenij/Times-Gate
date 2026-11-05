"""Base for widgets that read a Google API with the user's own OAuth token.

One OAuth client (secrets/client_secret*.json, type Desktop app) serves every Google widget; each widget keeps its own
token file in secrets/ with only the scope it needs, so access can be revoked per widget. Paths are relative to
config.toml; secrets/ is gitignored and can be closed to AI tools with one rule.
"""
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import AuthorizedSession
from google.oauth2.credentials import Credentials

from .base import ConfigError, Widget

AUTH_HINT = "sign in: settings page -> Система, or python -m timesgate --google-auth"
SCOPE_REASONS = {"ACCESS_TOKEN_SCOPE_INSUFFICIENT", "insufficientPermissions"}  # the token lacks a permission
_warned = set()  # token paths already reported missing


def google_error(r):
    """Google's own reason for a failed API call, e.g.
    "HTTP 403 SERVICE_DISABLED: Google Tasks API has not been used in project … Enable it by visiting …"."""
    try:
        err = r.json()["error"]
        reasons = ([d["reason"] for d in err.get("details", []) if "reason" in d] or
                   [e["reason"] for e in err.get("errors", []) if "reason" in e])
        message = str(err.get("message", ""))[:300]
    except (ValueError, KeyError, TypeError, AttributeError):  # not Google's JSON error body
        return f"HTTP {r.status_code}"
    text = f"HTTP {r.status_code} {reasons[0] if reasons else ''}: {message}"
    return f"{text}; {AUTH_HINT}" if SCOPE_REASONS & set(reasons) else text


class GoogleWidget(Widget):
    """Subclasses set `scopes` and put `client_secret` and `token` into their `defaults`."""
    scopes = []
    help = {"client_secret": "OAuth-клієнт (Desktop app), шлях від config.toml, можна маску",
            "token": "Створюється кнопкою «Увійти» на вкладці «Система»"}

    def setup(self):
        self.token_path = self.root / self.token
        self.session = None
        if self.token_path.exists():
            creds = Credentials.from_authorized_user_file(self.token_path, self.scopes)
            self.session = AuthorizedSession(creds)  # refreshes the hourly access token by itself
        elif self.token_path not in _warned:  # once: every preview in the settings UI builds a new widget
            _warned.add(self.token_path)
            self.log.warning("%s not found, %s widget disabled; %s", self.token_path.name, self.type, AUTH_HINT)

    def authorize(self):
        """Interactive one-time OAuth consent in the browser; saves the refresh token."""
        from google_auth_oauthlib.flow import InstalledAppFlow  # only needed here
        found = sorted(self.root.glob(self.client_secret))
        if not found:
            raise ConfigError(f"{self.type}: no {self.client_secret} (relative to the config); download the OAuth "
                              "client (type Desktop app) from Google Cloud Console")
        creds = InstalledAppFlow.from_client_secrets_file(found[0], self.scopes).run_local_server(port=0)
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        self.token_path.write_text(creds.to_json(), encoding="utf-8")
        return self.token_path

    def api_json(self, url, **params):
        try:
            r = self.session.get(url, params=params, timeout=15)
        except RefreshError as e:
            self.session = None  # revoked or expired: stop retrying every minute
            raise RuntimeError(f"token rejected, {self.type} disabled; {AUTH_HINT} ({e})") from e
        if not r.ok:  # shown in the settings UI: say what Google says, e.g. which API to enable
            raise RuntimeError(google_error(r))
        return r.json()

from ..render import SIZE, canvas, fit, font
from .google import GoogleWidget

# Labels and their counts only: this token cannot read, send or delete mail.
SCOPES = ["https://www.googleapis.com/auth/gmail.labels"]
LABELS_URL = "https://gmail.googleapis.com/gmail/v1/users/me/labels"
ROWS = 4  # label rows under the total


def decide(prev, count, showing):
    """Show when the unread count grows, hide when it drops or hits zero, else keep."""
    if count > prev:
        return True
    if count < prev or count == 0:
        return False
    return showing


def top(counts):
    """[(name, unread)] with unread mail, most first, at most ROWS."""
    return sorted(((name, n) for name, n in counts if n), key=lambda row: -row[1])[:ROWS]


class Gmail(GoogleWidget):
    """Total unread and up to 4 labels with unread mail (INBOX and your own labels); shown only after new mail
    arrives, otherwise yields to the next widget."""
    type = "gmail"
    scopes = SCOPES
    defaults = {
        "every": 60,
        "label": "UNREAD",  # what Total counts and what makes the screen appear: UNREAD = all unread mail
        "client_secret": "secrets/client_secret*.json",  # glob, relative to config.toml
        "token": "secrets/token_gmail.json",             # written by "sign in"
    }
    label, about = "Gmail", "Unread mail: total and by label; shown only when it grows"
    help = {**GoogleWidget.help,
            "label": "Label counted as Total: UNREAD = all unread mail, INBOX = the inbox only"}

    def setup(self):
        self.prev, self.showing = 0, False
        super().setup()

    def unread(self, label=None):
        return self.api_json(f"{LABELS_URL}/{label or self.label}").get("messagesUnread", 0)

    def rows(self):
        """INBOX and your own labels with unread mail. The list has no counts: one request per label."""
        mine = [l for l in self.api_json(LABELS_URL)["labels"] if l["type"] == "user" or l["id"] == "INBOX"]
        return top([(self.words["inbox"] if l["id"] == "INBOX" else l["name"], self.unread(l["id"])) for l in mine])

    def render(self, total, rows):
        t = self.theme
        img, d = canvas(t)
        small = font(13, t.cyrillic_font)
        if not rows:  # unread mail only outside INBOX and your labels: just the big number
            d.text((SIZE // 2, 16), "Gmail", fill=t.muted, font=font(13), anchor="mm")
            text = str(total)  # 4 digits fit at 52 px; 5 (10000+) would be clipped
            d.text((SIZE // 2, 62), text, fill=t.text, font=font(52 if len(text) <= 4 else 36), anchor="mm")
            d.text((SIZE // 2, 106), self.words["total"], fill=t.muted, font=font(14, t.cyrillic_font), anchor="mm")
            return img
        d.text((6, 15), self.words["total"], fill=t.muted, font=small, anchor="lm")
        d.text((SIZE - 6, 15), str(total), fill=t.text, font=font(24), anchor="rm")
        d.line([(6, 31), (SIZE - 6, 31)], fill=t.dim)
        for i, (name, n) in enumerate(rows):
            y = 46 + i * 23
            count = str(n)
            d.text((SIZE - 6, y), count, fill=t.text, font=small, anchor="rm")
            room = SIZE - 12 - small.getlength(count) - 8
            d.text((6, y), fit(name, small, room), fill=t.text, font=small, anchor="lm")
        return img

    def frames(self):
        if self.session is None:
            return None
        total = self.unread()
        self.showing, self.prev = decide(self.prev, total, self.showing), total
        if not self.showing:
            return None  # labels are fetched only while the screen is shown
        return [self.render(total, self.rows())]

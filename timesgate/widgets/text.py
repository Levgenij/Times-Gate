from ..render import SIZE, canvas, font
from .base import Widget


class Text(Widget):
    """Static centred text (the original Hello World)."""
    type = "text"
    defaults = {"every": 3600, "text": "Hello\nWorld", "size": 22, "cyrillic": False}
    label, about = "Text", "Static centred text"
    help = {"text": "Several lines are fine", "size": "Font size, px",
            "cyrillic": "Cyrillic font from the theme (the default one has none)"}

    def frames(self):
        img, d = canvas(self.theme)
        f = font(self.size, self.theme.cyrillic_font if self.cyrillic else None)
        d.multiline_text((SIZE // 2, SIZE // 2), self.text, fill=self.theme.text, font=f, anchor="mm", align="center")
        return [img]

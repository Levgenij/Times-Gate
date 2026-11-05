import re
import tempfile
import unittest
from pathlib import Path

from timesgate.config import load
from timesgate.i18n import UK, WORDS
from timesgate.widgets import REGISTRY, ConfigError, Widget

PAGE = (Path(__file__).parents[1] / "timesgate" / "ui" / "index.html").read_text(encoding="utf-8")


class TranslationsTest(unittest.TestCase):
    def test_every_settings_page_text_has_ukrainian(self):
        texts = set(re.findall(r"\bt\('((?:[^'\\]|\\.)+)'\)", PAGE))           # t('...') in templates and code
        texts |= set(re.findall(r"\b(?:label|help): '([^']+)'", PAGE))          # tabs, exit modes, hand-made fields
        for block in re.findall(r"const (?:THEME|DEVICE)_LABELS = \{(.*?)\}", PAGE, re.S):
            texts |= set(re.findall(r": '([^']+)'", block))
        texts = {s.replace("\\'", "'") for s in texts}
        self.assertGreater(len(texts), 50)
        self.assertEqual(sorted(texts - set(UK)), [])

    def test_every_widget_text_has_ukrainian(self):
        texts = set(Widget.common_help.values()) | {"Settings", "Refresh screens", "Exit"}
        for cls in REGISTRY.values():
            texts |= {cls.label, cls.about, *cls.help.values()} - {"", "Gmail"}
        self.assertEqual(sorted(texts - set(UK)), [])

    def test_words_cover_the_same_keys(self):
        self.assertEqual(set(WORDS["en"]), set(WORDS["uk"]))


class LanguageConfigTest(unittest.TestCase):
    def load(self, ui):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "config.toml"
            path.write_text(f'[device]\nip = "192.168.1.60"\n{ui}\n[[screen]]\nslot = 3\nwidgets = [{{ type = "clock" }}]\n',
                            encoding="utf-8")
            return load(path)

    def test_default_is_english(self):
        (clock,) = self.load("").slots[0].widgets
        self.assertEqual(clock.weekdays[0], "Mon")

    def test_ukrainian(self):
        (clock,) = self.load('[ui]\nlanguage = "uk"').slots[0].widgets
        self.assertEqual(clock.weekdays[2], "Сер")

    def test_unknown_language(self):
        with self.assertRaisesRegex(ConfigError, "language"):
            self.load('[ui]\nlanguage = "de"')


if __name__ == "__main__":
    unittest.main()

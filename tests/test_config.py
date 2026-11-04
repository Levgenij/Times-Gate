import tempfile
import unittest
from pathlib import Path

from timesgate.config import load
from timesgate.widgets import ConfigError

MINIMAL = """
[device]
ip = "192.168.1.60"

[[screen]]
slot = 3
widgets = [{ type = "text" }]
"""


class ConfigTest(unittest.TestCase):
    def load(self, text):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "config.toml"
            path.write_text(text, encoding="utf-8")
            return load(path)

    def test_minimal_uses_defaults(self):
        cfg = self.load(MINIMAL)
        self.assertEqual(cfg.device.url, "http://192.168.1.60:9000/divoom_api")
        self.assertEqual(cfg.level, "INFO")
        (slot,) = cfg.slots
        self.assertEqual(slot.number, 3)
        self.assertEqual(slot.widgets[0].text, "Hello\nWorld")

    def test_example_config_loads(self):
        example = (Path(__file__).parents[1] / "config.example.toml").read_text(encoding="utf-8")
        with self.assertLogs("timesgate.gmail", "WARNING"):  # temp dir: no token.json, independent of the repo
            cfg = self.load(example)
        self.assertEqual([s.number for s in cfg.slots], [1, 2, 3, 4, 5])
        self.assertEqual([w.type for w in cfg.slots[1].widgets], ["gmail", "rates"])

    def test_widget_files_resolve_next_to_config(self):
        with self.assertLogs("timesgate.gmail", "WARNING"):
            cfg = self.load(MINIMAL.replace('"text"', '"gmail"'))
        g = cfg.slots[0].widgets[0]
        self.assertEqual(g.token_path.name, "token.json")
        self.assertEqual(g.token_path.parent, g.root)

    def test_errors(self):
        cases = {
            "unknown widget type": MINIMAL.replace('"text"', '"nope"'),
            "defined twice": MINIMAL + "\n[[screen]]\nslot = 3\nwidgets = [{ type = \"text\" }]\n",
            "slot must be 1-5": MINIMAL.replace("slot = 3", "slot = 6"),
            "unknown option": MINIMAL.replace('{ type = "text" }', '{ type = "text", txt = "x" }'),
            "Expected 4 octets":MINIMAL.replace("192.168.1.60", "192.168.1"),
            "ip is required": MINIMAL.replace('ip = "192.168.1.60"', 'port = 9000'),
            "unknown key": MINIMAL.replace("[device]", "[theme]\ncolour = 1\n[device]"),
            "unknown section": MINIMAL + "\n[extra]\n",
            "non-empty list": MINIMAL.replace('[{ type = "text" }]', "[]"),
            "unknown level": MINIMAL + '\n[log]\nlevel = "LOUD"\n',
            "on_exit must be": MINIMAL.replace('ip = "192.168.1.60"', 'ip = "192.168.1.60"\non_exit = 581'),
            "cyrillic_font": MINIMAL.replace("[device]", '[theme]\ncyrillic_font = "no-such.ttf"\n[device]'),
            "text: unknown color": MINIMAL.replace("[device]", '[theme]\ntext = "white2"\n[device]'),
            "muted: ": MINIMAL.replace("[device]", '[theme]\nmuted = 123\n[device]'),
            "double brackets":'[device]\nip = "192.168.1.60"\n[screen]\nslot = 1\n',
        }
        for message, text in cases.items():
            with self.subTest(message), self.assertRaisesRegex(ConfigError, message):
                self.load(text)

    def test_missing_file(self):
        with self.assertRaisesRegex(ConfigError, "not found"):
            load("no-such-config.toml")


if __name__ == "__main__":
    unittest.main()

import json
import socket
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from timesgate import __main__ as main
from timesgate import config, web
from timesgate.runner import Runner, Slot
from timesgate.widgets import REGISTRY

MINIMAL = '[device]\nip = "192.168.1.60"\n\n[[screen]]\nslot = 3\nwidgets = [{ type = "text" }]\n'


class WebTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "config.toml"
        self.path.write_text(MINIMAL, encoding="utf-8")
        self.runner = SimpleNamespace(cfg=config.load(self.path), reload=MagicMock())
        self.server = web.make_server(self.runner, self.path, 0)  # 0: any free port
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def call(self, method, url, body=None, headers=None):
        data = None if body is None else json.dumps(body).encode()
        h = {} if body is None else {"Content-Type": "application/json"}
        req = urllib.request.Request(self.base + url, data, {**h, **(headers or {})}, method=method)
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_config_has_schema_of_every_widget(self):
        code, body = self.call("GET", "/api/config")
        self.assertEqual(code, 200)
        self.assertEqual(set(body["schema"]["widgets"]), set(REGISTRY))
        self.assertEqual(body["config"]["device"]["ip"], "192.168.1.60")

    def test_invalid_save_is_rejected_and_file_kept(self):
        raw = config.read(self.path)
        raw["device"]["ip"] = "1.2.3"
        code, body = self.call("PUT", "/api/config", raw)
        self.assertEqual(code, 400)
        self.assertIn("octets", body["error"])
        self.assertEqual(self.path.read_text(encoding="utf-8"), MINIMAL)
        self.runner.reload.assert_not_called()

    def test_save_writes_and_reloads(self):
        raw = config.read(self.path)
        raw["screen"][0]["widgets"][0]["text"] = "Привіт"
        raw["screen"][0]["widgets"][0]["retry"] = None  # left empty in the UI: dropped, TOML has no null
        self.assertEqual(self.call("PUT", "/api/config", raw)[0], 200)
        saved = config.read(self.path)
        self.assertEqual(saved["screen"][0]["widgets"][0], {"type": "text", "text": "Привіт"})
        self.assertTrue(self.path.with_suffix(".toml.bak").exists())
        self.runner.reload.assert_called_once()

    def test_other_sites_are_refused(self):
        self.assertEqual(self.call("GET", "/api/status", headers={"Host": "evil.example"})[0], 403)
        req = urllib.request.Request(self.base + "/api/config", b"{}", {"Content-Type": "text/plain"}, method="PUT")
        with self.assertRaises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(req, timeout=10)
        self.assertEqual(e.exception.code, 403)

    def test_bad_json_is_400(self):
        req = urllib.request.Request(self.base + "/api/preview", b"{nope", {"Content-Type": "application/json"},
                                     method="POST")
        with self.assertRaises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(req, timeout=10)
        self.assertEqual(e.exception.code, 400)

    def test_port_of_another_program_fails_loudly(self):
        with socket.socket() as other:  # bound, not timesgate: must not be mistaken for a running copy
            other.bind(("127.0.0.1", 0))
            cfg = SimpleNamespace(ui={"enabled": True, "port": other.getsockname()[1]})
            with self.assertRaises(SystemExit), self.assertLogs(level="CRITICAL"):
                main.serve(cfg, self.path)

    def test_autostart_command_runs_this_copy(self):
        cmd = web.autostart_command(self.path)
        self.assertIn("pythonw.exe", cmd)
        self.assertIn(str(web.LAUNCHER), cmd)
        self.assertTrue(cmd.endswith(f'-c "{self.path.resolve()}"'))


class RunnerTest(unittest.TestCase):
    def cfg(self):
        widget = MagicMock(every=3600, align=False, retry=None, speed=100)
        widget.frames.return_value = None
        return SimpleNamespace(slots=[Slot(1, [widget])], device=MagicMock(), level="INFO")

    def test_reload_halts_old_device_without_on_exit(self):
        r, old, new = Runner(), self.cfg(), self.cfg()
        old.device._last_id, new.device._last_id = 1_700_000_004, 0  # old burst used PicIDs up to ...004
        r.start(old)
        old_stop = r._stop
        r.reload(new)
        self.assertEqual(new.device._last_id, 1_700_000_004)  # next upload gets a higher PicID
        old.device.halt.assert_called_once()
        old.device.close.assert_not_called()
        self.assertTrue(old_stop.is_set())
        self.assertIs(r.cfg, new)
        r.stop()
        new.device.close.assert_called_once()  # on_exit only on a real stop
        self.assertTrue(r.done.is_set())


if __name__ == "__main__":
    unittest.main()

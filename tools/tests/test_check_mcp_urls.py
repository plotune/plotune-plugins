import json
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

import check_mcp_urls as cmu  # noqa: E402

REPO_ROOT = TOOLS.parent


def write_mcp(root: Path, rel: str, servers: dict, plugin="demo"):
    p = root / "plugins" / plugin / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"mcpServers": servers}), encoding="utf-8")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        code = {"/ok": 200, "/auth": 401, "/missing": 404, "/gone": 410, "/boom": 500}.get(self.path, 404)
        self.send_response(code)
        self.end_headers()

    do_POST = do_HEAD = do_GET

    def log_message(self, *args):
        pass


class CollectTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def test_collects_from_root_mcp_json_and_mcp_dir(self):
        write_mcp(self.root, ".mcp.json", {"a": {"type": "http", "url": "https://a.example/mcp"}})
        write_mcp(self.root, "mcp/x.mcp.json", {"b": {"url": "https://b.example/mcp"}})
        urls = sorted(e.url for e in cmu.collect_urls(self.root))
        self.assertEqual(urls, ["https://a.example/mcp", "https://b.example/mcp"])

    def test_collects_cursor_mcp_json_at_plugin_root(self):
        write_mcp(self.root, "mcp.json", {"c": {"url": "https://c.example/mcp"}})
        self.assertEqual([e.url for e in cmu.collect_urls(self.root)], ["https://c.example/mcp"])

    def test_skips_placeholders_and_stdio_servers(self):
        write_mcp(self.root, ".mcp.json", {
            "user": {"type": "http", "url": "${user_config.nexus_mcp_url}"},
            "local": {"command": "npx", "args": ["x"]}})
        self.assertEqual(cmu.collect_urls(self.root), [])

    def test_malformed_json_does_not_raise(self):
        p = self.root / "plugins/demo/.mcp.json"
        p.parent.mkdir(parents=True)
        p.write_text("{nope", encoding="utf-8")
        errs = cmu.check(self.root, fetch=lambda url: 200)
        self.assertTrue(any(".mcp.json" in e for e in errs))


class CheckTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        write_mcp(self.root, ".mcp.json", {"s": {"type": "http", "url": "https://s.example/mcp"}})

    def test_alive_statuses_pass(self):
        for status in (200, 400, 401, 403, 405, 500):
            self.assertEqual(cmu.check(self.root, fetch=lambda url, s=status: s), [], status)

    def test_404_and_410_fail(self):
        for status in (404, 410):
            errs = cmu.check(self.root, fetch=lambda url, s=status: s)
            self.assertTrue(any("https://s.example/mcp" in e and str(status) in e for e in errs))

    def test_connection_failure_fails(self):
        errs = cmu.check(self.root, fetch=lambda url: None)
        self.assertTrue(any("unreachable" in e for e in errs))

    def test_plain_http_to_remote_host_fails_without_fetching(self):
        write_mcp(self.root, ".mcp.json", {"s": {"type": "http", "url": "http://remote.example/mcp"}})
        called = []
        errs = cmu.check(self.root, fetch=lambda url: called.append(url) or 200)
        self.assertTrue(any("https" in e for e in errs))

    def test_plain_http_to_loopback_is_allowed(self):
        write_mcp(self.root, ".mcp.json", {"s": {"type": "http", "url": "http://127.0.0.1:1/mcp"}})
        self.assertEqual(cmu.check(self.root, fetch=lambda url: 200), [])

    def test_invalid_url_is_reported(self):
        write_mcp(self.root, ".mcp.json", {"s": {"type": "http", "url": "not a url"}})
        self.assertTrue(cmu.check(self.root, fetch=lambda url: 200))

    def test_real_repo_urls_are_wellformed(self):
        # network-free: every declared URL must at least be https and well-formed
        self.assertEqual(cmu.check(REPO_ROOT, fetch=lambda url: 200), [])


class HttpStatusTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), Handler)
        cls.port = cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def url(self, path):
        return f"http://127.0.0.1:{self.port}{path}"

    def test_returns_real_status_codes_including_errors(self):
        self.assertEqual(cmu.http_status(self.url("/ok")), 200)
        self.assertEqual(cmu.http_status(self.url("/auth")), 401)
        self.assertEqual(cmu.http_status(self.url("/missing")), 404)
        self.assertEqual(cmu.http_status(self.url("/gone")), 410)
        self.assertEqual(cmu.http_status(self.url("/boom")), 500)

    def test_unreachable_returns_none(self):
        self.assertIsNone(cmu.http_status("http://127.0.0.1:1/mcp", timeout=2))


if __name__ == "__main__":
    unittest.main()

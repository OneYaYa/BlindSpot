from __future__ import annotations

import json
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

import server


class WebHostingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        web_root = Path(self.temporary.name)
        (web_root / "index.html").write_text("<!doctype html><title>BlindSpot Web</title>", encoding="utf-8")
        (web_root / "index.wasm").write_bytes(b"\x00asm")
        settings = server.Settings(
            api_key="test-key",
            base_url="https://api.openai.com/v1",
            model="test-model",
            reasoning_effort="low",
            host="127.0.0.1",
            port=0,
        )
        self.relay = server.create_server(settings)
        self.relay.web_root = web_root.resolve()  # type: ignore[attr-defined]
        self.thread = threading.Thread(target=self.relay.serve_forever, daemon=True)
        self.thread.start()
        self.origin = f"http://127.0.0.1:{self.relay.server_address[1]}"

    def tearDown(self) -> None:
        self.relay.shutdown()
        self.relay.server_close()
        self.thread.join(timeout=3)
        self.temporary.cleanup()

    def test_root_serves_web_export_and_api_health_remains_available(self) -> None:
        with urllib.request.urlopen(f"{self.origin}/", timeout=3) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers.get_content_type(), "text/html")
            self.assertIn("BlindSpot Web", response.read().decode("utf-8"))
        with urllib.request.urlopen(f"{self.origin}/index.wasm", timeout=3) as response:
            self.assertEqual(response.headers.get_content_type(), "application/wasm")
        with urllib.request.urlopen(f"{self.origin}/api/health", timeout=3) as response:
            payload = json.loads(response.read().decode("utf-8"))
            self.assertTrue(payload["ok"])
            self.assertTrue(payload["configured"])

    def test_static_path_traversal_is_rejected(self) -> None:
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(f"{self.origin}/%2e%2e/server.py", timeout=3)
        self.assertEqual(caught.exception.code, 404)

    def test_same_origin_preflight_is_allowed_but_foreign_origin_is_rejected(self) -> None:
        request = urllib.request.Request(
            f"{self.origin}/api/npc/decide",
            method="OPTIONS",
            headers={"Origin": self.origin, "Access-Control-Request-Method": "POST"},
        )
        with urllib.request.urlopen(request, timeout=3) as response:
            self.assertEqual(response.status, 204)
            self.assertEqual(response.headers["Access-Control-Allow-Origin"], self.origin)

        request = urllib.request.Request(
            f"{self.origin}/api/npc/decide",
            method="OPTIONS",
            headers={"Origin": "https://example.invalid", "Access-Control-Request-Method": "POST"},
        )
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request, timeout=3)
        self.assertEqual(caught.exception.code, 403)


if __name__ == "__main__":
    unittest.main()

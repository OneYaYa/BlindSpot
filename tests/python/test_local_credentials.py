from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request

import local_credentials
import server


@unittest.skipUnless(os.name == "nt", "Windows DPAPI is required")
class LocalCredentialTests(unittest.TestCase):
    def test_dpapi_round_trip_never_writes_plaintext_key(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "online_ai.json"
            key = "sk-player-test-credential-123456"
            local_credentials.save_online_config(key, model="gpt-5.6-luna", path=path)
            raw = path.read_text(encoding="utf-8")
            payload = json.loads(raw)
            self.assertNotIn(key, raw)
            self.assertIn("api_key_dpapi", payload)
            self.assertEqual(local_credentials.load_online_config(path=path)["api_key"], key)

    def test_delete_removes_player_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "online_ai.json"
            local_credentials.save_online_config("sk-player-test-credential-123456", path=path)
            self.assertTrue(local_credentials.delete_online_config(path=path))
            self.assertFalse(path.exists())
            self.assertFalse(local_credentials.delete_online_config(path=path))

    def test_validation_rejects_insecure_remote_url(self) -> None:
        with self.assertRaises(ValueError):
            local_credentials.validate_online_config(
                "sk-player-test-credential-123456", "http://example.com/v1", "gpt-5.6-luna", "low"
            )

    def test_server_uses_player_config_without_environment_key(self) -> None:
        player_config = {
            "api_key": "sk-local-player-key",
            "base_url": "https://api.openai.com/v1",
            "model": "gpt-5.6-luna",
            "reasoning_effort": "medium",
        }
        with patch.dict(os.environ, {}, clear=True), patch.object(server, "_configuration_directories", return_value=[]), patch.object(
            server, "load_online_config", return_value=player_config
        ):
            settings = server.load_settings()
        self.assertEqual(settings.api_key, player_config["api_key"])
        self.assertEqual(settings.model, player_config["model"])
        self.assertEqual(settings.reasoning_effort, "medium")

    def test_environment_key_overrides_player_config(self) -> None:
        player_config = {
            "api_key": "sk-local-player-key",
            "base_url": "https://local.invalid/v1",
            "model": "local-model",
            "reasoning_effort": "medium",
        }
        environment = {
            "OPENAI_API_KEY": "sk-environment-key",
            "OPENAI_BASE_URL": "https://api.openai.com/v1",
            "OPENAI_MODEL": "environment-model",
            "OPENAI_REASONING_EFFORT": "low",
        }
        with patch.dict(os.environ, environment, clear=True), patch.object(server, "_configuration_directories", return_value=[]), patch.object(
            server, "load_online_config", return_value=player_config
        ):
            settings = server.load_settings()
        self.assertEqual(settings.api_key, environment["OPENAI_API_KEY"])
        self.assertEqual(settings.model, environment["OPENAI_MODEL"])

    def test_loopback_setup_page_saves_and_deletes_encrypted_player_key(self) -> None:
        isolated_environment = {
            "OPENAI_API_KEY": "",
            "LLM_API_KEY": "",
            "OPENAI_BASE_URL": "",
            "LLM_BASE_URL": "",
            "OPENAI_MODEL": "",
            "LLM_MODEL": "",
            "OPENAI_REASONING_EFFORT": "",
        }
        with tempfile.TemporaryDirectory() as temporary, patch.dict(
            os.environ, {**isolated_environment, "LOCALAPPDATA": temporary}, clear=False
        ), patch.object(server, "_configuration_directories", return_value=[]):
            settings = server.Settings("", "https://api.openai.com/v1", "gpt-5.6-luna", "low", "127.0.0.1", 0)
            relay = server.create_server(settings)
            thread = threading.Thread(target=relay.serve_forever, daemon=True)
            thread.start()
            port = relay.server_address[1]
            origin = f"http://127.0.0.1:{port}"
            try:
                with urllib.request.urlopen(f"{origin}/setup", timeout=3) as response:
                    self.assertIn("API Key", response.read().decode("utf-8"))
                body = json.dumps(
                    {
                        "action": "save",
                        "api_key": "sk-loopback-player-credential",
                        "base_url": "https://api.openai.com/v1",
                        "model": "gpt-5.6-luna",
                        "reasoning_effort": "low",
                    }
                ).encode("utf-8")
                request = urllib.request.Request(
                    f"{origin}/api/local-config",
                    data=body,
                    headers={"Content-Type": "application/json", "Origin": origin},
                )
                with urllib.request.urlopen(request, timeout=3) as response:
                    result = json.loads(response.read().decode("utf-8"))
                self.assertTrue(result["configured"])
                encrypted = local_credentials.configuration_path().read_text(encoding="utf-8")
                self.assertNotIn("sk-loopback-player-credential", encrypted)

                delete_request = urllib.request.Request(
                    f"{origin}/api/local-config",
                    data=json.dumps({"action": "delete"}).encode("utf-8"),
                    headers={"Content-Type": "application/json", "Origin": origin},
                )
                with urllib.request.urlopen(delete_request, timeout=3) as response:
                    deleted = json.loads(response.read().decode("utf-8"))
                self.assertFalse(deleted["player_configured"])
                self.assertFalse(local_credentials.configuration_path().exists())
            finally:
                relay.shutdown()
                relay.server_close()
                thread.join(timeout=3)


if __name__ == "__main__":
    unittest.main()

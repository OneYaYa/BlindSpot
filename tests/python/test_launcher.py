from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LAUNCHER_PATH = PROJECT_ROOT / "packaging" / "launcher.py"
SPEC = importlib.util.spec_from_file_location("blindspot_packaging_launcher", LAUNCHER_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Could not load the packaged launcher module")
launcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(launcher)


class _FakeGameProcess:
    def wait(self) -> int:
        return 0


class LauncherTests(unittest.TestCase):
    def test_configured_relay_is_announced_and_game_receives_launch_marker(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle_dir = Path(temporary)
            runtime_dir = bundle_dir / "_runtime"
            runtime_dir.mkdir()
            (runtime_dir / "BlindspotGame.exe").touch()
            (runtime_dir / "BlindspotGame.pck").touch()
            messages: list[tuple[str, bool]] = []
            popen_calls: list[tuple[list[str], dict[str, object]]] = []

            def fake_message(message: str, *, error: bool = False) -> None:
                messages.append((message, error))

            def fake_popen(arguments: list[str], **kwargs: object) -> _FakeGameProcess:
                popen_calls.append((arguments, kwargs))
                return _FakeGameProcess()

            with (
                mock.patch.object(launcher, "_hide_console_window"),
                mock.patch.object(launcher, "_bundle_dir", return_value=bundle_dir),
                mock.patch.object(
                    launcher,
                    "_start_relay",
                    return_value=(None, {"configured": True, "model": "test-model"}),
                ),
                mock.patch.object(launcher, "_show_message", side_effect=fake_message),
                mock.patch.object(launcher.subprocess, "Popen", side_effect=fake_popen),
                mock.patch.object(launcher, "_stop_owned_process"),
                mock.patch.dict(os.environ, {"BLINDSPOT_SMOKE_QUIT_AFTER": ""}),
            ):
                self.assertEqual(launcher.main(), 0)

            self.assertEqual(len(messages), 1)
            self.assertIn("已检测到 API Key 配置", messages[0][0])
            self.assertIn("test-model", messages[0][0])
            self.assertFalse(messages[0][1])
            self.assertEqual(len(popen_calls), 1)
            child_environment = popen_calls[0][1]["env"]
            self.assertIsInstance(child_environment, dict)
            self.assertEqual(child_environment["BLINDSPOT_LAUNCHED_BY_LAUNCHER"], "1")


if __name__ == "__main__":
    unittest.main()

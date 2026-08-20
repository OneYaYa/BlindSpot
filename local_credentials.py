"""Windows-local encrypted provider configuration for Blindspot Relay."""

from __future__ import annotations

import base64
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


CONFIG_SCHEMA_VERSION = 1
DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-5.6-luna"
DEFAULT_REASONING_EFFORT = "low"
VALID_REASONING_EFFORTS = {"none", "minimal", "low", "medium", "high", "xhigh", "max"}
CRYPTPROTECT_UI_FORBIDDEN = 0x1


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]


def configuration_path(config_root: Path | None = None) -> Path:
    if config_root is not None:
        root = Path(config_root)
    else:
        local_app_data = os.getenv("LOCALAPPDATA", "").strip()
        if not local_app_data:
            root = Path.home() / ".config"
        else:
            root = Path(local_app_data)
    return root / "BlindspotRelay" / "online_ai.json"


def _blob(data: bytes) -> tuple[_DataBlob, Any]:
    buffer = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
    return _DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte))), buffer


def _protect_secret(secret: str) -> str:
    if os.name != "nt":
        raise RuntimeError("Local API Key storage is only supported on Windows")
    raw_blob, raw_buffer = _blob(secret.encode("utf-8"))
    protected_blob = _DataBlob()
    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    if not crypt32.CryptProtectData(
        ctypes.byref(raw_blob),
        "Blindspot Relay online AI credential",
        None,
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(protected_blob),
    ):
        raise OSError(ctypes.get_last_error(), "Windows could not encrypt the API Key")
    try:
        protected = ctypes.string_at(protected_blob.pbData, protected_blob.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(protected_blob.pbData)
        del raw_buffer
    return base64.b64encode(protected).decode("ascii")


def _unprotect_secret(encoded: str) -> str:
    if os.name != "nt":
        raise RuntimeError("Local API Key storage is only supported on Windows")
    protected = base64.b64decode(encoded, validate=True)
    protected_blob, protected_buffer = _blob(protected)
    raw_blob = _DataBlob()
    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    if not crypt32.CryptUnprotectData(
        ctypes.byref(protected_blob),
        None,
        None,
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(raw_blob),
    ):
        raise OSError(ctypes.get_last_error(), "Windows could not decrypt the API Key")
    try:
        raw = ctypes.string_at(raw_blob.pbData, raw_blob.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(raw_blob.pbData)
        del protected_buffer
    return raw.decode("utf-8")


def validate_online_config(api_key: str, base_url: str, model: str, reasoning_effort: str) -> dict[str, str]:
    api_key = api_key.strip()
    base_url = base_url.strip().rstrip("/")
    model = model.strip()
    reasoning_effort = reasoning_effort.strip().lower()
    if len(api_key) < 8 or any(character.isspace() for character in api_key):
        raise ValueError("API Key 不能为空，也不能包含空格或换行。")
    parsed = urlparse(base_url)
    is_local_http = parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost"}
    if parsed.scheme != "https" and not is_local_http:
        raise ValueError("API 地址必须使用 HTTPS；仅本机 127.0.0.1/localhost 可以使用 HTTP。")
    if not parsed.netloc:
        raise ValueError("API 地址无效。")
    if not model or any(character.isspace() for character in model):
        raise ValueError("模型名称不能为空，也不能包含空格。")
    if reasoning_effort not in VALID_REASONING_EFFORTS:
        raise ValueError("推理强度无效。")
    return {
        "api_key": api_key,
        "base_url": base_url,
        "model": model,
        "reasoning_effort": reasoning_effort,
    }


def save_online_config(
    api_key: str,
    base_url: str = DEFAULT_BASE_URL,
    model: str = DEFAULT_MODEL,
    reasoning_effort: str = DEFAULT_REASONING_EFFORT,
    *,
    path: Path | None = None,
) -> Path:
    values = validate_online_config(api_key, base_url, model, reasoning_effort)
    target = Path(path) if path is not None else configuration_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": CONFIG_SCHEMA_VERSION,
        "provider": "openai",
        "api_key_dpapi": _protect_secret(values["api_key"]),
        "base_url": values["base_url"],
        "model": values["model"],
        "reasoning_effort": values["reasoning_effort"],
    }
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.chmod(temporary, 0o600)
    os.replace(temporary, target)
    return target


def load_online_config(*, path: Path | None = None) -> dict[str, str]:
    target = Path(path) if path is not None else configuration_path()
    if os.name != "nt" or not target.is_file():
        return {}
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or int(payload.get("schema_version", 0)) != CONFIG_SCHEMA_VERSION:
            return {}
        api_key = _unprotect_secret(str(payload.get("api_key_dpapi", "")))
        return validate_online_config(
            api_key,
            str(payload.get("base_url", DEFAULT_BASE_URL)),
            str(payload.get("model", DEFAULT_MODEL)),
            str(payload.get("reasoning_effort", DEFAULT_REASONING_EFFORT)),
        )
    except (OSError, ValueError, UnicodeError, json.JSONDecodeError):
        return {}


def delete_online_config(*, path: Path | None = None) -> bool:
    target = Path(path) if path is not None else configuration_path()
    if not target.exists():
        return False
    target.unlink()
    return True

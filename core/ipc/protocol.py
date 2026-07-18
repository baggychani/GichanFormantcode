"""Line-delimited JSON IPC envelopes for the GichanFormant sidecar.

Transport is NDJSON over stdio (one JSON object per line). Request/response
pairs share an ``id``. Server-push notifications use ``event`` without ``id``.
"""

from __future__ import annotations

import json
from typing import Any, Mapping

PROTOCOL_VERSION = 1
MAX_MESSAGE_BYTES = 32 * 1024 * 1024

# Methods handled by ApplicationService (plus host-only health/shutdown).
COMMANDS: dict[str, dict[str, Any]] = {
    "ping": {"params": {}},
    "health": {"params": {}},
    "shutdown": {"params": {}},
    "get_state": {"params": {}},
    "snapshot": {"params": {}},
    "get_vowel_analysis": {
        "params": {"index": "int"},
        "required": ["index"],
    },
    "set_analysis_settings": {
        "params": {
            "settings": "object",
        },
        "required": ["settings"],
    },
    "load_files": {
        "params": {
            "paths": "string[]",
        },
        "required": ["paths"],
    },
    "remove_file": {
        "params": {
            "index": "int",
        },
        "required": ["index"],
    },
    "set_current_index": {
        "params": {
            "index": "int",
        },
        "required": ["index"],
    },
    "reset": {"params": {}},
    "save_project": {
        "params": {
            "path": "string",
        },
        "required": ["path"],
    },
    "load_project": {
        "params": {
            "path": "string",
        },
        "required": ["path"],
    },
    "export_combined_txt": {
        "params": {
            "path": "string",
        },
        "required": ["path"],
    },
    "open_single_plot": {"params": {}},
    "open_compare": {
        "params": {
            "source_groups": "int[][]",
            "normalization": "string|null",
        },
        "required": ["source_groups"],
    },
    "open_guide": {"params": {}},
    "request_preview": {"params": {"request_id": "int"}},
    "measure_distance": {
        "params": {
            "x1": "number",
            "y1": "number",
            "x2": "number",
            "y2": "number",
        },
        "required": ["x1", "y1", "x2", "y2"],
    },
    "export_interactive_preview": {
        "params": {
            "path": "string",
            "format": "string",
            "options": "interactive_options",
        },
        "required": ["path", "format", "options"],
    },
    "export_interactive_batch": {
        "params": {
            "directory": "string",
            "format": "string",
            "options": "interactive_options",
        },
        "required": ["directory", "format", "options"],
    },
    "update_interactive_session": {
        "params": {
            "options": "interactive_options",
        },
        "required": ["options"],
    },
    "render_interactive_preview": {
        "params": {
            "options": "interactive_options",
        },
        "required": ["options"],
    },
    "navigate_interactive_preview": {
        "params": {
            "index": "int",
            "options": "interactive_options",
        },
        "required": ["index", "options"],
    },
}

EVENTS: tuple[str, ...] = (
    "state_changed",
    "files_changed",
    "operation_progress",
    "project_saved",
    "project_loaded",
    "preview_ready",
    "preview_cleared",
    "preview_failed",
    "plot_session_changed",
    "window_requested",
    "operation_failed",
    "sidecar_ready",
    "sidecar_shutting_down",
)


class ProtocolError(ValueError):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }


def encode_request(
    method: str, params: Mapping[str, Any] | None = None, *, request_id: str
) -> str:
    return _dump(
        {
            "v": PROTOCOL_VERSION,
            "id": request_id,
            "method": method,
            "params": dict(params or {}),
        }
    )


def encode_response(request_id: str, result: Any) -> str:
    return _dump({"v": PROTOCOL_VERSION, "id": request_id, "result": result})


def encode_error(
    request_id: str | None,
    code: str,
    message: str,
    details: Mapping[str, Any] | None = None,
) -> str:
    payload: dict[str, Any] = {
        "v": PROTOCOL_VERSION,
        "error": {
            "code": code,
            "message": message,
            "details": dict(details or {}),
        },
    }
    if request_id is not None:
        payload["id"] = request_id
    return _dump(payload)


def encode_event(name: str, payload: Mapping[str, Any] | None = None) -> str:
    return _dump(
        {
            "v": PROTOCOL_VERSION,
            "event": name,
            "payload": dict(payload or {}),
        }
    )


def peek_request_id(raw: str | bytes) -> str | None:
    """Best-effort extract of ``id`` when full decode fails."""
    if isinstance(raw, bytes):
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("utf-8", errors="surrogatepass")
    else:
        text = raw
    try:
        data = json.loads(text.strip())
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    request_id = data.get("id")
    return str(request_id) if isinstance(request_id, str) else None


def decode_line(raw: str | bytes) -> dict[str, Any]:
    if isinstance(raw, bytes):
        if len(raw) > MAX_MESSAGE_BYTES:
            raise ProtocolError(
                "message_too_large",
                f"message exceeds {MAX_MESSAGE_BYTES} bytes",
                {"size": len(raw)},
            )
        text = raw.decode("utf-8")
    else:
        text = raw
        # Surrogate-laden strings (locale-misdecoded UTF-8) must not crash size
        # checks before we can surface a protocol error with the request id.
        try:
            encoded_size = len(text.encode("utf-8"))
        except UnicodeEncodeError:
            encoded_size = len(text.encode("utf-8", errors="surrogatepass"))
        if encoded_size > MAX_MESSAGE_BYTES:
            raise ProtocolError(
                "message_too_large",
                f"message exceeds {MAX_MESSAGE_BYTES} bytes",
            )
    text = text.strip()
    if not text:
        raise ProtocolError("empty_message", "empty IPC line")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProtocolError("invalid_json", str(exc)) from exc
    if not isinstance(data, dict):
        raise ProtocolError("invalid_envelope", "IPC message must be a JSON object")
    version = data.get("v", PROTOCOL_VERSION)
    if version != PROTOCOL_VERSION:
        raise ProtocolError(
            "unsupported_version",
            f"unsupported protocol version {version}",
            {"expected": PROTOCOL_VERSION},
        )
    return data


def validate_params(method: str, params: Mapping[str, Any] | None) -> dict[str, Any]:
    if method not in COMMANDS:
        raise ProtocolError(
            "unknown_method",
            f"unknown method {method!r}",
            {"method": method},
        )
    if params is not None and not isinstance(params, Mapping):
        raise ProtocolError(
            "invalid_params",
            "params must be a JSON object",
            {"expected": "object"},
        )
    spec = COMMANDS[method]
    raw = dict(params or {})
    required = spec.get("required", [])
    missing = [name for name in required if name not in raw]
    if missing:
        raise ProtocolError(
            "invalid_params",
            f"missing required params: {', '.join(missing)}",
            {"missing": missing},
        )
    expected = spec.get("params", {})
    for key, value in raw.items():
        if key not in expected:
            raise ProtocolError(
                "invalid_params",
                f"unexpected param {key!r} for {method}",
                {"param": key},
            )
        _check_type(method, key, expected[key], value)
    if method == "load_files":
        paths = raw.get("paths")
        if not paths:
            raise ProtocolError(
                "invalid_params",
                "load_files requires at least one path",
                {"param": "paths", "expected": "non-empty string[]"},
            )
        blank = [index for index, path in enumerate(paths) if not path.strip()]
        if blank:
            raise ProtocolError(
                "invalid_params",
                "load_files paths must not be blank",
                {"param": "paths", "blank_indices": blank},
            )
    return raw


def protocol_manifest() -> dict[str, Any]:
    """Serializable contract consumed by TypeScript and contract tests."""
    return {
        "protocol_version": PROTOCOL_VERSION,
        "transport": "ndjson-stdio",
        "max_message_bytes": MAX_MESSAGE_BYTES,
        "commands": COMMANDS,
        "events": list(EVENTS),
        "envelopes": {
            "request": ["v", "id", "method", "params"],
            "response": ["v", "id", "result"],
            "error": ["v", "id?", "error"],
            "event": ["v", "event", "payload"],
        },
        "application_state": {
            "analysis": [
                "type",
                "f1_scale",
                "f2_scale",
                "origin",
                "use_bark_units",
                "outlier_mode",
                "outlier_scope",
                "normalization",
            ],
            "current_index": "int",
            "current_vowels": "string[]",
            "design_defaults": "object",
            "plot_session": "object",
            "sources": [
                "index",
                "name",
                "path",
                "has_f3",
                "is_combined",
                "is_pre_lobanov",
            ],
            "capabilities": ["can_plot", "can_compare", "can_save_project"],
        },
    }


def _check_type(method: str, key: str, expected: str, value: Any) -> None:
    ok = False
    if expected == "object":
        ok = isinstance(value, dict)
    elif expected == "number":
        ok = isinstance(value, (int, float)) and not isinstance(value, bool)
    elif expected == "string":
        ok = isinstance(value, str)
    elif expected == "string|null":
        ok = value is None or isinstance(value, str)
    elif expected == "int":
        ok = isinstance(value, int) and not isinstance(value, bool)
    elif expected == "string[]":
        ok = isinstance(value, list) and all(isinstance(item, str) for item in value)
    elif expected == "int[][]":
        ok = (
            isinstance(value, list)
            and all(isinstance(group, list) for group in value)
            and all(
                isinstance(item, int) and not isinstance(item, bool)
                for group in value
                for item in group
            )
        )
    elif expected == "interactive_options":
        from core.interactive_plot_state import (
            InteractiveOptionsError,
            validate_interactive_options,
        )

        try:
            validate_interactive_options(value)
            ok = True
        except InteractiveOptionsError as exc:
            raise ProtocolError(
                "invalid_params",
                f"param {key!r} for {method}: {exc}",
                {"param": key, "expected": expected},
            ) from exc
    else:
        raise ProtocolError(
            "internal_error",
            f"unknown param type {expected!r}",
            {"method": method, "param": key},
        )
    if not ok:
        raise ProtocolError(
            "invalid_params",
            f"param {key!r} for {method} must be {expected}",
            {"param": key, "expected": expected},
        )


def _dump(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

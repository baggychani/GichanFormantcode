from __future__ import annotations

import json

from core.ipc.protocol import (
    COMMANDS,
    EVENTS,
    PROTOCOL_VERSION,
    ProtocolError,
    decode_line,
    encode_error,
    encode_event,
    encode_request,
    encode_response,
    peek_request_id,
    protocol_manifest,
    validate_params,
)


def test_encode_decode_roundtrip():
    line = encode_request("load_files", {"paths": ["a.txt"]}, request_id="1")
    message = decode_line(line)
    assert message["v"] == PROTOCOL_VERSION
    assert message["method"] == "load_files"
    assert message["params"]["paths"] == ["a.txt"]


def test_decode_line_accepts_korean_paths_as_utf8_bytes():
    line = encode_request(
        "load_files",
        {"paths": [r"C:\Users\테스트\file.txt"]},
        request_id="ko-1",
    )
    message = decode_line(line.encode("utf-8"))
    assert message["params"]["paths"] == [r"C:\Users\테스트\file.txt"]


def test_decode_line_size_check_tolerates_surrogates():
    # Locale-misdecoded UTF-8 can produce surrogate code points on Windows.
    raw = '{"v":1,"id":"1","method":"ping","params":{},"x":"' + "\udced" + '"}'
    message = decode_line(raw)
    assert message["id"] == "1"


def test_decode_line_preserves_unicode_escape_path_as_utf8_bytes():
    korean_leaf = "\\ud14c\\uc2a4\\ud2b8"
    path = rf"C:\\Users\\{korean_leaf}\\file.txt"
    line = encode_request("load_files", {"paths": [path]}, request_id="ko-escaped")
    assert decode_line(line.encode("utf-8"))["params"]["paths"] == [path]


def test_peek_request_id_recovers_id_from_valid_json():
    line = encode_request("health", {}, request_id="abc")
    assert peek_request_id(line) == "abc"
    assert peek_request_id(b"not-json") is None


def test_validate_params_rejects_unknown_and_bad_types():
    validate_params("reset", {})
    try:
        validate_params("load_files", {"paths": [1]})
        assert False, "expected ProtocolError"
    except ProtocolError as exc:
        assert exc.code == "invalid_params"

    try:
        validate_params("nope", {})
        assert False, "expected ProtocolError"
    except ProtocolError as exc:
        assert exc.code == "unknown_method"


def test_error_and_event_envelopes():
    err = json.loads(encode_error("9", "boom", "failed", {"x": 1}))
    assert err["id"] == "9"
    assert err["error"]["code"] == "boom"
    event = json.loads(encode_event("state_changed", {"reason": "test"}))
    assert event["event"] == "state_changed"
    assert "id" not in event


def test_manifest_lists_all_commands_and_events():
    manifest = protocol_manifest()
    assert set(manifest["commands"]) == set(COMMANDS)
    assert manifest["events"] == list(EVENTS)
    assert json.loads(encode_response("1", {"ok": True}))["result"]["ok"] is True

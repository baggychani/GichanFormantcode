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
    protocol_manifest,
    validate_params,
)


def test_encode_decode_roundtrip():
    line = encode_request("load_files", {"paths": ["a.txt"]}, request_id="1")
    message = decode_line(line)
    assert message["v"] == PROTOCOL_VERSION
    assert message["method"] == "load_files"
    assert message["params"]["paths"] == ["a.txt"]


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

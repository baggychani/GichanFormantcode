"""IPC protocol shared by the Python sidecar and future Tauri/React clients."""

from core.ipc.protocol import (
    PROTOCOL_VERSION,
    COMMANDS,
    EVENTS,
    MAX_MESSAGE_BYTES,
    decode_line,
    encode_error,
    encode_event,
    encode_request,
    encode_response,
    validate_params,
)

__all__ = [
    "PROTOCOL_VERSION",
    "COMMANDS",
    "EVENTS",
    "MAX_MESSAGE_BYTES",
    "decode_line",
    "encode_error",
    "encode_event",
    "encode_request",
    "encode_response",
    "validate_params",
]

# GichanFormant Working Rules

## MANDATORY: No Checkbox UI

- Never use checkbox controls in the application UI. Use a visible toggle switch
  with `role="switch"` and `aria-checked` for binary settings, including modal
  dialogs and export options. This is a shared project rule and must remain in
  this tracked file, not only in local ignored agent instructions.

## Text Encoding

- Store all source code, JSON, TOML, Markdown, and test fixtures as UTF-8.
- The desktop sidecar protocol is NDJSON encoded as UTF-8 bytes. Never rely on
  the Windows ANSI code page or the active terminal locale for this boundary.
- Keep Python sidecar standard input and output explicitly configured as UTF-8.
  Do not remove `PYTHONUTF8`, `PYTHONIOENCODING`, or the sidecar stdio setup
  without an equivalent end-to-end guarantee.

## Changes To IPC

- When changing sidecar request parsing or process spawning, add or update a
  regression test that sends a non-ASCII Windows path as UTF-8 bytes.
- Do not treat terminal display output as evidence of the underlying byte
  encoding. Use byte-level assertions or Unicode escape test data when the
  shell code page could alter pasted characters.
- Preserve a request id whenever a malformed request can still be identified,
  so the Rust caller fails promptly instead of waiting for its timeout.

//! NDJSON bridge to the Python analysis sidecar (`python -m sidecar`).

use std::collections::HashMap;
use std::io::{BufRead, BufReader, Write};
use std::path::PathBuf;
use std::process::{Child, ChildStderr, ChildStdin, ChildStdout, Command, Stdio};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::mpsc::{self, Receiver, Sender};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;

use serde_json::{json, Value};
use tauri::{AppHandle, Emitter, Manager};
use tauri_plugin_shell::{
    process::{CommandChild, CommandEvent},
    ShellExt,
};
use uuid::Uuid;

type PendingMap = HashMap<String, Sender<Result<Value, String>>>;
type PendingRequest = (
    String,
    Receiver<Result<Value, String>>,
    Arc<Mutex<PendingMap>>,
);

/// Incrementally split the sidecar's NDJSON stream.
///
/// `tauri-plugin-shell` delivers arbitrary stdout chunks, not logical lines.
/// Parsing each chunk as JSON loses messages whenever a JSON document is split
/// across chunks (or several documents arrive together), which in turn leaves
/// pending IPC calls waiting until their timeout.
#[derive(Default)]
struct NdjsonChunkBuffer {
    bytes: Vec<u8>,
}

impl NdjsonChunkBuffer {
    fn push(&mut self, chunk: &[u8]) -> Vec<String> {
        self.bytes.extend_from_slice(chunk);
        let mut lines = Vec::new();
        while let Some(newline) = self.bytes.iter().position(|byte| *byte == b'\n') {
            let mut line: Vec<u8> = self.bytes.drain(..=newline).collect();
            line.pop(); // newline
            if line.last() == Some(&b'\r') {
                line.pop();
            }
            match String::from_utf8(line) {
                Ok(line) => lines.push(line),
                Err(error) => lines.push(format!("{{\"event\":\"sidecar-log\",\"payload\":{{\"message\":\"invalid utf-8 stdout: {error}\"}}}}")),
            }
        }
        // A malformed sidecar must not grow desktop memory without bound.
        if self.bytes.len() > 8 * 1024 * 1024 {
            self.bytes.clear();
        }
        lines
    }
}

// Starting the desktop sidecar imports Python, PySide6, matplotlib, and the
// application service.  On a first run (or a slower Windows machine) that can
// exceed the old eight-second health check even though the child is healthy.
const SIDECAR_STARTUP_TIMEOUT: Duration = Duration::from_secs(45);

pub struct SidecarState {
    inner: Mutex<SidecarInner>,
}

struct SidecarInner {
    process: Option<SidecarProcess>,
    pending: Arc<Mutex<PendingMap>>,
}

enum SidecarProcess {
    Development {
        child: Child,
        stdin: ChildStdin,
    },
    Bundled {
        child: CommandChild,
        running: Arc<AtomicBool>,
    },
}

impl SidecarState {
    pub fn new() -> Self {
        Self {
            inner: Mutex::new(SidecarInner {
                process: None,
                pending: Arc::new(Mutex::new(HashMap::new())),
            }),
        }
    }

    pub(crate) fn stop(&self) -> Result<(), String> {
        let mut inner = self.inner.lock().map_err(|_| "sidecar lock poisoned")?;
        stop_inner(&mut inner)
    }
}

impl Drop for SidecarState {
    fn drop(&mut self) {
        if let Ok(inner) = self.inner.get_mut() {
            let _ = stop_inner(inner);
        }
    }
}

fn repo_root() -> Result<PathBuf, String> {
    let manifest = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    manifest
        .join("../..")
        .canonicalize()
        .map_err(|err| format!("failed to resolve repo root: {err}"))
}

type SpawnedSidecar = (Child, ChildStdin, ChildStdout, ChildStderr);
const BUNDLED_SIDECAR_NAME: &str = "gichan-formant-sidecar";

fn spawn_development_sidecar() -> Result<SpawnedSidecar, String> {
    let root = repo_root()?;
    let mut command = if let Ok(custom) = std::env::var("GICHAN_SIDECAR_CMD") {
        let mut parts = custom.split_whitespace();
        let program = parts
            .next()
            .ok_or_else(|| "GICHAN_SIDECAR_CMD is empty".to_string())?;
        let mut cmd = Command::new(program);
        cmd.args(parts);
        cmd
    } else {
        let mut cmd = Command::new("uv");
        cmd.args(["run", "python", "-m", "sidecar", "--desktop"]);
        cmd
    };

    command
        .current_dir(&root)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .env("PYTHONUNBUFFERED", "1");

    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        command.creation_flags(CREATE_NO_WINDOW);
    }

    let mut child = command
        .spawn()
        .map_err(|err| format!("failed to start sidecar (is uv installed?): {err}"))?;
    let stdin = child
        .stdin
        .take()
        .ok_or_else(|| "sidecar stdin missing".to_string())?;
    let stdout = child
        .stdout
        .take()
        .ok_or_else(|| "sidecar stdout missing".to_string())?;
    let stderr = child
        .stderr
        .take()
        .ok_or_else(|| "sidecar stderr missing".to_string())?;
    Ok((child, stdin, stdout, stderr))
}

fn use_development_sidecar() -> bool {
    cfg!(debug_assertions) || std::env::var_os("GICHAN_SIDECAR_CMD").is_some()
}

fn start_stdout_reader(app: AppHandle, stdout: ChildStdout, pending: Arc<Mutex<PendingMap>>) {
    thread::spawn(move || {
        let reader = BufReader::new(stdout);
        for line in reader.lines() {
            let Ok(line) = line else { break };
            handle_sidecar_output(&app, &line, &pending);
        }
        fail_pending(&pending, "sidecar output closed");
        let _ = app.emit("sidecar-log", "sidecar stdout closed");
    });
}

fn handle_sidecar_output(app: &AppHandle, line: &str, pending: &Arc<Mutex<PendingMap>>) {
    let line = line.trim();
    if line.is_empty() {
        return;
    }
    let Ok(message) = serde_json::from_str::<Value>(line) else {
        let _ = app.emit("sidecar-log", format!("invalid json: {line}"));
        return;
    };

    if let Some(event) = message.get("event").and_then(|value| value.as_str()) {
        let payload = message.get("payload").cloned().unwrap_or_else(|| json!({}));
        let _ = app.emit(
            "sidecar-event",
            json!({ "event": event, "payload": payload }),
        );
        return;
    }

    if let Some(id) = message.get("id").and_then(|value| value.as_str()) {
        let result = if let Some(error) = message.get("error") {
            Err(error.to_string())
        } else {
            Ok(message.get("result").cloned().unwrap_or(Value::Null))
        };
        if let Some(tx) = pending.lock().ok().and_then(|mut map| map.remove(id)) {
            let _ = tx.send(result);
        }
    }
}

fn fail_pending(pending: &Arc<Mutex<PendingMap>>, reason: &str) {
    if let Ok(mut map) = pending.lock() {
        for (_, sender) in map.drain() {
            let _ = sender.send(Err(reason.to_string()));
        }
    }
}

fn start_stderr_reader(app: AppHandle, stderr: ChildStderr) {
    thread::spawn(move || {
        for line in BufReader::new(stderr).lines() {
            match line {
                Ok(line) if !line.trim().is_empty() => {
                    let _ = app.emit("sidecar-log", line);
                }
                Ok(_) => {}
                Err(err) => {
                    let _ = app.emit("sidecar-log", format!("stderr read failed: {err}"));
                    break;
                }
            }
        }
    });
}

fn ensure_running(app: &AppHandle, state: &SidecarState) -> Result<(), String> {
    let mut inner = state.inner.lock().map_err(|_| "sidecar lock poisoned")?;
    if let Some(process) = inner.process.as_mut() {
        let running = match process {
            SidecarProcess::Development { child, .. } => {
                child.try_wait().map_err(|err| err.to_string())?.is_none()
            }
            SidecarProcess::Bundled { running, .. } => running.load(Ordering::Acquire),
        };
        if running {
            return Ok(());
        }
    }

    inner.process = None;
    let pending = Arc::new(Mutex::new(HashMap::new()));
    inner.pending = Arc::clone(&pending);
    if use_development_sidecar() {
        let (child, stdin, stdout, stderr) = spawn_development_sidecar()?;
        start_stdout_reader(app.clone(), stdout, pending);
        start_stderr_reader(app.clone(), stderr);
        inner.process = Some(SidecarProcess::Development { child, stdin });
    } else {
        let (mut events, child) = app
            .shell()
            .sidecar(BUNDLED_SIDECAR_NAME)
            .map_err(|err| format!("failed to resolve bundled sidecar: {err}"))?
            .arg("--desktop")
            .spawn()
            .map_err(|err| format!("failed to start bundled sidecar: {err}"))?;
        let running = Arc::new(AtomicBool::new(true));
        let reader_app = app.clone();
        let reader_pending = Arc::clone(&pending);
        let reader_running = Arc::clone(&running);
        tauri::async_runtime::spawn(async move {
            let mut stdout_buffer = NdjsonChunkBuffer::default();
            while let Some(event) = events.recv().await {
                match event {
                    CommandEvent::Stdout(bytes) => {
                        for line in stdout_buffer.push(&bytes) {
                            handle_sidecar_output(&reader_app, &line, &reader_pending);
                        }
                    }
                    CommandEvent::Stderr(bytes) => {
                        let line = String::from_utf8_lossy(&bytes).trim().to_string();
                        if !line.is_empty() {
                            let _ = reader_app.emit("sidecar-log", line);
                        }
                    }
                    CommandEvent::Error(error) => {
                        let _ = reader_app.emit("sidecar-log", format!("sidecar error: {error}"));
                    }
                    CommandEvent::Terminated(status) => {
                        let _ = reader_app.emit(
                            "sidecar-log",
                            format!("sidecar exited with code {:?}", status.code),
                        );
                    }
                    _ => {}
                }
            }
            reader_running.store(false, Ordering::Release);
            fail_pending(&reader_pending, "sidecar output closed");
        });
        inner.process = Some(SidecarProcess::Bundled { child, running });
    }
    Ok(())
}

fn send_request(
    state: &SidecarState,
    method: &str,
    params: Value,
) -> Result<PendingRequest, String> {
    let id = Uuid::new_v4().to_string();
    let (tx, rx) = mpsc::channel();
    let pending = {
        let mut inner = state.inner.lock().map_err(|_| "sidecar lock poisoned")?;
        let pending = Arc::clone(&inner.pending);
        pending
            .lock()
            .map_err(|_| "pending lock poisoned")?
            .insert(id.clone(), tx);

        let request = json!({
            "v": 1,
            "id": id,
            "method": method,
            "params": params,
        });
        let write_result = (|| {
            let payload = format!("{request}\n");
            match inner
                .process
                .as_mut()
                .ok_or_else(|| "sidecar is not running".to_string())?
            {
                SidecarProcess::Development { stdin, .. } => {
                    stdin
                        .write_all(payload.as_bytes())
                        .map_err(|err| format!("failed to write sidecar request: {err}"))?;
                    stdin
                        .flush()
                        .map_err(|err| format!("failed to flush sidecar request: {err}"))
                }
                SidecarProcess::Bundled { child, running } => {
                    if !running.load(Ordering::Acquire) {
                        return Err("bundled sidecar is not running".to_string());
                    }
                    child
                        .write(payload.as_bytes())
                        .map_err(|err| format!("failed to write bundled sidecar request: {err}"))
                }
            }
        })();
        if let Err(err) = write_result {
            if let Ok(mut map) = pending.lock() {
                map.remove(&id);
            }
            return Err(err);
        }
        pending
    };
    Ok((id, rx, pending))
}

fn call_sidecar(
    state: &SidecarState,
    method: &str,
    params: Value,
    timeout: Duration,
) -> Result<Value, String> {
    let (id, rx, pending) = send_request(state, method, params)?;
    match rx.recv_timeout(timeout) {
        Ok(Ok(value)) => Ok(value),
        Ok(Err(err)) => Err(err),
        Err(_) => {
            if let Ok(mut map) = pending.lock() {
                map.remove(&id);
            }
            Err(format!("timed out waiting for sidecar method '{method}'"))
        }
    }
}

fn timeout_for_method(method: &str) -> Duration {
    match method {
        "load_files" | "load_project" | "save_project" => Duration::from_secs(120),
        "open_single_plot" | "open_compare" | "open_guide" => Duration::from_secs(30),
        // Preparation crosses the Qt executor and the isolated renderer may
        // need a cold font-cache start. Keep this aligned with Python's
        // renderer watchdog so a request cannot become an orphaned preview.
        "render_interactive_preview" => Duration::from_secs(125),
        "ping" | "health" | "get_state" | "snapshot" => Duration::from_secs(8),
        _ => Duration::from_secs(15),
    }
}

fn is_idempotent_method(method: &str) -> bool {
    matches!(method, "ping" | "health" | "get_state" | "snapshot")
}

fn is_transport_error(error: &str) -> bool {
    error.contains("sidecar output closed")
        || error.contains("sidecar is not running")
        || error.contains("failed to write")
        || error.contains("timed out waiting")
}

fn call_with_recovery(
    app: &AppHandle,
    state: &SidecarState,
    method: &str,
    params: Value,
) -> Result<Value, String> {
    ensure_running(app, state)?;
    let timeout = timeout_for_method(method);
    match call_sidecar(state, method, params.clone(), timeout) {
        Ok(value) => Ok(value),
        Err(first_error) if is_idempotent_method(method) && is_transport_error(&first_error) => {
            state.stop()?;
            ensure_running(app, state)?;
            call_sidecar(state, method, params, timeout).map_err(|retry_error| {
                format!(
                    "sidecar method '{method}' failed after one safe restart; \
                     initial attempt: {first_error}; retry: {retry_error}"
                )
            })
        }
        Err(error) => Err(error),
    }
}

fn ensure_healthy(app: &AppHandle, state: &SidecarState) -> Result<Value, String> {
    ensure_running(app, state)?;
    match call_sidecar(state, "health", json!({}), SIDECAR_STARTUP_TIMEOUT) {
        Ok(health) => Ok(health),
        Err(first_error) => {
            state.stop()?;
            ensure_running(app, state)?;
            call_sidecar(state, "health", json!({}), SIDECAR_STARTUP_TIMEOUT).map_err(
                |retry_error| {
                    format!(
                        "analysis sidecar did not become ready after a restart; \
                         initial attempt: {first_error}; retry: {retry_error}"
                    )
                },
            )
        }
    }
}

#[tauri::command]
pub async fn sidecar_ensure(app: AppHandle) -> Result<Value, String> {
    let worker_app = app.clone();
    tauri::async_runtime::spawn_blocking(move || {
        let state = worker_app.state::<SidecarState>();
        ensure_healthy(&worker_app, &state)
    })
    .await
    .map_err(|err| format!("sidecar task failed: {err}"))?
}

#[tauri::command]
pub async fn sidecar_call(
    app: AppHandle,
    method: String,
    params: Option<Value>,
) -> Result<Value, String> {
    let worker_app = app.clone();
    tauri::async_runtime::spawn_blocking(move || {
        let state = worker_app.state::<SidecarState>();
        call_with_recovery(
            &worker_app,
            &state,
            &method,
            params.unwrap_or_else(|| json!({})),
        )
    })
    .await
    .map_err(|err| format!("sidecar task failed: {err}"))?
}

#[tauri::command]
pub async fn sidecar_stop(app: AppHandle) -> Result<(), String> {
    tauri::async_runtime::spawn_blocking(move || app.state::<SidecarState>().stop())
        .await
        .map_err(|err| format!("sidecar stop task failed: {err}"))?
}

fn stop_inner(inner: &mut SidecarInner) -> Result<(), String> {
    if let Some(mut process) = inner.process.take() {
        let request = json!({
            "v": 1,
            "id": Uuid::new_v4().to_string(),
            "method": "shutdown",
            "params": {},
        });
        match &mut process {
            SidecarProcess::Development { stdin, .. } => {
                let _ = writeln!(stdin, "{request}");
                let _ = stdin.flush();
            }
            SidecarProcess::Bundled { child, running } => {
                let _ = child.write(format!("{request}\n").as_bytes());
                running.store(false, Ordering::Release);
            }
        }
        match process {
            SidecarProcess::Development { mut child, .. } => child
                .wait_timeout_or_kill(Duration::from_secs(2))
                .map_err(|err| err.to_string())?,
            SidecarProcess::Bundled { child, .. } => child
                .kill()
                .map_err(|err| format!("failed to stop bundled sidecar: {err}"))?,
        }
    }
    fail_pending(&inner.pending, "sidecar stopped");
    Ok(())
}

trait WaitTimeout {
    fn wait_timeout_or_kill(&mut self, timeout: Duration) -> std::io::Result<()>;
}

impl WaitTimeout for Child {
    fn wait_timeout_or_kill(&mut self, timeout: Duration) -> std::io::Result<()> {
        let start = std::time::Instant::now();
        loop {
            if self.try_wait()?.is_some() {
                return Ok(());
            }
            if start.elapsed() >= timeout {
                self.kill()?;
                self.wait()?;
                return Ok(());
            }
            thread::sleep(Duration::from_millis(50));
        }
    }
}

#[cfg(test)]
mod tests {
    use super::NdjsonChunkBuffer;

    #[test]
    fn reconstructs_split_and_coalesced_ndjson_chunks() {
        let mut buffer = NdjsonChunkBuffer::default();
        assert!(buffer.push(br#"{"id":"a","res"#).is_empty());
        assert_eq!(
            buffer.push(b"ult\":1}\n{\"id\":\"b\"}\n"),
            vec![r#"{"id":"a","result":1}"#, r#"{"id":"b"}"#]
        );
    }
}

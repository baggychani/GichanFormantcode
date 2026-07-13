//! NDJSON bridge to the Python analysis sidecar (`python -m sidecar`).

use std::collections::HashMap;
use std::io::{BufRead, BufReader, Write};
use std::path::PathBuf;
use std::process::{Child, ChildStderr, ChildStdin, ChildStdout, Command, Stdio};
use std::sync::mpsc::{self, Receiver, Sender};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;

use serde_json::{json, Value};
use tauri::{AppHandle, Emitter, Manager};
use uuid::Uuid;

type PendingMap = HashMap<String, Sender<Result<Value, String>>>;
type PendingRequest = (
    String,
    Receiver<Result<Value, String>>,
    Arc<Mutex<PendingMap>>,
);

pub struct SidecarState {
    inner: Mutex<SidecarInner>,
}

struct SidecarInner {
    child: Option<Child>,
    stdin: Option<ChildStdin>,
    pending: Arc<Mutex<PendingMap>>,
}

impl SidecarState {
    pub fn new() -> Self {
        Self {
            inner: Mutex::new(SidecarInner {
                child: None,
                stdin: None,
                pending: Arc::new(Mutex::new(HashMap::new())),
            }),
        }
    }

    pub(crate) fn stop(&self) -> Result<(), String> {
        let mut inner = self.inner.lock().map_err(|_| "sidecar lock poisoned")?;
        stop_inner(&mut inner).map_err(|err| err.to_string())
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

fn spawn_sidecar() -> Result<SpawnedSidecar, String> {
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

fn start_stdout_reader(app: AppHandle, stdout: ChildStdout, pending: Arc<Mutex<PendingMap>>) {
    thread::spawn(move || {
        let reader = BufReader::new(stdout);
        for line in reader.lines() {
            let Ok(line) = line else { break };
            let line = line.trim().to_string();
            if line.is_empty() {
                continue;
            }
            let Ok(message) = serde_json::from_str::<Value>(&line) else {
                let _ = app.emit("sidecar-log", format!("invalid json: {line}"));
                continue;
            };

            if let Some(event) = message.get("event").and_then(|value| value.as_str()) {
                let payload = message.get("payload").cloned().unwrap_or_else(|| json!({}));
                let _ = app.emit(
                    "sidecar-event",
                    json!({
                        "event": event,
                        "payload": payload,
                    }),
                );
                continue;
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

        if let Ok(mut map) = pending.lock() {
            for (_, sender) in map.drain() {
                let _ = sender.send(Err("sidecar output closed".to_string()));
            }
        }
        let _ = app.emit("sidecar-log", "sidecar stdout closed");
    });
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
    if let Some(child) = inner.child.as_mut() {
        if child.try_wait().map_err(|err| err.to_string())?.is_none() {
            return Ok(());
        }
    }

    inner.stdin = None;
    inner.child = None;
    let (child, stdin, stdout, stderr) = spawn_sidecar()?;
    let pending = Arc::new(Mutex::new(HashMap::new()));
    inner.pending = Arc::clone(&pending);
    start_stdout_reader(app.clone(), stdout, pending);
    start_stderr_reader(app.clone(), stderr);
    inner.child = Some(child);
    inner.stdin = Some(stdin);
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
            let stdin = inner
                .stdin
                .as_mut()
                .ok_or_else(|| "sidecar is not running".to_string())?;
            writeln!(stdin, "{request}")
                .map_err(|err| format!("failed to write sidecar request: {err}"))?;
            stdin
                .flush()
                .map_err(|err| format!("failed to flush sidecar request: {err}"))
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

#[tauri::command]
pub async fn sidecar_ensure(app: AppHandle) -> Result<Value, String> {
    let worker_app = app.clone();
    tauri::async_runtime::spawn_blocking(move || {
        let state = worker_app.state::<SidecarState>();
        ensure_running(&worker_app, &state)?;
        call_sidecar(&state, "health", json!({}), Duration::from_secs(8))
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
        ensure_running(&worker_app, &state)?;
        call_sidecar(
            &state,
            &method,
            params.unwrap_or_else(|| json!({})),
            Duration::from_secs(60),
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

fn stop_inner(inner: &mut SidecarInner) -> std::io::Result<()> {
    if let Some(stdin) = inner.stdin.as_mut() {
        let request = json!({
            "v": 1,
            "id": Uuid::new_v4().to_string(),
            "method": "shutdown",
            "params": {},
        });
        let _ = writeln!(stdin, "{request}");
        let _ = stdin.flush();
    }
    inner.stdin = None;
    if let Some(mut child) = inner.child.take() {
        child.wait_timeout_or_kill(Duration::from_secs(2))?;
    }
    if let Ok(mut pending) = inner.pending.lock() {
        for (_, sender) in pending.drain() {
            let _ = sender.send(Err("sidecar stopped".to_string()));
        }
    }
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

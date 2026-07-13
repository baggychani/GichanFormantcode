mod sidecar;

use sidecar::{sidecar_call, sidecar_ensure, sidecar_stop, SidecarState};
use tauri::{Manager, RunEvent};

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .manage(SidecarState::new())
        .invoke_handler(tauri::generate_handler![
            sidecar_ensure,
            sidecar_call,
            sidecar_stop
        ])
        .build(tauri::generate_context!())
        .expect("error while building GichanFormant");
    app.run(|app_handle, event| {
        if matches!(event, RunEvent::Exit) {
            let _ = app_handle.state::<SidecarState>().stop();
        }
    });
}

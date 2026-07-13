mod sidecar;

use sidecar::{sidecar_call, sidecar_ensure, sidecar_stop, SidecarState};
use tauri::{Manager, RunEvent};

const AUTO_MAXIMIZE_WIDTH: f64 = 1680.0;
const AUTO_MAXIMIZE_HEIGHT: f64 = 1000.0;

fn prepare_main_window(app: &tauri::App) -> tauri::Result<()> {
    let Some(window) = app.get_webview_window("main") else {
        return Ok(());
    };

    let monitor = window.current_monitor()?.or(window.primary_monitor()?);
    let should_maximize = monitor.is_some_and(|monitor| {
        let scale = monitor.scale_factor();
        let size = monitor.size();
        let logical_width = f64::from(size.width) / scale;
        let logical_height = f64::from(size.height) / scale;
        logical_width <= AUTO_MAXIMIZE_WIDTH || logical_height <= AUTO_MAXIMIZE_HEIGHT
    });

    if should_maximize {
        window.maximize()?;
    } else {
        window.center()?;
    }
    window.show()?;
    Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .manage(SidecarState::new())
        .setup(|app| {
            prepare_main_window(app)?;
            Ok(())
        })
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

mod sidecar;

use sidecar::{sidecar_call, sidecar_ensure, sidecar_stop, SidecarState};
use tauri::{AppHandle, Manager, RunEvent, WebviewUrl, WebviewWindowBuilder};

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

#[tauri::command]
fn open_interactive_plot(app: AppHandle) -> Result<(), String> {
    if let Some(window) = app.get_webview_window("single-plot") {
        window.show().map_err(|err| err.to_string())?;
        window.set_focus().map_err(|err| err.to_string())?;
        return Ok(());
    }

    WebviewWindowBuilder::new(
        &app,
        "single-plot",
        WebviewUrl::App("index.html#single-plot".into()),
    )
    .title("GichanFormant — 대화형 플롯")
    .inner_size(1440.0, 860.0)
    .min_inner_size(1120.0, 680.0)
    .build()
    .map_err(|err| err.to_string())?;
    Ok(())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_shell::init())
        .manage(SidecarState::new())
        .setup(|app| {
            prepare_main_window(app)?;
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            sidecar_ensure,
            sidecar_call,
            sidecar_stop,
            open_interactive_plot
        ])
        .build(tauri::generate_context!())
        .expect("error while building GichanFormant");
    app.run(|app_handle, event| {
        if matches!(event, RunEvent::Exit) {
            let _ = app_handle.state::<SidecarState>().stop();
        }
    });
}

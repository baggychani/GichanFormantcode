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

fn sync_plot_window_size(app: &AppHandle, plot: &tauri::WebviewWindow) -> Result<(), String> {
    let Some(main) = app.get_webview_window("main") else {
        return Ok(());
    };
    if main.is_maximized().map_err(|err| err.to_string())? {
        plot.maximize().map_err(|err| err.to_string())?;
    } else {
        if plot.is_maximized().map_err(|err| err.to_string())? {
            plot.unmaximize().map_err(|err| err.to_string())?;
        }
        let size = main.inner_size().map_err(|err| err.to_string())?;
        plot.set_size(size).map_err(|err| err.to_string())?;
        plot.center().map_err(|err| err.to_string())?;
    }
    Ok(())
}

// Windows: sync command에서 WebviewWindowBuilder::build() 호출 시 WebView2 데드락
// → 흰 화면 + 닫기 불가. 반드시 async 명령으로 창을 만든다.
#[tauri::command]
async fn open_interactive_plot(app: AppHandle) -> Result<(), String> {
    if let Some(window) = app.get_webview_window("single-plot") {
        sync_plot_window_size(&app, &window)?;
        window.show().map_err(|err| err.to_string())?;
        window.set_focus().map_err(|err| err.to_string())?;
        return Ok(());
    }

    let window = WebviewWindowBuilder::new(
        &app,
        "single-plot",
        WebviewUrl::App("index.html#single-plot".into()),
    )
    .title("GichanFormant — 대화형 플롯")
    .inner_size(1560.0, 880.0)
    .min_inner_size(1200.0, 720.0)
    .background_color(tauri::window::Color(0x07, 0x09, 0x0c, 0xff))
    .build()
    .map_err(|err| err.to_string())?;
    sync_plot_window_size(&app, &window)?;
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

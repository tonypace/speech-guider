#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod backend;

use backend::BackendState;
use std::{
    fs, io,
    path::{Path, PathBuf},
    sync::{
        atomic::{AtomicU16, Ordering},
        Arc, Mutex,
    },
    thread,
};
use tauri::{
    menu::{Menu, MenuItem, PredefinedMenuItem},
    tray::TrayIconBuilder,
    webview::PageLoadEvent,
    App, AppHandle, Manager, RunEvent, Url, WebviewWindow, WebviewWindowBuilder,
};

#[cfg(not(target_os = "windows"))]
const START_PAGE: &str = "tauri://localhost/index.html";
#[cfg(target_os = "windows")]
const START_PAGE: &str = "http://tauri.localhost/index.html";

#[derive(Default)]
struct PendingMode(Mutex<Option<&'static str>>);

fn backend_url(port: u16) -> Url {
    Url::parse(&format!("http://127.0.0.1:{port}/")).expect("valid loopback URL")
}

fn is_backend_origin(url: &Url, port: u16) -> bool {
    port != 0
        && url.scheme() == "http"
        && url.host_str() == Some("127.0.0.1")
        && url.port_or_known_default() == Some(port)
        && url.username().is_empty()
        && url.password().is_none()
}

fn is_local_page(url: &Url) -> bool {
    let start = Url::parse(START_PAGE).expect("valid startup page URL");
    url.scheme() == start.scheme()
        && url.host_str() == start.host_str()
        && url.port_or_known_default() == start.port_or_known_default()
}

fn display_backend_failure(window: &WebviewWindow, message: &str, log: Option<&Path>) {
    eprintln!("Speech Guider backend: {message}");
    let mut page = Url::parse(START_PAGE).expect("valid startup page URL");
    page.query_pairs_mut().append_pair("error", message);
    if let Some(log) = log {
        page.query_pairs_mut()
            .append_pair("log", &log.to_string_lossy());
    }
    let _ = window.navigate(page);
}

fn start_backend(
    app: &AppHandle,
    window: &WebviewWindow,
    port: Arc<AtomicU16>,
    data_dir: &Path,
    log_path: &Path,
) -> Result<(), Box<dyn std::error::Error>> {
    let resources = app.path().resource_dir()?;
    let executable = resources.join("backend/speech-guider-backend");
    if !executable.is_file() {
        return Err(io::Error::new(
            io::ErrorKind::NotFound,
            "The bundled backend is missing. Build or reinstall the standalone Speech Guider app.",
        )
        .into());
    }
    if let Some(directory) = log_path.parent() {
        fs::create_dir_all(directory)?;
    }
    let state = app.state::<BackendState>();
    state.spawn(&executable, data_dir, log_path, &resources.join("assets"))?;

    let handle = app.clone();
    let window = window.clone();
    let log_path = log_path.to_path_buf();
    if let Err(error) = thread::Builder::new()
        .name("speech-guider-backend-monitor".into())
        .spawn(move || monitor_backend(handle, window, port, log_path))
    {
        state.terminate();
        return Err(error.into());
    }
    Ok(())
}

fn monitor_backend(app: AppHandle, window: WebviewWindow, port: Arc<AtomicU16>, log_path: PathBuf) {
    let state = app.state::<BackendState>();
    let result = (|| -> Result<Option<String>, Box<dyn std::error::Error>> {
        let Some(assigned) = state.wait_for_ready()? else {
            return Ok(None);
        };
        port.store(assigned, Ordering::Release);
        window.navigate(backend_url(assigned))?;
        eprintln!("Speech Guider backend ready at http://127.0.0.1:{assigned}");
        let exit = state.wait_for_exit()?;
        Ok(exit.map(|status| format!("The local backend stopped unexpectedly ({status}).")))
    })();
    let error = match result {
        Ok(None) => return,
        Ok(Some(message)) => message,
        Err(error) => error.to_string(),
    };
    port.store(0, Ordering::Release);
    state.terminate();
    if !state.is_stopping() {
        display_backend_failure(&window, &error, Some(&log_path));
    }
}

fn open_mode(window: &WebviewWindow, mode: &'static str) {
    let mode = serde_json::to_string(mode).expect("mode can be serialized");
    let _ = window.eval(format!("window.tauriController?.handleLaunch({mode});"));
}

fn install_tray(app: &App, port: Arc<AtomicU16>) -> tauri::Result<()> {
    let open = MenuItem::with_id(app, "open", "Open Window", true, None::<&str>)?;
    let pronunciation = MenuItem::with_id(
        app,
        "pronunciation",
        "Practice Pronunciation",
        true,
        None::<&str>,
    )?;
    let prosody = MenuItem::with_id(app, "prosody", "Practice Prosody", true, None::<&str>)?;
    let animation =
        MenuItem::with_id(app, "animation", "Explore Mouth Shapes", true, None::<&str>)?;
    let first_separator = PredefinedMenuItem::separator(app)?;
    let second_separator = PredefinedMenuItem::separator(app)?;
    let quit = MenuItem::with_id(app, "quit", "Quit", true, None::<&str>)?;
    let menu = Menu::with_items(
        app,
        &[
            &open,
            &first_separator,
            &pronunciation,
            &prosody,
            &animation,
            &second_separator,
            &quit,
        ],
    )?;

    let mut tray = TrayIconBuilder::new()
        .show_menu_on_left_click(true)
        .menu(&menu)
        .on_menu_event(move |app, event| {
            let mode = match event.id.as_ref() {
                "quit" => {
                    app.exit(0);
                    return;
                }
                "open" => None,
                "pronunciation" => Some("pronunciation"),
                "prosody" => Some("prosody"),
                "animation" => Some("animation"),
                _ => return,
            };
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.show();
                let _ = window.set_focus();
                if let Some(mode) = mode {
                    if window
                        .url()
                        .is_ok_and(|url| is_backend_origin(&url, port.load(Ordering::Acquire)))
                    {
                        open_mode(&window, mode);
                    } else if let Ok(mut pending) = app.state::<PendingMode>().0.lock() {
                        *pending = Some(mode);
                    }
                }
            }
        });
    if let Some(icon) = app.default_window_icon() {
        tray = tray.icon(icon.clone());
    }
    tray.build(app)?;
    Ok(())
}

fn desktop_paths(app: &AppHandle) -> Result<(PathBuf, PathBuf), Box<dyn std::error::Error>> {
    if let Some(value) = std::env::var_os("SPEECH_GUIDER_DESKTOP_STATE_DIR") {
        let data = PathBuf::from(value);
        if !data.is_absolute() {
            return Err(
                io::Error::other("SPEECH_GUIDER_DESKTOP_STATE_DIR must be absolute").into(),
            );
        }
        let log = data.join("logs/backend.log");
        return Ok((data, log));
    }
    Ok((
        app.path().app_data_dir()?,
        app.path().app_log_dir()?.join("backend.log"),
    ))
}

fn setup(app: &mut App) -> Result<(), Box<dyn std::error::Error>> {
    let development = tauri::is_dev();
    let port = Arc::new(AtomicU16::new(if development { 7860 } else { 0 }));
    let navigation_port = Arc::clone(&port);
    let page_port = Arc::clone(&port);
    let config = app
        .config()
        .app
        .windows
        .iter()
        .find(|window| window.label == "main")
        .ok_or_else(|| io::Error::other("Missing main window configuration"))?;
    let window = WebviewWindowBuilder::from_config(app, config)?
        .initialization_script("window.__SPEECH_GUIDER_TAURI__ = true;")
        .on_navigation(move |url| {
            is_local_page(url) || is_backend_origin(url, navigation_port.load(Ordering::Acquire))
        })
        .on_page_load(move |window, payload| {
            if payload.event() == PageLoadEvent::Finished
                && is_backend_origin(payload.url(), page_port.load(Ordering::Acquire))
            {
                if let Ok(mut pending) = window.state::<PendingMode>().0.lock() {
                    if let Some(mode) = pending.take() {
                        open_mode(&window, mode);
                    }
                }
            }
        })
        .build()?;

    install_tray(app, Arc::clone(&port))?;
    if !development {
        match desktop_paths(app.handle()) {
            Ok((data_dir, log_path)) => {
                if let Err(error) = start_backend(app.handle(), &window, port, &data_dir, &log_path)
                {
                    display_backend_failure(&window, &error.to_string(), Some(&log_path));
                }
            }
            Err(error) => display_backend_failure(&window, &error.to_string(), None),
        }
    }
    Ok(())
}

fn main() {
    tauri::Builder::default()
        .manage(BackendState::default())
        .manage(PendingMode::default())
        .setup(setup)
        .build(tauri::generate_context!())
        .expect("error while building Speech Guider")
        .run(|app, event| {
            if matches!(event, RunEvent::Exit) {
                app.state::<BackendState>().stop();
            }
        });
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn navigation_is_limited_to_local_startup_or_exact_backend_origin() {
        assert!(is_local_page(&Url::parse(START_PAGE).unwrap()));
        assert!(is_backend_origin(&backend_url(15000), 15000));
        assert!(!is_backend_origin(&backend_url(15000), 0));
        assert!(!is_backend_origin(&backend_url(15001), 15000));
        assert!(!is_backend_origin(
            &Url::parse("http://localhost:15000/").unwrap(),
            15000
        ));
        assert!(!is_backend_origin(
            &Url::parse("https://127.0.0.1:15000/").unwrap(),
            15000
        ));
        assert!(!is_local_page(
            &Url::parse("https://tauri.localhost/").unwrap()
        ));
    }
}

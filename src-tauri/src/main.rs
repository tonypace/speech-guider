#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::{
    menu::{Menu, MenuItem},
    tray::TrayIconBuilder,
    Manager,
};

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            // Create menu items
            let open_i = MenuItem::with_id(app, "open", "Open Window", true, None::<&str>)?;
            let separator1 = MenuItem::with_id(app, "sep1", "-", false, None::<&str>)?;
            let pronunciation_i = MenuItem::with_id(app, "pronunciation", "Practice Pronunciation", true, None::<&str>)?;
            let prosody_i = MenuItem::with_id(app, "prosody", "Practice Prosody", true, None::<&str>)?;
            let animation_i = MenuItem::with_id(app, "animation", "Explore Mouth Shapes", true, None::<&str>)?;
            let separator2 = MenuItem::with_id(app, "sep2", "-", false, None::<&str>)?;
            let quit_i = MenuItem::with_id(app, "quit", "Quit", true, None::<&str>)?;
            
            let menu = Menu::with_items(app, &[
                &open_i, &separator1, &pronunciation_i, &prosody_i, &animation_i, &separator2, &quit_i
            ])?;

            // Build the system tray
            let _tray = TrayIconBuilder::new()
                .icon(app.default_window_icon().unwrap().clone())
                .show_menu_on_left_click(true)
                .menu(&menu)
                .on_menu_event(|app, event| match event.id.as_ref() {
                    "open" => {
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    }
                    "pronunciation" => {
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                            // Emit event to web app via JavaScript
                            let _ = window.eval("if(window.tauriController){window.tauriController.handleLaunch('pronunciation');}");
                        }
                    }
                    "prosody" => {
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                            // Emit event to web app via JavaScript
                            let _ = window.eval("if(window.tauriController){window.tauriController.handleLaunch('prosody');}");
                        }
                    }
                    "animation" => {
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                            // Emit event to web app via JavaScript
                            let _ = window.eval("if(window.tauriController){window.tauriController.handleLaunch('animation');}");
                        }
                    }
                    "quit" => {
                        app.exit(0);
                    }
                    _ => {}
                })
                .build(app)?;

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

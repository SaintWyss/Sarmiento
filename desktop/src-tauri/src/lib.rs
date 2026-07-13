mod api;
mod workstation;

use tauri::{
    menu::{Menu, MenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    Manager,
};
use tauri_plugin_autostart::MacosLauncher;
use tauri_plugin_deep_link::DeepLinkExt;

fn show_main_window(app: &tauri::AppHandle) {
    if let Some(window) = app.get_webview_window("main") {
        let _ = window.show();
        let _ = window.unminimize();
        let _ = window.set_focus();
    }
}

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            show_main_window(app);
        }))
        .plugin(tauri_plugin_deep_link::init())
        .plugin(tauri_plugin_autostart::init(
            MacosLauncher::LaunchAgent,
            Some(vec!["--hidden"]),
        ))
        .manage(api::ApiState::default())
        .invoke_handler(tauri::generate_handler![
            api::login,
            api::dashboard,
            api::logout,
            api::update_device,
            api::rotate_device_token,
            api::revoke_device,
            api::create_enrollment_token,
            api::change_password,
            api::setup_mfa,
            api::enable_mfa,
            api::disable_mfa,
            workstation::workstation_status,
            workstation::set_integrated_mode,
            workstation::connect_device,
        ])
        .setup(|app| {
            #[cfg(target_os = "linux")]
            let _ = app.deep_link().register_all();

            let open = MenuItem::with_id(app, "open", "Abrir Sarmiento", true, None::<&str>)?;
            let physical = MenuItem::with_id(
                app,
                "physical",
                "Usar pantallas físicas",
                true,
                None::<&str>,
            )?;
            let quit = MenuItem::with_id(app, "quit", "Salir", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&open, &physical, &quit])?;
            TrayIconBuilder::new()
                .icon(app.default_window_icon().cloned().expect("application icon"))
                .menu(&menu)
                .show_menu_on_left_click(false)
                .tooltip("Sarmiento Desktop")
                .on_menu_event(|app, event| match event.id.as_ref() {
                    "open" => show_main_window(app),
                    "physical" => {
                        let _ = workstation::set_integrated_mode();
                        show_main_window(app);
                    }
                    "quit" => app.exit(0),
                    _ => {}
                })
                .on_tray_icon_event(|tray, event| {
                    if let TrayIconEvent::Click {
                        button: MouseButton::Left,
                        button_state: MouseButtonState::Up,
                        ..
                    } = event
                    {
                        show_main_window(tray.app_handle());
                    }
                })
                .build(app)?;

            if std::env::args().any(|argument| argument == "--hidden") {
                if let Some(window) = app.get_webview_window("main") {
                    let _ = window.hide();
                }
            }
            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                api.prevent_close();
                let _ = window.hide();
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running Sarmiento Desktop");
}

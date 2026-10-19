//! Ambiance's system side: read the themes and sessions the plugin writes
//! under ~/.ambiance, assign a theme to a session, launch a new session in the
//! terminal, customize, generate and install themes from the gallery, and play
//! the mood sounds.

mod gallery;
mod generate;
mod sounds;
mod store;
mod terminal;
mod wallpaper;

use serde_json::{json, Value};
use std::fs;
use std::path::{Path, PathBuf};
use store::{check_id, config, data_dir, is_safe_id, is_under, now_ms, override_of, read_json, save_config, theme_file, themes, themes_dir, write_json};
use tauri::menu::{Menu, MenuItem};
use tauri::tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent};
use tauri::{AppHandle, Emitter, Manager, WindowEvent};

/// A session whose heartbeat is older than this is closed.
const ALIVE_MS: u64 = 15_000;
/// Records of closed sessions are deleted after a day.
const FORGET_MS: u64 = 24 * 60 * 60 * 1000;
const MAX_ASSET: u64 = 8 * 1024 * 1024;

fn resources(app: &AppHandle) -> PathBuf {
    app.path().resource_dir().unwrap_or_default()
}

fn bundled_ids(app: &AppHandle) -> Vec<String> {
    theme_ids(&resources(app).join("themes"))
}

fn theme_ids(dir: &Path) -> Vec<String> {
    fs::read_dir(dir)
        .into_iter()
        .flatten()
        .flatten()
        .filter_map(|e| e.file_name().to_str().map(str::to_string))
        .collect()
}

#[tauri::command]
fn list_themes(app: AppHandle) -> Vec<Value> {
    let bundled = bundled_ids(&app);
    themes()
        .into_iter()
        .map(|mut theme| {
            let id = theme["id"].as_str().unwrap_or_default().to_string();
            theme["isBundled"] = json!(bundled.contains(&id));
            theme["override"] = override_of(&id);
            theme
        })
        .collect()
}

#[tauri::command]
fn list_sessions() -> Vec<Value> {
    let now = now_ms();
    let mut alive = Vec::new();
    for entry in fs::read_dir(data_dir().join("sessions")).into_iter().flatten().flatten() {
        let path = entry.path();
        let Some(session) = read_json(&path) else { continue };
        let heartbeat = session["heartbeat"].as_u64().unwrap_or(0);
        let is_ended = session.get("endedAt").is_some_and(|v| !v.is_null());
        if !is_ended && now.saturating_sub(heartbeat) < ALIVE_MS {
            alive.push(session);
        } else if now.saturating_sub(heartbeat) > FORGET_MS {
            let _ = fs::remove_file(&path);
            if let Some(id) = session["id"].as_str().filter(|id| is_safe_id(id)) {
                let _ = fs::remove_file(data_dir().join("assign").join(format!("{id}.json")));
                let _ = fs::remove_file(data_dir().join("events").join(format!("{id}.json")));
            }
        }
    }
    alive.sort_by_key(|s| std::cmp::Reverse(s["startedAt"].as_u64().unwrap_or(0)));
    alive
}

#[tauri::command]
fn assign_theme(session_id: String, theme: Option<String>) -> Result<(), String> {
    check_id(&session_id)?;
    if let Some(t) = &theme {
        check_id(t)?;
    }
    write_json(&data_dir().join("assign").join(format!("{session_id}.json")), &json!({ "theme": theme, "at": now_ms() }))
}

#[tauri::command]
fn get_config() -> Value {
    config()
}

#[tauri::command]
fn set_default_theme(theme: Option<String>) -> Result<(), String> {
    if let Some(t) = &theme {
        check_id(t)?;
    }
    let mut config = config();
    config["defaultTheme"] = json!(theme);
    save_config(&config)
}

/// Saves a preference shared with the plugin: style, persona, sounds or banner.
/// Every open session picks it up within two seconds.
#[tauri::command]
fn set_preference(key: String, value: Value) -> Result<(), String> {
    let valid = match key.as_str() {
        "style" => value.as_str().is_some_and(|v| ["full", "compact", "minimal"].contains(&v)),
        "persona" | "sounds" | "banner" => value.is_boolean(),
        _ => false,
    };
    if !valid {
        return Err("unknown preference".into());
    }
    let mut config = config();
    config[&key] = value;
    save_config(&config)
}

/// Links a project folder to a theme (`None` removes the link).
#[tauri::command]
fn set_project(dir: String, theme: Option<String>) -> Result<(), String> {
    if let Some(t) = &theme {
        check_id(t)?;
    }
    let mut config = config();
    if !config["projects"].is_object() {
        config["projects"] = json!({});
    }
    match theme {
        Some(t) => config["projects"][&dir] = json!(t),
        None => {
            if let Some(map) = config["projects"].as_object_mut() {
                map.remove(&dir);
            }
        }
    }
    save_config(&config)
}

#[tauri::command]
fn launch_session(dir: String, theme: Option<String>) -> Result<(), String> {
    if let Some(t) = &theme {
        check_id(t)?;
    }
    terminal::launch(&dir, theme.as_deref())
}

#[tauri::command]
fn sync_terminal() -> Result<String, String> {
    terminal::sync()
}

/// Saves a user's settings for a theme, after checking their shape.
#[tauri::command]
fn set_override(id: String, value: Value) -> Result<Value, String> {
    check_id(&id)?;
    let mut clean = json!({});
    if let Some(opacity) = value["backgroundImageOpacity"].as_f64() {
        clean["backgroundImageOpacity"] = json!(opacity.clamp(0.05, 1.0));
    }
    match value.get("shader") {
        Some(Value::Null) => clean["shader"] = Value::Null,
        Some(Value::String(s)) if terminal::SHADERS.contains(&s.as_str()) => clean["shader"] = json!(s),
        _ => {}
    }
    match value.get("backgroundImage") {
        Some(Value::Null) => clean["backgroundImage"] = Value::Null,
        Some(Value::String(path)) if path.starts_with("theme:") && theme_file(&id, &path["theme:".len()..]).is_some() => {
            clean["backgroundImage"] = json!(path)
        }
        Some(Value::String(path)) if is_under(Path::new(path), &data_dir().join("overrides").join(&id)) => clean["backgroundImage"] = json!(path),
        _ => {}
    }
    if let Some(sounds) = value["sounds"].as_bool() {
        clean["sounds"] = json!(sounds);
    }
    write_json(&data_dir().join("overrides").join(format!("{id}.json")), &clean)?;
    terminal::sync()?;
    Ok(clean)
}

/// Takes the image the user picked and adapts it to the terminal: cropped to
/// 2560 × 1440, slightly blurred, tinted with the theme's colors, darkened on
/// the left where the text goes. It stays on their machine
/// (~/.ambiance/overrides/<id>/) and never enters the repository or the
/// gallery. An animated GIF is kept as is.
#[tauri::command]
async fn set_wallpaper(id: String, path: String, intensity: Option<f64>) -> Result<Value, String> {
    check_id(&id)?;
    let target = tauri::async_runtime::spawn_blocking({
        let id = id.clone();
        move || wallpaper::adapt(&id, Path::new(&path), intensity.unwrap_or(0.5))
    })
    .await
    .map_err(|e| e.to_string())??;
    apply_wallpaper(id, &target)
}

/// The same, from an image on the web: downloaded, adapted, then the download is deleted.
#[tauri::command]
async fn set_wallpaper_url(id: String, url: String, intensity: Option<f64>) -> Result<Value, String> {
    check_id(&id)?;
    let target = tauri::async_runtime::spawn_blocking({
        let id = id.clone();
        move || {
            let download = wallpaper::download(&url)?;
            let adapted = wallpaper::adapt(&id, &download, intensity.unwrap_or(0.5));
            let _ = fs::remove_file(&download);
            adapted
        }
    })
    .await
    .map_err(|e| e.to_string())??;
    apply_wallpaper(id, &target)
}

/// Points the theme's override at a freshly adapted wallpaper.
fn apply_wallpaper(id: String, target: &Path) -> Result<Value, String> {
    let mut value = override_of(&id);
    value["backgroundImage"] = json!(target.to_string_lossy());
    value["backgroundImageOpacity"] = json!(if target.extension().is_some_and(|e| e == "gif") { 0.35 } else { 0.9 });
    set_override(id, value)
}

fn data_url(path: &Path) -> Result<String, String> {
    if fs::metadata(path).map_err(|_| "file not found")?.len() > MAX_ASSET {
        return Err("file too large to preview".into());
    }
    let mime = match path.extension().and_then(|e| e.to_str()).unwrap_or_default().to_lowercase().as_str() {
        "png" => "image/png",
        "jpg" | "jpeg" => "image/jpeg",
        "gif" => "image/gif",
        "bmp" => "image/bmp",
        "wav" => "audio/wav",
        "ogg" => "audio/ogg",
        _ => return Err("file type not allowed".into()),
    };
    let bytes = fs::read(path).map_err(|e| e.to_string())?;
    Ok(format!("data:{mime};base64,{}", store::base64(&bytes)))
}

/// A theme file, or the user's own wallpaper (only under its override folder).
fn asset_path(id: &str, path: &str) -> Result<PathBuf, String> {
    check_id(id)?;
    let candidate = PathBuf::from(path);
    if candidate.is_absolute() {
        if !is_under(&candidate, &data_dir().join("overrides").join(id)) {
            return Err("path not allowed".into());
        }
        return Ok(candidate);
    }
    theme_file(id, path).ok_or_else(|| "file not found".into())
}

/// A theme file (wallpaper, sound) or the user's own wallpaper, as a data URL.
#[tauri::command]
async fn theme_asset(id: String, path: String) -> Result<String, String> {
    tauri::async_runtime::spawn_blocking(move || data_url(&asset_path(&id, &path)?)).await.map_err(|e| e.to_string())?
}

/// A wallpaper for the previews: a small cached copy (an animated GIF as is).
#[tauri::command]
async fn theme_thumb(id: String, path: String) -> Result<String, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let source = asset_path(&id, &path)?;
        if source.extension().is_some_and(|e| e.eq_ignore_ascii_case("gif")) {
            return data_url(&source);
        }
        data_url(&wallpaper::thumbnail(&source)?)
    })
    .await
    .map_err(|e| e.to_string())?
}

#[tauri::command]
async fn generate_theme(description: String) -> Result<Value, String> {
    tauri::async_runtime::spawn_blocking(move || generate::generate(&description)).await.map_err(|e| e.to_string())?
}

#[tauri::command]
fn save_theme(theme: Value) -> Result<String, String> {
    let theme = generate::sanitize(theme)?;
    let id = theme["id"].as_str().ok_or("missing id")?.to_string();
    write_json(&themes_dir().join(&id).join("theme.json"), &theme)?;
    terminal::sync()?;
    Ok(id)
}

#[tauri::command]
fn delete_theme(app: AppHandle, id: String) -> Result<(), String> {
    check_id(&id)?;
    if bundled_ids(&app).contains(&id) {
        return Err("themes bundled with Ambiance cannot be deleted".into());
    }
    fs::remove_dir_all(themes_dir().join(&id)).map_err(|e| e.to_string())?;
    let _ = terminal::sync();
    Ok(())
}

#[tauri::command]
async fn gallery_index(app: AppHandle) -> Value {
    let resources = resources(&app);
    let (index, source) = tauri::async_runtime::spawn_blocking(move || gallery::index(&resources))
        .await
        .unwrap_or((json!({ "themes": [] }), "local"));
    json!({ "source": source, "index": index, "repo": gallery::repo() })
}

#[tauri::command]
async fn gallery_install(app: AppHandle, id: String) -> Result<(), String> {
    let resources = resources(&app);
    tauri::async_runtime::spawn_blocking(move || gallery::install(&id, &resources)).await.map_err(|e| e.to_string())??;
    terminal::sync().map(|_| ())
}

#[tauri::command]
fn open_url(url: String) -> Result<(), String> {
    if !url.starts_with("https://github.com/") {
        return Err("address not allowed".into());
    }
    store::open_external(&url)
}

#[tauri::command]
fn plugin_status() -> Value {
    let installed = read_json(&store::home_dir().join(".claude").join("plugins").join("installed_plugins.json"))
        .map(|v| v.to_string().contains("\"ambiance@"))
        .unwrap_or(false);
    json!({
        "installed": installed,
        "dataDir": data_dir().to_string_lossy(),
        "platform": std::env::consts::OS,
        "repo": gallery::repo(),
    })
}

#[tauri::command]
fn open_data_dir() -> Result<(), String> {
    let dir = data_dir();
    fs::create_dir_all(&dir).map_err(|e| e.to_string())?;
    store::open_external(&dir.to_string_lossy())
}

/// Copies the themes and effects bundled with the app into ~/.ambiance.
/// Themes that an earlier version bundled and this one no longer ships are
/// removed; themes the user created or installed are never touched.
fn install_bundled(resources: &Path) {
    let current = theme_ids(&resources.join("themes"));
    let record = data_dir().join("bundled.json");
    let previous: Vec<String> = read_json(&record).and_then(|v| serde_json::from_value(v).ok()).unwrap_or_default();
    for id in previous.iter().filter(|id| is_safe_id(id) && !current.contains(id)) {
        let _ = fs::remove_dir_all(themes_dir().join(id));
    }
    let _ = write_json(&record, &json!(current));
    for id in &current {
        let _ = store::copy_dir(&resources.join("themes").join(id), &themes_dir().join(id));
    }
    let _ = store::copy_dir(&resources.join("shaders"), &data_dir().join("shaders"));
}

fn show_window(app: &AppHandle) {
    if let Some(window) = app.get_webview_window("main") {
        let _ = window.show();
        let _ = window.unminimize();
        let _ = window.set_focus();
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .setup(|app| {
            // Copying the bundled themes and writing the terminal profiles take
            // a moment: they run beside the window, which refreshes when done.
            let handle = app.handle().clone();
            std::thread::spawn(move || {
                install_bundled(&resources(&handle));
                let _ = terminal::sync();
                let _ = handle.emit("themes-installed", ());
            });
            sounds::start();

            // Ambiance stays in the system tray once the window is closed: it is
            // what plays the mood sounds.
            let open = MenuItem::with_id(app, "open", "Open Ambiance", true, None::<&str>)?;
            let quit = MenuItem::with_id(app, "quit", "Quit", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&open, &quit])?;
            let mut tray = TrayIconBuilder::new()
                .tooltip("Ambiance")
                .menu(&menu)
                .show_menu_on_left_click(false)
                .on_menu_event(|app, event| match event.id.as_ref() {
                    "open" => show_window(app),
                    "quit" => app.exit(0),
                    _ => {}
                })
                .on_tray_icon_event(|tray, event| {
                    if let TrayIconEvent::Click { button: MouseButton::Left, button_state: MouseButtonState::Up, .. } = event {
                        show_window(tray.app_handle());
                    }
                });
            if let Some(icon) = app.default_window_icon() {
                tray = tray.icon(icon.clone());
            }
            tray.build(app)?;
            Ok(())
        })
        .on_window_event(|window, event| {
            if let WindowEvent::CloseRequested { api, .. } = event {
                let _ = window.hide();
                api.prevent_close();
            }
        })
        .invoke_handler(tauri::generate_handler![
            list_themes,
            list_sessions,
            assign_theme,
            get_config,
            set_default_theme,
            set_preference,
            set_project,
            launch_session,
            sync_terminal,
            set_override,
            set_wallpaper,
            set_wallpaper_url,
            theme_asset,
            theme_thumb,
            generate_theme,
            save_theme,
            delete_theme,
            gallery_index,
            gallery_install,
            open_url,
            plugin_status,
            open_data_dir
        ])
        .build(tauri::generate_context!())
        .expect("Ambiance could not start")
        .run(|app, event| {
            // macOS: clicking the Dock icon brings the hidden window back.
            #[cfg(target_os = "macos")]
            if let tauri::RunEvent::Reopen { .. } = event {
                show_window(app);
            }
            #[cfg(not(target_os = "macos"))]
            let _ = (app, event);
        });
}

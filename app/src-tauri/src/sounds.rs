//! The mood sounds. The plugin writes each session's latest event under
//! ~/.ambiance/events, and the app plays the theme's sound for it, from a
//! background thread: it keeps working while the window is hidden in the tray.
//! On macOS, Claude Code plays them itself.

use crate::store::{config, data_dir, find_theme, now_ms, override_of, read_json, theme_file};
use serde_json::Value;
use std::collections::HashMap;
use std::path::Path;
use std::time::Duration;

const POLL: Duration = Duration::from_millis(500);

/// Sounds follow the style unless the user chose: on in the full style.
pub fn enabled(config: &Value) -> bool {
    config["sounds"].as_bool().unwrap_or_else(|| config["style"].as_str().unwrap_or("full") == "full")
}

pub fn start() {
    if cfg!(target_os = "macos") {
        return;
    }
    std::thread::spawn(|| {
        let started = now_ms();
        let mut seen: HashMap<String, u64> = HashMap::new();
        loop {
            check(started, &mut seen);
            std::thread::sleep(POLL);
        }
    });
}

fn check(started: u64, seen: &mut HashMap<String, u64>) {
    let mut wants: Option<bool> = None;
    for entry in std::fs::read_dir(data_dir().join("events")).into_iter().flatten().flatten() {
        let path = entry.path();
        let Some(session) = path.file_stem().and_then(|s| s.to_str()).map(str::to_string) else { continue };
        let Some(event) = read_json(&path) else { continue };
        let at = event["at"].as_u64().unwrap_or(0);
        // A session seen for the first time only sounds for events newer than
        // the app: old ones are not replayed at startup.
        let is_new = match seen.insert(session, at) {
            Some(previous) => at > previous,
            None => at > started,
        };
        if !is_new || !*wants.get_or_insert_with(|| enabled(&config())) {
            continue;
        }
        let (Some(kind), Some(id)) = (event["type"].as_str(), event["theme"].as_str()) else { continue };
        if override_of(id)["sounds"].as_bool() == Some(false) {
            continue;
        }
        let file = find_theme(id).and_then(|theme| theme["sounds"][kind].as_str().and_then(|rel| theme_file(id, rel)));
        if let Some(file) = file {
            play(&file);
        }
    }
}

#[cfg(target_os = "windows")]
fn play(file: &Path) {
    use std::os::windows::ffi::OsStrExt;
    use windows_sys::Win32::Media::Audio::{PlaySoundW, SND_ASYNC, SND_FILENAME, SND_NODEFAULT};
    let wide: Vec<u16> = file.as_os_str().encode_wide().chain(Some(0)).collect();
    // SAFETY: a NUL-terminated path that outlives the call; with SND_ASYNC the
    // system reads the file on its own thread.
    unsafe {
        PlaySoundW(wide.as_ptr(), std::ptr::null_mut(), SND_FILENAME | SND_ASYNC | SND_NODEFAULT);
    }
}

#[cfg(not(target_os = "windows"))]
fn play(file: &Path) {
    use std::process::{Command, Stdio};
    let players: &[&str] = if cfg!(target_os = "macos") { &["afplay"] } else { &["paplay", "pw-play", "aplay"] };
    for player in players {
        if let Ok(mut child) = Command::new(player).arg(file).stdout(Stdio::null()).stderr(Stdio::null()).spawn() {
            std::thread::spawn(move || child.wait());
            return;
        }
    }
}

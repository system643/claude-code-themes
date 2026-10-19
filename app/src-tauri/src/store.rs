//! The files shared with the plugin, under ~/.ambiance.

use serde_json::{json, Value};
use std::fs;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

pub fn now_ms() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_millis() as u64)
        .unwrap_or(0)
}

pub fn home_dir() -> PathBuf {
    std::env::var_os("USERPROFILE")
        .or_else(|| std::env::var_os("HOME"))
        .map(PathBuf::from)
        .unwrap_or_default()
}

pub fn data_dir() -> PathBuf {
    home_dir().join(".ambiance")
}

pub fn themes_dir() -> PathBuf {
    data_dir().join("themes")
}

pub fn read_json(path: &Path) -> Option<Value> {
    serde_json::from_str(&fs::read_to_string(path).ok()?).ok()
}

/// Writes to a temporary file, then renames it: the plugin never reads a
/// half-written file.
pub fn write_json(path: &Path, value: &Value) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    let text = serde_json::to_string_pretty(value).map_err(|e| e.to_string())?;
    let tmp = path.with_extension("tmp");
    fs::write(&tmp, text).map_err(|e| e.to_string())?;
    fs::rename(&tmp, path).map_err(|e| e.to_string())
}

pub fn is_safe_id(id: &str) -> bool {
    !id.is_empty() && id.len() <= 128 && id.chars().all(|c| c.is_ascii_alphanumeric() || c == '-' || c == '_')
}

pub fn check_id(id: &str) -> Result<(), String> {
    if is_safe_id(id) { Ok(()) } else { Err("invalid id".into()) }
}

pub fn config() -> Value {
    read_json(&data_dir().join("config.json")).unwrap_or_else(|| json!({}))
}

pub fn save_config(config: &Value) -> Result<(), String> {
    write_json(&data_dir().join("config.json"), config)
}

/// The settings a user made on a theme: wallpaper, effect, sounds.
pub fn override_of(id: &str) -> Value {
    read_json(&data_dir().join("overrides").join(format!("{id}.json"))).unwrap_or_else(|| json!({}))
}

pub fn themes() -> Vec<Value> {
    let mut list: Vec<Value> = fs::read_dir(themes_dir())
        .into_iter()
        .flatten()
        .flatten()
        .filter_map(|entry| read_json(&entry.path().join("theme.json")))
        .filter(|theme| theme["id"].as_str().is_some_and(is_safe_id))
        .collect();
    list.sort_by_key(|theme| theme["name"].as_str().unwrap_or_default().to_lowercase());
    list
}

pub fn find_theme(id: &str) -> Option<Value> {
    themes().into_iter().find(|t| t["id"].as_str() == Some(id))
}

/// A theme file given by a relative path ("assets/wallpaper.png"), never
/// leaving the theme's folder.
pub fn theme_file(id: &str, relative: &str) -> Option<PathBuf> {
    let clean = relative.replace('\\', "/");
    if clean.is_empty() || clean.starts_with('/') || clean.contains(':') || clean.split('/').any(|part| part == "..") {
        return None;
    }
    let path = clean.split('/').fold(themes_dir().join(id), |path, part| path.join(part));
    path.is_file().then_some(path)
}

/// `path` lies inside `root`, with no ".." that could climb back out of it.
pub fn is_under(path: &Path, root: &Path) -> bool {
    !path.components().any(|part| part == std::path::Component::ParentDir) && path.starts_with(root)
}

/// A "#RRGGBB" color. Anything else (wrong length, non-ASCII) is refused
/// before slicing, so no input can panic.
pub fn parse_hex(value: &str) -> Option<[u8; 3]> {
    let hex = value.strip_prefix('#')?;
    if hex.len() != 6 || !hex.bytes().all(|b| b.is_ascii_hexdigit()) {
        return None;
    }
    let channel = |i: usize| u8::from_str_radix(&hex[i..i + 2], 16).ok();
    Some([channel(0)?, channel(2)?, channel(4)?])
}

pub fn copy_dir(source: &Path, target: &Path) -> std::io::Result<()> {
    fs::create_dir_all(target)?;
    for entry in fs::read_dir(source)?.flatten() {
        let from = entry.path();
        let to = target.join(entry.file_name());
        if from.is_dir() {
            copy_dir(&from, &to)?;
        } else if !same_file(&from, &to) {
            fs::copy(&from, &to)?;
            // Not every system keeps the time on a copy: set it, for same_file.
            if let Ok(modified) = fs::metadata(&from).and_then(|m| m.modified()) {
                let _ = fs::File::options().write(true).open(&to).and_then(|f| f.set_modified(modified));
            }
        }
    }
    Ok(())
}

/// Same size and same modification time (copy_dir gives each copy its
/// source's time): unchanged files are skipped without reading them.
fn same_file(a: &Path, b: &Path) -> bool {
    match (fs::metadata(a), fs::metadata(b)) {
        (Ok(a), Ok(b)) => a.len() == b.len() && a.modified().ok() == b.modified().ok(),
        _ => false,
    }
}

pub fn base64(bytes: &[u8]) -> String {
    const TABLE: &[u8; 64] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    let mut out = String::with_capacity(bytes.len().div_ceil(3) * 4);
    for chunk in bytes.chunks(3) {
        let n = (chunk[0] as u32) << 16 | (*chunk.get(1).unwrap_or(&0) as u32) << 8 | *chunk.get(2).unwrap_or(&0) as u32;
        for i in 0..4 {
            if i <= chunk.len() {
                out.push(TABLE[(n >> (18 - 6 * i) & 63) as usize] as char);
            } else {
                out.push('=');
            }
        }
    }
    out
}

pub fn open_external(target: &str) -> Result<(), String> {
    let mut command = if cfg!(target_os = "windows") {
        let mut c = std::process::Command::new("explorer");
        c.arg(target);
        c
    } else if cfg!(target_os = "macos") {
        let mut c = std::process::Command::new("open");
        c.arg(target);
        c
    } else {
        let mut c = std::process::Command::new("xdg-open");
        c.arg(target);
        c
    };
    command.spawn().map(|_| ()).map_err(|e| e.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_hex_colors() {
        assert_eq!(parse_hex("#FF8000"), Some([255, 128, 0]));
        assert_eq!(parse_hex("#ff8000"), Some([255, 128, 0]));
        assert_eq!(parse_hex("FF8000"), None);
        assert_eq!(parse_hex("#FFF"), None);
        // Six bytes, but "é" straddles the slice boundaries.
        assert_eq!(parse_hex("#aéaaa"), None);
    }

    #[test]
    fn refuses_paths_that_climb_out() {
        let root = Path::new("/home/u/.ambiance/overrides/nord");
        assert!(is_under(&root.join("wallpaper-1.jpg"), root));
        assert!(!is_under(&root.join("..").join("..").join("secret.png"), root));
        assert!(!is_under(Path::new("/home/u/other.png"), root));
    }

    /// Themes installed on this machine: `cargo test -- --ignored --nocapture`.
    #[test]
    #[ignore]
    fn lists_installed_themes() {
        let ids: Vec<String> = themes().iter().filter_map(|t| t["id"].as_str().map(str::to_string)).collect();
        println!("{ids:?}");
        assert!(!ids.is_empty());
    }
}

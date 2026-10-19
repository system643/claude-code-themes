//! The community gallery: an index on GitHub, one-click installs. Offline
//! (or before the repository is published), the index bundled with the app
//! takes over.

use crate::store::{check_id, copy_dir, themes_dir};
use serde_json::Value;
use std::io::Read;
use std::path::Path;
use std::time::Duration;

const REPO: &str = include_str!("../../repo.json");
const MAX_FILE: u64 = 8 * 1024 * 1024;
const ALLOWED: [&str; 7] = ["json", "png", "jpg", "jpeg", "gif", "wav", "ogg"];

fn raw_base() -> String {
    let repo: Value = serde_json::from_str(REPO).unwrap_or_default();
    format!(
        "https://raw.githubusercontent.com/{}/{}/{}/",
        repo["owner"].as_str().unwrap_or("sytem643"),
        repo["repo"].as_str().unwrap_or("claude-code-themes"),
        repo["branch"].as_str().unwrap_or("main"),
    )
}

pub fn repo() -> Value {
    serde_json::from_str(REPO).unwrap_or_default()
}

fn agent() -> ureq::Agent {
    ureq::AgentBuilder::new().timeout(Duration::from_secs(8)).build()
}

fn fetch(url: &str) -> Result<Vec<u8>, String> {
    let response = agent().get(url).call().map_err(|e| e.to_string())?;
    let mut bytes = Vec::new();
    response.into_reader().take(MAX_FILE + 1).read_to_end(&mut bytes).map_err(|e| e.to_string())?;
    if bytes.len() as u64 > MAX_FILE {
        return Err("file too large".into());
    }
    Ok(bytes)
}

/// The gallery index, and where it came from: "remote" or "local".
pub fn index(resources: &Path) -> (Value, &'static str) {
    if let Ok(bytes) = fetch(&format!("{}gallery/index.json", raw_base())) {
        if let Ok(index) = serde_json::from_slice::<Value>(&bytes) {
            return (index, "remote");
        }
    }
    let local = std::fs::read_to_string(resources.join("gallery").join("index.json"))
        .ok()
        .and_then(|text| serde_json::from_str(&text).ok())
        .unwrap_or_else(|| serde_json::json!({ "themes": [] }));
    (local, "local")
}

fn is_safe_file(path: &str) -> bool {
    let clean = path.replace('\\', "/");
    let extension = clean.rsplit('.').next().unwrap_or_default().to_lowercase();
    !clean.is_empty()
        && !clean.starts_with('/')
        && !clean.contains(':')
        && !clean.split('/').any(|part| part == ".." || part.is_empty())
        && ALLOWED.contains(&extension.as_str())
}

/// Installs a gallery theme into ~/.ambiance/themes/<id>.
pub fn install(id: &str, resources: &Path) -> Result<(), String> {
    check_id(id)?;
    let (index, source) = index(resources);
    let entry = index["themes"]
        .as_array()
        .and_then(|list| list.iter().find(|t| t["id"].as_str() == Some(id)))
        .cloned()
        .ok_or("theme not in the gallery")?;

    if source == "local" {
        let bundled = resources.join("themes").join(id);
        return copy_dir(&bundled, &themes_dir().join(id)).map_err(|e| format!("installation failed: {e}"));
    }

    let files: Vec<String> = entry["files"]
        .as_array()
        .map(|list| list.iter().filter_map(|f| f.as_str().map(str::to_string)).collect())
        .unwrap_or_else(|| vec!["theme.json".into()]);
    if !files.iter().any(|f| f == "theme.json") || files.iter().any(|f| !is_safe_file(f)) {
        return Err("file list rejected".into());
    }

    // Everything is downloaded before anything is written.
    let mut downloaded = Vec::new();
    for file in &files {
        let bytes = fetch(&format!("{}plugin/themes/{id}/{file}", raw_base()))?;
        if file == "theme.json" {
            let theme: Value = serde_json::from_slice(&bytes).map_err(|_| "unreadable theme.json")?;
            if theme["id"].as_str() != Some(id) {
                return Err("theme.json does not match".into());
            }
        }
        downloaded.push((file.clone(), bytes));
    }
    let target = themes_dir().join(id);
    for (file, bytes) in downloaded {
        let path = target.join(&file);
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
        }
        std::fs::write(&path, bytes).map_err(|e| e.to_string())?;
    }
    Ok(())
}

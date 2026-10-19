//! The theme generator: a description, and Claude Code (the user's own
//! subscription, no API key) writes the theme.json. The result is then checked
//! and fixed here: shape, pixel art, color contrast.

use crate::store::{self, find_theme};
use crate::terminal::{without_claude_env, SHADERS};
use serde_json::{json, Map, Value};
use std::io::{Read, Write};
use std::process::{Command, Stdio};
use std::time::{Duration, Instant};

const TIMEOUT: Duration = Duration::from_secs(240);
const EXAMPLE: &str = include_str!("../../../plugin/themes/aurora/theme.json");

fn prompt(description: &str) -> String {
    format!(
        r#"You are designing a theme for "Ambiance", which dresses up Claude Code's terminal.
Reply with ONLY a valid JSON object, no surrounding text and no code fence.

The theme the user wants: {description}

The JSON follows the exact shape of this example (same keys):
{EXAMPLE}

Constraints:
- "id": lowercase letters, digits and hyphens.
- "pixelArt": 20 columns × 12 rows per frame, 2 to 4 frames for a small looping animation; "." = transparent; every other character is a "palette" key (one letter → one #RRGGBB color). A readable, original character or emblem.
- "moods": "error" (angry, with 1 or 2 dedicated frames) and "success" (proud), each with a "status" and 3 "quotes".
- "terminal": a 16-color ANSI scheme in Windows Terminal format, dark background, highly readable text; "name" starts with "Claude · ".
- "terminal"."effects": only "shader" (one of: {shaders}) and "cursorShape"; no background image.
- No "sounds".
- ORIGINAL quotes, verbs and persona: if the idea refers to an existing work, take inspiration without quoting any official text or line.
- "persona": 1 or 2 sentences about the tone, kind-hearted.
- Language: the language of the description."#,
        shaders = SHADERS.join(", ")
    )
}

/// `claude -p` for this system. On macOS and Linux a desktop app does not get the
/// shell's PATH (nvm, Homebrew, ~/.local/bin), so claude runs through the user's
/// interactive login shell, which sets it up.
#[cfg(target_os = "windows")]
fn claude_command(model: &str) -> Command {
    let mut c = Command::new("cmd.exe");
    c.args(["/c", "claude", "-p", "--output-format", "json", "--model", model]);
    c
}

#[cfg(not(target_os = "windows"))]
fn claude_command(model: &str) -> Command {
    let safe_model: String = model.chars().filter(|c| c.is_ascii_alphanumeric() || "-._".contains(*c)).collect();
    let mut c = Command::new(crate::terminal::user_shell());
    c.args(["-lic", &format!("exec claude -p --output-format json --model {safe_model}")]);
    c
}

fn run_claude(prompt: &str) -> Result<String, String> {
    let model = std::env::var("AMBIANCE_GEN_MODEL").unwrap_or_else(|_| "sonnet".into());
    let mut command = claude_command(&model);
    without_claude_env(&mut command);
    command
        .current_dir(std::env::temp_dir())
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x0800_0000);
    }
    let mut child = command.spawn().map_err(|e| format!("Claude Code not found: {e}"))?;
    child.stdin.take().ok_or("stdin")?.write_all(prompt.as_bytes()).map_err(|e| e.to_string())?;

    // Both pipes are drained as the child runs: a full stderr pipe would block it.
    let drain = |mut pipe: Box<dyn Read + Send>| {
        std::thread::spawn(move || {
            let mut text = String::new();
            let _ = pipe.read_to_string(&mut text);
            text
        })
    };
    let reader = drain(Box::new(child.stdout.take().ok_or("stdout")?));
    let errors = drain(Box::new(child.stderr.take().ok_or("stderr")?));
    let started = Instant::now();
    loop {
        if child.try_wait().map_err(|e| e.to_string())?.is_some() {
            break;
        }
        if started.elapsed() > TIMEOUT {
            let _ = child.kill();
            return Err("Claude Code took too long to answer".into());
        }
        std::thread::sleep(Duration::from_millis(200));
    }
    let output = reader.join().map_err(|_| "could not read the output")?;
    let stderr = errors.join().unwrap_or_default();
    let envelope: Value = serde_json::from_str(output.trim()).map_err(|_| {
        let detail = stderr.trim().lines().last().unwrap_or_default();
        if detail.is_empty() { "unreadable answer from Claude Code".to_string() } else { format!("Claude Code failed: {detail}") }
    })?;
    if envelope["is_error"].as_bool() == Some(true) {
        return Err(envelope["result"].as_str().unwrap_or("Claude Code returned an error").to_string());
    }
    envelope["result"].as_str().map(str::to_string).ok_or_else(|| "empty answer".into())
}

fn extract_json(text: &str) -> Result<Value, String> {
    let start = text.find('{').ok_or("no JSON in the answer")?;
    let end = text.rfind('}').ok_or("incomplete JSON")?;
    serde_json::from_str(&text[start..=end]).map_err(|e| format!("invalid JSON: {e}"))
}

fn parse_hex(hex: &str) -> Option<[f64; 3]> {
    store::parse_hex(hex).map(|rgb| rgb.map(f64::from))
}

fn to_hex(rgb: [f64; 3]) -> String {
    format!("#{:02X}{:02X}{:02X}", rgb[0].round() as u8, rgb[1].round() as u8, rgb[2].round() as u8)
}

fn luminance(rgb: [f64; 3]) -> f64 {
    let channel = |v: f64| {
        let v = v / 255.0;
        if v <= 0.03928 { v / 12.92 } else { ((v + 0.055) / 1.055).powf(2.4) }
    };
    0.2126 * channel(rgb[0]) + 0.7152 * channel(rgb[1]) + 0.0722 * channel(rgb[2])
}

pub fn contrast(a: [f64; 3], b: [f64; 3]) -> f64 {
    let (la, lb) = (luminance(a), luminance(b));
    (la.max(lb) + 0.05) / (la.min(lb) + 0.05)
}

/// Lightens (or darkens, on a light background) a color until it reaches the wanted contrast.
fn ensure_contrast(color: &str, background: [f64; 3], target: f64) -> String {
    let Some(mut rgb) = parse_hex(color) else { return "#E0E0E0".into() };
    let toward = if luminance(background) < 0.4 { 255.0 } else { 0.0 };
    for _ in 0..40 {
        if contrast(rgb, background) >= target {
            break;
        }
        for v in &mut rgb {
            *v += (toward - *v) * 0.08;
        }
    }
    to_hex(rgb)
}

fn slug(text: &str) -> String {
    let mut out = String::new();
    for c in text.to_lowercase().chars() {
        let mapped = match c {
            'à' | 'â' | 'ä' => 'a',
            'é' | 'è' | 'ê' | 'ë' => 'e',
            'î' | 'ï' => 'i',
            'ô' | 'ö' => 'o',
            'ù' | 'û' | 'ü' => 'u',
            'ç' => 'c',
            c if c.is_ascii_alphanumeric() => c,
            _ => '-',
        };
        if mapped != '-' || !out.ends_with('-') {
            out.push(mapped);
        }
    }
    out.trim_matches('-').chars().take(40).collect()
}

fn valid_frames(value: &Value, width: usize, height: usize) -> Vec<Value> {
    value
        .as_array()
        .map(|frames| {
            frames
                .iter()
                .filter(|frame| {
                    frame.as_array().is_some_and(|rows| {
                        rows.len() == height && rows.iter().all(|r| r.as_str().is_some_and(|s| s.chars().count() == width))
                    })
                })
                .cloned()
                .collect()
        })
        .unwrap_or_default()
}

/// Makes the theme safe to install, whatever the model wrote.
pub fn sanitize(mut theme: Value) -> Result<Value, String> {
    let map = theme.as_object_mut().ok_or("the theme is not an object")?;
    let name = map.get("name").and_then(Value::as_str).unwrap_or("My theme").chars().take(40).collect::<String>();
    // The plugin only reads lowercase ids: whatever the model wrote goes through the slug.
    let base = slug(map.get("id").and_then(Value::as_str).unwrap_or(&name));
    let base = if base.is_empty() { "my-theme".to_string() } else { base };
    let mut id = base.clone();
    let mut n = 2;
    while find_theme(&id).is_some() {
        id = format!("{base}-{n}");
        n += 1;
    }
    map.insert("id".into(), json!(id));
    map.insert("name".into(), json!(name));
    map.insert("author".into(), json!("Ambiance · generated with Claude"));
    map.remove("sounds");

    // Pixel art: every frame the same size, otherwise it is dropped.
    let art = map.get("pixelArt").cloned().unwrap_or(Value::Null);
    let first = art["frames"][0].as_array().cloned().unwrap_or_default();
    let height = first.len();
    let width = first.first().and_then(Value::as_str).map(|s| s.chars().count()).unwrap_or(0);
    let frames = valid_frames(&art["frames"], width, height);
    if (1..=32).contains(&width) && (1..=24).contains(&height) && !frames.is_empty() {
        map.insert("pixelArt".into(), json!({ "palette": art["palette"], "fps": art["fps"].as_f64().unwrap_or(3.0).clamp(1.0, 8.0), "frames": frames }));
        if let Some(moods) = map.get_mut("moods").and_then(Value::as_object_mut) {
            for mood in moods.values_mut() {
                let kept = valid_frames(&mood["frames"], width, height);
                mood["frames"] = json!(kept);
            }
        }
    } else {
        map.remove("pixelArt");
    }

    // Terminal: valid colors and text readable on the background.
    let terminal = map.entry("terminal").or_insert_with(|| json!({}));
    let background_hex = terminal["background"].as_str().filter(|c| parse_hex(c).is_some()).unwrap_or("#14141A").to_string();
    let background = parse_hex(&background_hex).unwrap_or([20.0, 20.0, 26.0]);
    terminal["background"] = json!(background_hex);
    terminal["name"] = json!(format!("Claude · {name}"));
    let foreground = terminal["foreground"].as_str().unwrap_or("#E0E0E0").to_string();
    terminal["foreground"] = json!(ensure_contrast(&foreground, background, 7.0));
    for key in ["white", "brightWhite", "red", "green", "yellow", "blue", "purple", "cyan", "brightRed", "brightGreen", "brightYellow", "brightBlue", "brightPurple", "brightCyan"] {
        let color = terminal[key].as_str().unwrap_or("#C0C0C0").to_string();
        terminal[key] = json!(ensure_contrast(&color, background, 3.0));
    }
    let shader = terminal["effects"]["shader"].as_str().filter(|s| SHADERS.contains(s)).map(str::to_string);
    let cursor = terminal["effects"]["cursorShape"].clone();
    terminal["effects"] = json!({ "shader": shader, "cursorShape": cursor });

    let colors = map.entry("colors").or_insert_with(|| json!({}));
    for (key, target) in [("accent", 3.0), ("secondary", 4.5), ("muted", 4.5)] {
        let color = colors[key].as_str().unwrap_or("#C0C0C0").to_string();
        colors[key] = json!(ensure_contrast(&color, background, target));
    }

    let mut clean = Map::new();
    clean.insert("$schema".into(), json!("../../../docs/theme.schema.json"));
    clean.extend(map.clone());
    Ok(Value::Object(clean))
}

pub fn generate(description: &str) -> Result<Value, String> {
    let description = description.trim();
    if description.is_empty() || description.chars().count() > 400 {
        return Err("describe the theme in one or two sentences".into());
    }
    sanitize(extract_json(&run_claude(&prompt(description))?)?)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn contrast_is_fixed() {
        let theme = sanitize(json!({
            "name": "Test",
            "terminal": { "background": "#101010", "foreground": "#202020" },
            "colors": { "muted": "#151515" }
        }))
        .unwrap();
        let bg = parse_hex("#101010").unwrap();
        assert!(contrast(parse_hex(theme["terminal"]["foreground"].as_str().unwrap()).unwrap(), bg) >= 7.0);
        assert!(contrast(parse_hex(theme["colors"]["muted"].as_str().unwrap()).unwrap(), bg) >= 4.5);
        assert_eq!(theme["terminal"]["name"], "Claude · Test");
    }

    #[test]
    fn broken_pixel_art_is_dropped() {
        let theme = sanitize(json!({ "name": "X", "pixelArt": { "palette": {}, "frames": [["ab", "a"]] } })).unwrap();
        assert!(theme.get("pixelArt").is_none());
    }

    #[test]
    fn ids_are_lowercase_slugs() {
        let theme = sanitize(json!({ "id": "My_Theme", "name": "X" })).unwrap();
        assert!(theme["id"].as_str().unwrap().starts_with("my-theme"));
    }

    #[test]
    fn non_ascii_colors_do_not_panic() {
        let theme = sanitize(json!({ "name": "X", "terminal": { "background": "#aéaaa" } })).unwrap();
        assert_eq!(theme["terminal"]["background"], "#14141A");
    }

    /// A real generation: `AMBIANCE_GEN_MODEL=haiku cargo test -- --ignored --nocapture`.
    #[test]
    #[ignore]
    fn generates_a_theme() {
        let theme = generate("An ice dragon in the mountains under the northern lights").unwrap();
        println!("{}", serde_json::to_string_pretty(&theme).unwrap());
        assert!(theme["id"].as_str().is_some_and(store::is_safe_id));
        assert!(theme["terminal"]["background"].is_string());
    }
}

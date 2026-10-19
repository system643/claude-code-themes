//! Theme colors, wallpapers and effects in the terminals, and launching a new
//! session that is already themed.
//!
//! Windows: Windows Terminal (a fragment: one color scheme and one profile per theme).
//! macOS: iTerm2 (dynamic profiles), Ghostty (theme files), Terminal.app as a fallback.
//! Linux: Ghostty, kitty, otherwise the default terminal.

use crate::store::{data_dir, find_theme, home_dir, override_of, parse_hex, read_json, theme_file, themes, write_json};
use serde_json::{json, Value};
use std::path::{Path, PathBuf};
use std::process::Command;

const ANSI: [&str; 16] = [
    "black", "red", "green", "yellow", "blue", "purple", "cyan", "white",
    "brightBlack", "brightRed", "brightGreen", "brightYellow", "brightBlue", "brightPurple", "brightCyan", "brightWhite",
];

pub const SHADERS: [&str; 10] = ["stars", "embers", "snow", "rain", "petals", "fireflies", "bubbles", "matrix", "crt", "glow"];

/// A theme's effects once the user's settings are applied.
pub struct Effects {
    pub background_image: Option<PathBuf>,
    pub background_opacity: f64,
    pub stretch: String,
    /// The Windows Terminal (HLSL) shader file.
    pub shader: Option<PathBuf>,
    /// The Ghostty (GLSL) shader file, for macOS and Linux.
    pub glsl_shader: Option<PathBuf>,
    pub cursor: Option<String>,
    pub font: Option<String>,
}

pub fn effects(theme: &Value) -> Effects {
    let id = theme["id"].as_str().unwrap_or_default();
    let base = &theme["terminal"]["effects"];
    let custom = override_of(id);
    let pick = |key: &str| custom.get(key).unwrap_or(&base[key]).clone();

    // The chosen wallpaper: another image of the theme ("theme:assets/…"), the
    // user's own image (absolute path), none (null), otherwise the theme's.
    let background_image = match custom.get("backgroundImage") {
        Some(Value::String(path)) if path.starts_with("theme:") => theme_file(id, &path["theme:".len()..]),
        Some(Value::String(path)) => Some(PathBuf::from(path)).filter(|p| p.is_file()),
        Some(_) => None,
        None => base["backgroundImage"].as_str().and_then(|rel| theme_file(id, rel)),
    };
    let shader_name = pick("shader").as_str().filter(|name| SHADERS.contains(name)).map(str::to_string);
    let shader_file = |extension: &str| {
        shader_name
            .as_ref()
            .map(|name| data_dir().join("shaders").join(format!("{name}.{extension}")))
            .filter(|path| path.is_file())
    };
    let shader = shader_file("hlsl");
    let glsl_shader = shader_file("glsl");

    Effects {
        background_image,
        background_opacity: pick("backgroundImageOpacity").as_f64().unwrap_or(0.4).clamp(0.05, 1.0),
        stretch: pick("backgroundImageStretchMode").as_str().unwrap_or("uniformToFill").to_string(),
        shader,
        glsl_shader,
        cursor: pick("cursorShape").as_str().map(str::to_string),
        font: pick("font").as_str().map(str::to_string),
    }
}

fn profile_name(theme: &Value) -> String {
    format!("Claude · {}", theme["name"].as_str().or(theme["id"].as_str()).unwrap_or("Claude"))
}

/// Writes the configuration of every installed terminal. Returns "written",
/// "unchanged" or "unsupported".
pub fn sync() -> Result<String, String> {
    let themes: Vec<Value> = themes().into_iter().filter(|t| t["terminal"]["name"].is_string()).collect();
    let mut wrote = false;
    let mut supported = false;

    if cfg!(target_os = "windows") {
        if let Some(path) = windows_fragment_path() {
            supported = true;
            wrote |= write_if_changed(&path, &windows_fragment(&themes))?;
            if wrote {
                reload_windows_terminal();
            }
        }
    }
    if cfg!(target_os = "macos") {
        supported = true;
        let path = home_dir().join("Library/Application Support/iTerm2/DynamicProfiles/ambiance.json");
        wrote |= write_if_changed(&path, &iterm_profiles(&themes))?;
    }
    if !cfg!(target_os = "windows") {
        supported = true;
        for theme in &themes {
            wrote |= write_ghostty_theme(theme)?;
        }
    }
    Ok(if !supported { "unsupported" } else if wrote { "written" } else { "unchanged" }.into())
}

fn write_if_changed(path: &Path, value: &Value) -> Result<bool, String> {
    if read_json(path).as_ref() == Some(value) {
        return Ok(false);
    }
    write_json(path, value)?;
    Ok(true)
}

fn windows_fragment_path() -> Option<PathBuf> {
    std::env::var_os("LOCALAPPDATA").map(|dir| {
        PathBuf::from(dir).join("Microsoft").join("Windows Terminal").join("Fragments").join("Ambiance").join("ambiance.json")
    })
}

fn windows_fragment(themes: &[Value]) -> Value {
    let schemes: Vec<Value> = themes
        .iter()
        .map(|t| {
            let mut scheme = t["terminal"].clone();
            if let Some(map) = scheme.as_object_mut() {
                map.remove("effects");
            }
            scheme
        })
        .collect();
    let profiles: Vec<Value> = themes
        .iter()
        .filter_map(|t| {
            let id = t["id"].as_str()?;
            let fx = effects(t);
            let mut profile = json!({
                "name": profile_name(t),
                "commandline": format!("cmd.exe /k set CLAUDE_THEME={id}&& claude"),
                "colorScheme": t["terminal"]["name"],
                "tabColor": t["colors"]["accent"],
                "icon": t["emoji"],
                "startingDirectory": "%USERPROFILE%",
            });
            if let Some(image) = &fx.background_image {
                profile["backgroundImage"] = json!(image.to_string_lossy());
                profile["backgroundImageOpacity"] = json!(fx.background_opacity);
                profile["backgroundImageStretchMode"] = json!(fx.stretch);
            }
            if let Some(shader) = &fx.shader {
                profile["experimental.pixelShaderPath"] = json!(shader.to_string_lossy());
            }
            if let Some(cursor) = &fx.cursor {
                profile["cursorShape"] = json!(cursor);
            }
            if let Some(font) = &fx.font {
                profile["font"] = json!({ "face": font });
            }
            Some(profile)
        })
        .collect();
    json!({ "schemes": schemes, "profiles": profiles })
}

/// Windows Terminal only rereads its fragments when it reloads its settings:
/// touching settings.json is enough to ask for it, without changing anything.
fn reload_windows_terminal() {
    let Some(local) = std::env::var_os("LOCALAPPDATA").map(PathBuf::from) else { return };
    let candidates = [
        local.join("Packages").join("Microsoft.WindowsTerminal_8wekyb3d8bbwe").join("LocalState").join("settings.json"),
        local.join("Packages").join("Microsoft.WindowsTerminalPreview_8wekyb3d8bbwe").join("LocalState").join("settings.json"),
        local.join("Microsoft").join("Windows Terminal").join("settings.json"),
    ];
    for path in candidates.iter().filter(|p| p.is_file()) {
        if let Ok(file) = std::fs::OpenOptions::new().append(true).open(path) {
            let _ = file.set_modified(std::time::SystemTime::now());
        }
    }
}

fn iterm_color(hex: Option<&str>) -> Value {
    let [r, g, b] = hex.and_then(parse_hex).unwrap_or([0, 0, 0]).map(|v| f64::from(v) / 255.0);
    json!({ "Red Component": r, "Green Component": g, "Blue Component": b, "Color Space": "sRGB" })
}

fn iterm_profiles(themes: &[Value]) -> Value {
    let profiles: Vec<Value> = themes
        .iter()
        .filter_map(|t| {
            let id = t["id"].as_str()?;
            let term = &t["terminal"];
            let fx = effects(t);
            let mut profile = json!({
                "Name": profile_name(t),
                "Guid": format!("ambiance-{id}"),
                "Badge Text": format!("{} {}", t["emoji"].as_str().unwrap_or(""), t["name"].as_str().unwrap_or(id)),
                "Custom Command": "Yes",
                "Command": format!("/bin/zsh -lic 'CLAUDE_THEME={id} claude; exec /bin/zsh -l'"),
                "Background Color": iterm_color(term["background"].as_str()),
                "Foreground Color": iterm_color(term["foreground"].as_str()),
                "Cursor Color": iterm_color(term["cursorColor"].as_str()),
                "Selection Color": iterm_color(term["selectionBackground"].as_str()),
                "Tab Color": iterm_color(t["colors"]["accent"].as_str()),
                "Use Tab Color": true,
            });
            for (i, key) in ANSI.iter().enumerate() {
                profile[format!("Ansi {i} Color")] = iterm_color(term[*key].as_str());
            }
            if let Some(image) = &fx.background_image {
                profile["Background Image Location"] = json!(image.to_string_lossy());
                profile["Blend"] = json!(1.0 - fx.background_opacity);
                profile["Background Image Mode"] = json!(2);
            }
            Some(profile)
        })
        .collect();
    json!({ "Profiles": profiles })
}

fn ghostty_dir() -> PathBuf {
    std::env::var_os("XDG_CONFIG_HOME").map(PathBuf::from).unwrap_or_else(|| home_dir().join(".config")).join("ghostty").join("themes")
}

/// A "#RRGGBB" color of the theme's terminal scheme, or nothing. Colors end up
/// in config files and command lines: a community theme must not be able to
/// slip another setting in through them.
fn color<'a>(term: &'a Value, key: &str) -> Option<&'a str> {
    term[key].as_str().filter(|c| parse_hex(c).is_some())
}

fn ghostty_theme(theme: &Value, fx: &Effects) -> String {
    let term = &theme["terminal"];
    let mut lines: Vec<String> = ANSI
        .iter()
        .enumerate()
        .filter_map(|(i, key)| color(term, key).map(|c| format!("palette = {i}={c}")))
        .collect();
    for (key, field) in [("background", "background"), ("foreground", "foreground"), ("cursor-color", "cursorColor"), ("selection-background", "selectionBackground")] {
        if let Some(c) = color(term, field) {
            lines.push(format!("{key} = {c}"));
        }
    }
    if let Some(image) = &fx.background_image {
        lines.push(format!("background-image = {}", image.to_string_lossy()));
        lines.push(format!("background-image-opacity = {:.2}", fx.background_opacity));
        lines.push("background-image-fit = cover".to_string());
    }
    if let Some(shader) = &fx.glsl_shader {
        lines.push(format!("custom-shader = {}", shader.to_string_lossy()));
        lines.push("custom-shader-animation = true".to_string());
    }
    lines.join("\n") + "\n"
}

fn write_ghostty_theme(theme: &Value) -> Result<bool, String> {
    let Some(id) = theme["id"].as_str() else { return Ok(false) };
    let text = ghostty_theme(theme, &effects(theme));
    let path = ghostty_dir().join(format!("ambiance-{id}"));
    if std::fs::read_to_string(&path).ok().as_deref() == Some(text.as_str()) {
        return Ok(false);
    }
    std::fs::create_dir_all(ghostty_dir()).map_err(|e| e.to_string())?;
    std::fs::write(&path, text).map_err(|e| e.to_string())?;
    Ok(true)
}

/// A session launched from here must not inherit a parent Claude Code
/// session's variables (the app may have been opened from one): it would think
/// it is a sub-session and would not save its conversation.
pub fn without_claude_env(command: &mut Command) {
    for (name, _) in std::env::vars_os() {
        let upper = name.to_string_lossy().to_uppercase();
        if upper.starts_with("CLAUDE_CODE") || upper == "CLAUDECODE" || upper == "CLAUDE_THEME" {
            command.env_remove(&name);
        }
    }
}

#[cfg_attr(any(target_os = "windows", target_os = "macos"), allow(dead_code))]
fn on_path(program: &str) -> bool {
    std::env::var_os("PATH")
        .map(|paths| std::env::split_paths(&paths).any(|dir| dir.join(program).is_file()))
        .unwrap_or(false)
}

pub fn launch(dir: &str, theme_id: Option<&str>) -> Result<(), String> {
    if !Path::new(dir).is_dir() {
        return Err("this folder does not exist".into());
    }
    let theme = theme_id.and_then(find_theme);
    launch_with(dir, theme.as_ref())
}

#[cfg(target_os = "windows")]
fn launch_with(dir: &str, theme: Option<&Value>) -> Result<(), String> {
    use std::os::windows::process::CommandExt;
    const CREATE_NO_WINDOW: u32 = 0x0800_0000;

    let folder = Path::new(dir).file_name().and_then(|n| n.to_str()).unwrap_or(dir);
    let id = theme.and_then(|t| t["id"].as_str());
    let title = match theme.and_then(|t| t["name"].as_str()) {
        Some(name) => format!("{name} · {folder}"),
        None => format!("Claude · {folder}"),
    };
    // cmd.exe reads "set CLAUDE_THEME=x&& claude" as a single line: the pieces
    // are passed separately so there are no quotes to deal with.
    let shell: Vec<String> = match id {
        Some(id) => vec!["cmd.exe".into(), "/k".into(), "set".into(), format!("CLAUDE_THEME={id}&&"), "claude".into()],
        None => vec!["cmd.exe".into(), "/k".into(), "claude".into()],
    };

    let mut wt = Command::new("wt.exe");
    without_claude_env(&mut wt);
    // Windows Terminal shows 24-bit color: a TERM inherited from another terminal
    // would put Claude Code in 256-color mode and dull the theme.
    wt.env_remove("TERM").env("COLORTERM", "truecolor");
    wt.args(["-w", "0", "new-tab"]);
    // The theme's profile carries its colors, wallpaper and effect.
    if let Some(theme) = theme.filter(|t| t["terminal"]["name"].is_string()) {
        wt.args(["-p", &profile_name(theme)]);
    }
    wt.args(["--title", &title, "-d", dir]);
    if wt.args(&shell).creation_flags(CREATE_NO_WINDOW).spawn().is_ok() {
        return Ok(());
    }

    // Without Windows Terminal: a classic console, without the theme's colors.
    let mut console = Command::new("cmd.exe");
    without_claude_env(&mut console);
    console.args(["/c", "start", &title, "cmd.exe", "/k", "claude"]).current_dir(dir);
    if let Some(id) = id {
        console.env("CLAUDE_THEME", id);
    }
    console.creation_flags(CREATE_NO_WINDOW).spawn().map(|_| ()).map_err(|e| e.to_string())
}

#[cfg(not(target_os = "windows"))]
fn quote(s: &str) -> String {
    format!("'{}'", s.replace('\'', "'\\''"))
}

/// The user's shell: $SHELL, or zsh on macOS and bash elsewhere.
#[cfg(not(target_os = "windows"))]
pub fn user_shell() -> String {
    std::env::var("SHELL")
        .ok()
        .filter(|shell| Path::new(shell).is_file())
        .unwrap_or_else(|| if cfg!(target_os = "macos") { "/bin/zsh".into() } else { "/bin/bash".into() })
}

/// What the terminal runs: Claude Code with the theme, then the shell again.
#[cfg(not(target_os = "windows"))]
fn session_command(theme: Option<&Value>) -> String {
    let env = theme
        .and_then(|t| t["id"].as_str())
        .map(|id| format!("CLAUDE_THEME={id} "))
        .unwrap_or_default();
    format!("{env}claude; exec {}", user_shell())
}

#[cfg(target_os = "macos")]
fn launch_with(dir: &str, theme: Option<&Value>) -> Result<(), String> {
    let id = theme.and_then(|t| t["id"].as_str());
    let shell = user_shell();
    let run = session_command(theme);
    let applescript = |s: &str| s.replace('\\', "\\\\").replace('"', "\\\"");
    let spawn = |mut command: Command| {
        without_claude_env(&mut command);
        command.spawn().map(|_| ()).map_err(|e| e.to_string())
    };

    if Path::new("/Applications/iTerm.app").exists() {
        let profile = theme.map(profile_name).unwrap_or_else(|| "Default".into());
        let line = format!("{shell} -lic {}", quote(&format!("cd {} && {run}", quote(dir))));
        let script = format!(
            "tell application \"iTerm\"\nactivate\ncreate window with profile \"{}\" command \"{}\"\nend tell",
            applescript(&profile),
            applescript(&line)
        );
        let mut osa = Command::new("osascript");
        osa.args(["-e", &script]);
        return spawn(osa);
    }
    if Path::new("/Applications/Ghostty.app").exists() {
        let mut open = Command::new("open");
        open.args(["-na", "Ghostty.app", "--args", &format!("--working-directory={dir}")]);
        if let Some(id) = id {
            open.arg(format!("--theme=ambiance-{id}"));
        }
        open.args(["-e", &shell, "-lic", &run]);
        return spawn(open);
    }
    // Terminal.app: no 24-bit color, so the pixel art is approximated there.
    let line = format!("cd {} && {run}", quote(dir));
    let script = format!("tell application \"Terminal\"\nactivate\ndo script \"{}\"\nend tell", applescript(&line));
    let mut osa = Command::new("osascript");
    osa.args(["-e", &script]);
    spawn(osa)
}

#[cfg(not(any(target_os = "windows", target_os = "macos")))]
fn launch_with(dir: &str, theme: Option<&Value>) -> Result<(), String> {
    let id = theme.and_then(|t| t["id"].as_str());
    let shell = user_shell();
    let run = session_command(theme);
    let fx = theme.map(effects);
    let term = theme.map(|t| &t["terminal"]);

    let mut command = if on_path("ghostty") {
        let mut c = Command::new("ghostty");
        c.arg(format!("--working-directory={dir}"));
        if let Some(id) = id {
            c.arg(format!("--theme=ambiance-{id}"));
        }
        c.args(["-e", &shell, "-lic", &run]);
        c
    } else if on_path("kitty") {
        let mut c = Command::new("kitty");
        c.args(["--directory", dir]);
        if let Some(term) = term {
            for (i, key) in ANSI.iter().enumerate() {
                if let Some(value) = color(term, key) {
                    c.args(["-o", &format!("color{i}={value}")]);
                }
            }
            for (key, field) in [("background", "background"), ("foreground", "foreground"), ("cursor", "cursorColor"), ("selection_background", "selectionBackground")] {
                if let Some(value) = color(term, field) {
                    c.args(["-o", &format!("{key}={value}")]);
                }
            }
        }
        if let Some(image) = fx.as_ref().and_then(|fx| fx.background_image.as_ref()) {
            let tint = 1.0 - fx.as_ref().map(|fx| fx.background_opacity).unwrap_or(0.85);
            c.args(["-o", &format!("background_image={}", image.to_string_lossy())]);
            c.args(["-o", "background_image_layout=cscaled", "-o", &format!("background_tint={tint:.2}")]);
        }
        c.args([&shell, "-lic", &run]);
        c
    } else if on_path("wezterm") {
        let mut c = Command::new("wezterm");
        c.args(["start", "--cwd", dir, "--", &shell, "-lic", &run]);
        c
    } else if on_path("alacritty") {
        let mut c = Command::new("alacritty");
        c.args(["--working-directory", dir]);
        if let Some(term) = term {
            for (key, field) in [("colors.primary.background", "background"), ("colors.primary.foreground", "foreground")] {
                if let Some(value) = color(term, field) {
                    c.args(["-o", &format!("{key}='{value}'")]);
                }
            }
        }
        c.args(["-e", &shell, "-lic", &run]);
        c
    } else if on_path("gnome-terminal") {
        let mut c = Command::new("gnome-terminal");
        c.args([&format!("--working-directory={dir}"), "--", &shell, "-lic", &run]);
        c
    } else if on_path("konsole") {
        let mut c = Command::new("konsole");
        c.args(["--workdir", dir, "-e", &shell, "-lic", &run]);
        c
    } else if on_path("xfce4-terminal") {
        let mut c = Command::new("xfce4-terminal");
        c.args([&format!("--working-directory={dir}"), "-x", &shell, "-lic", &run]);
        c
    } else {
        let mut c = Command::new("x-terminal-emulator");
        c.args(["-e", &shell, "-lic", &format!("cd {} && {run}", quote(dir))]);
        c
    };
    without_claude_env(&mut command);
    command.spawn().map(|_| ()).map_err(|e| e.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ghostty_theme_keeps_only_real_colors() {
        let theme = json!({ "terminal": {
            "background": "#101010",
            "foreground": "#EEEEEE\ncommand = /bin/sh -c evil",
            "red": "red",
        } });
        let fx = Effects { background_image: None, background_opacity: 0.4, stretch: String::new(), shader: None, glsl_shader: None, cursor: None, font: None };
        let text = ghostty_theme(&theme, &fx);
        assert_eq!(text, "background = #101010\n");
    }
}

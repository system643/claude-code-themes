# Contributing to Ambiance

Thanks for helping. Themes, bug reports, terminal support and fixes are all welcome.

- Questions and ideas: [GitHub Discussions](https://github.com/sytem643/claude-code-themes/discussions).
- Bugs and feature requests: the [issue forms](https://github.com/sytem643/claude-code-themes/issues/new/choose).
- Security problems: privately, see [SECURITY.md](SECURITY.md).

Everyone taking part follows the [Code of Conduct](CODE_OF_CONDUCT.md).

## Good first contributions

- **A new theme.** The easiest way in, and the one that makes the gallery grow. No code: one JSON file, and art if you like. See [Creating a theme](#creating-a-theme) below.
- **Polish an existing theme**: better quotes, a cleaner pixel-art animation, a mood frame it is missing.
- **Terminal support**: Ambiance writes profiles for Windows Terminal, iTerm2, Ghostty and kitty (`app/src-tauri/src/terminal.rs`). Others are open.
- Issues labeled [`good first issue`](https://github.com/sytem643/claude-code-themes/labels/good%20first%20issue).

For anything bigger than a fix, open an issue or a discussion first, so we can agree on the approach before you spend time on it.

## Creating a theme

A theme is a folder, `plugin/themes/<id>/`: one `theme.json` file and, optionally, an `assets/` folder (wallpapers, sounds). No code to write: the engine and the app read these files.

The fastest way: the app's **Create** tab generates a complete theme from a description, then **Submit to the gallery**.

### 1. Start from an existing theme

Copy `plugin/themes/aurora/` under a new name, in lowercase letters, digits and hyphens (`plugin/themes/space-station/`), then set `id` to the same name.

### 2. Fill in `theme.json`

| Field | Role |
| --- | --- |
| `id`, `name`, `tagline`, `emoji` | Identity. The `id` is also the folder name and the argument of `/ambiance <id>`. |
| `description`, `universe`, `author`, `tags` | Shown in the gallery. |
| `credit` | If the palette comes from another project, its name and license. |
| `season` | For seasonal themes: when they shine (`"December"`). |
| `colors.accent`, `.secondary`, `.muted` | Accent (tab color), banner title, quotes. Hex. |
| `pixelArt` | The animated logo: a `palette` (one letter → one color, `.` = transparent), `fps`, and `frames` of the same size. 20 × 12 pixels recommended (that's 20 × 6 terminal cells). |
| `banner` | Fallback ASCII drawing, shown when there is no pixel art or no room for it, and in Claude's desktop app: 3 lines, 14 columns at most, no emoji. |
| `welcome` | The message shown when the theme is applied. |
| `quotes` | One quote per turn. 5 to 10, short. |
| `spinnerVerbs` | Replace the spinner verbs. Present continuous, no ellipsis. |
| `durationLines` | End-of-turn line. `{d}` becomes the duration: `"Flew for {d}"`. |
| `status.idle`, `status.working` | Status line when idle and during a turn. |
| `moods.error`, `moods.success` | Moods when a check (tests, build) fails or passes: `status`, `quotes`, and optional dedicated pixel-art `frames`. |
| `persona` | Claude's tone, in 1 to 3 sentences. State the tone and the allowed imagery, nothing more. The safety rules are added by the engine. |
| `sounds` | `start`, `success`, `error`: short WAV or OGG files from `assets/` (under a second). |
| `wallpapers` | The wallpapers offered in the app: `{ "name": "…", "file": "assets/…" }`. |
| `terminal` | The terminal colors, in Windows Terminal's color scheme format (the app converts them for iTerm2, Ghostty and kitty): `name` (prefixed with `Claude · `), background, foreground, cursor, selection, the 16 ANSI colors, and `effects`. |
| `terminal.effects` | `backgroundImage` (default wallpaper), `backgroundImageOpacity`, `shader` (`stars`, `embers`, `snow`, `rain`, `petals`, `fireflies`, `bubbles`, `matrix`, `crt`, `glow`), `cursorShape`, `font`. |

The full format is in [docs/theme.schema.json](docs/theme.schema.json). VS Code reads it thanks to the `$schema` line: completion and validation as you type.

### 3. The wallpaper

- 2560 × 1440, JPG quality 90 (under 1 MB), or an animated GIF (under 8 MB).
- **Keep the left and the bottom dark and calm**: that's where the text and the banner go. Put the subject on the right.
- `scripts/art/scenes.py` shows how to paint one in Python (Pillow, NumPy), with the helpers in `scripts/art/paint.py`.

### 4. Try it

- Copy the folder into `~/.ambiance/themes/` (themes there take precedence over the plugin's), or, if you run the app from source, restart `npm run tauri dev`: it installs the repository's themes on startup.
- In a Claude Code session: `/ambiance <id>`.
- `python scripts/build_gallery.py --check` runs the same check as the pull request.

### 5. Submit

Open a pull request with your folder, or use the "Submit a theme" issue form. The automatic check validates: the required fields, the `id` matching the folder name, text contrast (4.5:1 minimum between foreground and background), the pixel art (frames of the same size, every color in the palette), file types and sizes (8 MB per file, 20 MB per theme), and that the sounds and wallpaper it references exist.

**Gallery rules:**
- **No official images, logos, sounds or texts** from existing works. Inspiration is welcome, copies are not.
- For an asset under a free license (CC0, CC-BY), give the source and license in `assets/CREDITS.md`.
- For a palette tribute, the original palette must be under a permissive license, credited in `credit` and in `docs/CREDITS.md`.
- A kind persona: no mocking the user, no shocking content.

## Development

### Prerequisites

- **Plugin**: a recent Claude Code (`claude`) on your PATH. Nothing else: the engine runs inside it.
- **App**: Node 20+ (CI uses 22) and stable Rust, plus the Visual Studio C++ build tools on Windows, the Xcode command line tools on macOS, or `libwebkit2gtk-4.1-dev libayatana-appindicator3-dev librsvg2-dev patchelf` on Linux.
- **Themes and scripts**: Python 3.12 with Pillow (`pip install pillow`); NumPy too for `scripts/art/`; `glslangValidator` (package `glslang-tools`) to check the shaders.

### Run the app

```
cd app
npm install
npm run tauri dev
```

On startup it copies the repository's themes and shaders into `~/.ambiance/` and syncs the terminal profiles.

### Run the checks

These are what CI runs (`.github/workflows/`). Run the ones for the parts you touched:

| Part | Command | From |
| --- | --- | --- |
| Themes | `python scripts/build_gallery.py --check` | repository root |
| Plugin | `claude plugin validate .` then `claude plugin test plugin` | repository root |
| App frontend | `npm run build` (TypeScript and bundle) | `app/` |
| App backend | `cargo clippy --all-targets -- -D warnings` and `cargo test` | `app/src-tauri/` |
| Shaders | `python3 scripts/check_glsl.py` | repository root |

The app is built on Windows, macOS and Linux in CI: if you can only test on one, say which in the pull request.

### Project layout

- `plugin/hooks/register.tsx`: the engine (pixel-art banner, status line, spinner, moods, sounds, persona, companion, `/ambiance`, live switching), tested by `plugin/hooks/register.test.tsx`.
- `plugin/themes/`: the bundled themes. `gallery/` is generated from them by `scripts/build_gallery.py` when themes change on `main`: don't edit it by hand.
- `app/`: the Tauri v2 app. `app/src/` for the interface (TypeScript, no framework), `app/src-tauri/src/` for the system side (terminals, gallery, generator, wallpaper adapter, sounds).
- `app/src-tauri/shaders/`: the effects, generated by `scripts/build_shaders.py` as HLSL (Windows Terminal) and GLSL (Ghostty on macOS and Linux). Edit the script, not the generated files.
- `scripts/art/`: the collection's generators (`collection.py`, `scenes.py`, `sprites.py`, `cities.py`, `city_themes.py`, `sounds.py`, `originals.py`).
- `packaging/`: Homebrew and winget templates, and [code signing](packaging/SIGNING.md).

Files exchanged between the plugin and the app, under `~/.ambiance/`:

| File | Written by | Content |
| --- | --- | --- |
| `themes/<id>/` | the app | installed themes |
| `sessions/<session>.json` | the plugin | the session, its folder, theme and mood, a heartbeat every 5 s |
| `events/<session>.json` | the plugin | the latest mood, which the app turns into a sound |
| `assign/<session>.json` | the app | `{ "theme": "<id>" \| null, "at": <timestamp> }`, reread every 2 s |
| `overrides/<id>.json` | the app | the user's settings: wallpaper, opacity, effect, sounds |
| `config.json` | the app and `/ambiance` | `{ "defaultTheme", "projects", "style", "persona", "sounds", "banner" }` |

### Pull requests

- One topic per pull request. Keep unrelated formatting changes out.
- Add a line under `[Unreleased]` in [CHANGELOG.md](CHANGELOG.md) for anything users will notice.
- By contributing, you agree that your contribution is released under the [MIT license](LICENSE) (assets keep the license you credit them under).

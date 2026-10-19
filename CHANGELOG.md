# Changelog

All notable changes to Ambiance are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
The plugin and the desktop app share one version number.

## [Unreleased]

## [0.3.0] - 2026-10-19

Initial public release.

### Plugin

- A theme per Claude Code session: a label in the prompt footer, a status line entry with the current mood, themed spinner verbs and an end-of-turn line.
- Three styles: `full` (animated pixel-art banner), `compact` (one-line banner) and `minimal` (label and status line only).
- Moods: a failing test or build makes the session "angry", a passing one "proud", with dedicated status, quotes and optional pixel-art frames.
- Mood sounds, on by default in the full style only.
- An opt-in persona that sets the tone of Claude's replies, always followed by engine rules a theme cannot remove.
- An animated companion in a side panel (`/ambiance companion`).
- `/ambiance` to list themes, switch live, or change the style, persona, sounds and banner.
- Theme selection, by priority: the desktop app, `CLAUDE_THEME`, a project's `.ambiance.json`, then the default theme.

### Desktop app (Windows, macOS, Linux)

- **Sessions**: the open Claude Code sessions, with live theme switching.
- **Themes**: per-theme wallpaper (the theme's, a local image or GIF, or an image link), opacity, effect and sounds. Imported wallpapers are cropped, softened and tinted to keep text readable.
- **Discover**: the community gallery, with one-click installs and a bundled fallback when offline.
- **Create**: generates a full theme, pixel art included, from a short description, through the local Claude Code CLI (no API key). Colors are checked and fixed for contrast.
- **Projects** and **New session**: link folders to themes and open Claude Code in an already themed terminal.
- Terminal profiles per theme: Windows Terminal (fragments, HLSL effects), iTerm2 (dynamic profiles), Ghostty (themes, GLSL effects) and kitty.
- Ten live effects: stars, embers, snow, rain, petals, fireflies, bubbles, digital rain, CRT and neon glow.
- Stays in the system tray to play mood sounds when the window is closed (Claude Code plays them itself on macOS).

### Themes

- 33 themes: 10 palette tributes, 10 cities at night, 11 originals and 2 seasonal themes.
- A documented theme format ([docs/theme.schema.json](docs/theme.schema.json)) and an automatic check for submitted themes (`scripts/build_gallery.py --check`).

[Unreleased]: https://github.com/sytem643/claude-code-themes/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/sytem643/claude-code-themes/releases/tag/v0.3.0

# Security policy

## Supported versions

Ambiance is young: only the latest release line gets fixes.

| Version | Supported |
| --- | --- |
| 0.3.x | Yes |
| < 0.3 | No |

## Reporting a vulnerability

Please **do not open a public issue**. Report it privately through GitHub:
[github.com/sytem643/claude-code-themes/security/advisories/new](https://github.com/sytem643/claude-code-themes/security/advisories/new).

Include what you found, how to reproduce it (a proof-of-concept theme or link is ideal), the version and the operating system. You should get a first answer within a week. Once a fix is released, the advisory is published and you are credited, unless you prefer not to be.

## What is in scope

Ambiance is a plugin that runs inside Claude Code and a desktop app that configures your terminals. The parts that deserve scrutiny:

**Community themes.** A theme is meant to be data only: a `theme.json`, images and sounds, never code. The app downloads gallery themes from `raw.githubusercontent.com/sytem643/claude-code-themes/main` over HTTPS, keeps only the file types the gallery allows, refuses absolute paths and `..`, caps each file at 8 MB, and writes them under `~/.ambiance/themes/<id>/`. Anything that lets a theme escape that folder, run a command, or inject settings into a terminal configuration is a vulnerability.

**Terminal configuration.** The app writes, from installed themes:
- a Windows Terminal fragment (`%LOCALAPPDATA%\Microsoft\Windows Terminal\Fragments\Ambiance\ambiance.json`), and touches Windows Terminal's `settings.json` without changing its content so the fragment is reloaded;
- an iTerm2 dynamic profile (`~/Library/Application Support/iTerm2/DynamicProfiles/ambiance.json`), whose profiles start `claude`;
- Ghostty theme files (`~/.config/ghostty/themes/ambiance-<id>`);
- and it passes colors to kitty on the command line when it opens a session there.

Values copied from a theme into these files or arguments must never be able to add settings or commands of their own.

**Launching sessions.** The app opens a terminal in a folder you pick and runs `claude` in it, with `CLAUDE_THEME` set to a theme id (ids are restricted to letters, digits, `-` and `_`).

**Theme generation.** The *Create* tab runs your local `claude` CLI (`claude -p`, through `cmd.exe` on Windows and your login shell on macOS and Linux), with the description on stdin and a temporary folder as working directory. It uses your own Claude Code login: the app holds no API key. The answer is parsed and sanitized before it is saved.

**Wallpapers.** You can import an image from a link: the app downloads it (http or https, 64 MB at most), checks the format from its content and decodes it with the Rust `image` crate. Image decoding bugs that are reachable this way, or through a gallery theme, are in scope.

**The plugin and the persona.** The plugin reads `~/.ambiance/` and a project's `.ambiance.json` (a theme id only). When you turn the persona on (it is off by default), the theme's `persona` text is added to Claude's instructions, followed by rules no theme can remove. A gallery theme whose persona can make Claude act against you (run tools, change code, leak data) is a vulnerability, not just a content problem.

**Other.** The app opens external links only when they start with `https://github.com/`. Its webview runs under a strict content security policy.

## Out of scope

- Problems in Claude Code itself, Windows Terminal, iTerm2, Ghostty or other terminals: report them to their maintainers.
- A theme you wrote and installed yourself doing something to your own machine through a setting the terminal documents.
- Offensive or copied content in a theme: open a regular issue so it can be removed from the gallery.

# How far can a Claude Code terminal be customized?

A map of everything that can be changed in a Claude Code session, what Ambiance does with it, and what it deliberately leaves alone.

## Inside Claude Code (plugin hooks)

Claude Code plugins can hook its interface through `ui.render`, one "site" at a time. Ambiance uses the ones that help tell sessions apart and stay out of the way of your work.

| Site | What it is | Ambiance |
| --- | --- | --- |
| `AbovePrompt` | A band above the prompt | ✅ The banner: animated pixel art (`full`), one line (`compact`), nothing (`minimal`) |
| `SessionMode` | Labels at the right of the prompt footer | ✅ The theme's label (`🌆 Synthwave`), in every style |
| `Spinner` | The "Thinking…" line while Claude works | ✅ Themed verbs (`full`, `compact`) |
| `TurnDuration` | The line closing a turn ("Baked for 3s") | ✅ Themed line (`full`, `compact`) |
| `Pane` | A side panel (fullscreen layout) | ✅ `/ambiance companion`: big animated pixel art, mood and stats |
| Status line (`$.ui.status`) | An entry in the bottom status line | ✅ `🌆 Synthwave · full throttle`, with the mood |
| `PromptHint` | The dim hint under the prompt | ➖ Left alone: it carries useful shortcuts |
| `InfoNotice` | Dim lines under the logo at startup | ➖ Left alone: model and settings notices matter |
| `UserMessage`, `AssistantMessage` | Your prompts and Claude's replies | ❌ Never touched: your conversation stays as is |
| `ToolUse`, `ToolGroup`, `ToolResult` | Tool calls and their results | ❌ Never touched: you need to read what ran |
| `CommandOutput` | Output of slash commands | ➖ Only `/ambiance`'s own output |
| Toasts (`$.ui.toast`) | Short notifications | ✅ One when a theme is applied |
| System prompt (`prompt.compose`) | Instructions sent to the model | ✅ Optional persona, **off by default**, with guardrails no theme can remove |
| Sounds (`$.audio.play`) | Short audio clips (macOS) | ✅ Mood sounds, on in the full style; the app plays them on Windows and Linux |
| Slash commands | `/<name>` | ✅ `/ambiance` |
| Tool calls (`tool.call`) | Observing what runs | ✅ Read-only: a failing or passing check sets the mood. Nothing is blocked or changed |

Rendering details worth knowing:
- A `Raster` element draws colored cells (24-bit), two pixels per cell with `▀`/`▄`: that's how the pixel art and the banner text get exact colors.
- `$.ui.blit` repaints a `Raster` without a full redraw, up to 60 times a second: the pixel art animates at a few frames per second (4 for the bundled themes), which costs nothing noticeable.
- An `Image` element can show real pictures in terminals that speak the kitty graphics protocol (kitty, Ghostty). Elsewhere it falls back to text.

## Claude Code's own settings

Not touched by Ambiance, but good to know:
- `/theme`: dark, light and colorblind-friendly variants of Claude Code's own colors.
- `spinnerVerbs` in `~/.claude/settings.json`: replace or extend the spinner words (Ambiance's plugin hook does it per theme instead).
- `statusLine` in `settings.json`: a script that prints your own status line (tools like claude-powerline build on it). Ambiance adds its entry next to it.
- Output styles: alternative system prompts (Explanatory, Learning, or your own).

## The terminal itself

| | Windows Terminal | iTerm2 (macOS) | Ghostty (macOS, Linux) | kitty (Linux) |
| --- | --- | --- | --- | --- |
| 16-color palette, cursor, selection | ✅ | ✅ | ✅ | ✅ |
| Wallpaper | ✅ PNG, JPG, animated GIF | ✅ | ✅ (1.2+) | ✅ |
| Animated effects (shaders) | ✅ HLSL | ❌ | ✅ GLSL | ❌ |
| Tab color and icon | ✅ | ✅ tab color, badge | ➖ | ➖ |
| Window opacity, blur | ✅ acrylic, opacity | ✅ | ✅ | ✅ |
| Font | ✅ | ✅ | ✅ | ✅ |

This table is what each terminal can do. What Ambiance writes from the theme:
- **Windows Terminal**: a settings fragment with one color scheme and one profile per theme (palette, cursor shape, wallpaper and its opacity, HLSL effect, tab color, emoji icon, font).
- **iTerm2**: dynamic profiles (palette, cursor and selection colors, wallpaper, tab color, badge).
- **Ghostty**: theme files (palette, cursor and selection colors, wallpaper and its opacity, GLSL effect).
- **kitty**: the same colors and the wallpaper, passed as options when the app opens a session.

Window opacity and blur are left to your own terminal settings.

macOS Terminal.app has no 24-bit color, so the pixel art is approximated there. iTerm2 or Ghostty give the full result.

## The 10 effects

`stars`, `embers`, `snow`, `rain`, `petals`, `fireflies`, `bubbles`, `matrix`, `crt`, `glow`. Each one paints only over the dark background, so the text stays sharp. They're generated from one source by `scripts/build_shaders.py`: HLSL for Windows Terminal, GLSL for Ghostty. Each theme picks one, and the app's *Customize* sheet can switch it or turn it off.

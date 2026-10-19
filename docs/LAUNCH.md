# Launch checklist

For the maintainer: what to do around the first public release (v0.3.0), in order.
Lists and rules were checked in October 2026; re-read each one's rules before you submit.

## 1. Before the repository goes public

- [ ] CI is green on `main`: `plugin.yml`, `app.yml`, `themes.yml`.
- [ ] Clean install test on a machine (or user account) without Ambiance:
      `claude plugin install ambiance --marketplace sytem643/claude-code-themes`, then open a session and run `/ambiance`.
- [ ] `claude plugin validate --strict .` passes locally.
- [ ] The README renders well in **both** GitHub themes (switch in Settings → Appearance): the banner, the badges, the demo GIF and the tables.
- [ ] Images are up to date: `python scripts/art/social.py` (banner and social card), `python scripts/art/demo_gif.py` (demo and showcase).
- [ ] No secrets, personal paths or test files in the tree: `git ls-files | less`.

## 2. Configure the repository

- [ ] Run `scripts/github/setup.sh` (needs `gh auth login` with admin rights). It sets the description, the topics, the labels, enables Issues and Discussions, disables the Wiki and Projects, and turns on private vulnerability reporting and Dependabot alerts. Safe to run again.
- [ ] **Social preview** (no API for it): Settings → General → Social preview → Edit → Upload `docs/social-preview.png`. Check it by pasting the repo link in a Discord or Slack DM.
- [ ] Discussions → set up categories: Announcements, Q&A, Ideas, Show and tell.
- [ ] Settings → Branches: protect `main` (require the CI checks, no force push).

## 3. Release v0.3.0

- [ ] Move the `[Unreleased]` notes in `CHANGELOG.md` under `[0.3.0]` if needed, commit.
- [ ] Tag and push:
      ```sh
      git tag -a v0.3.0 -m "Ambiance 0.3.0"
      git push origin v0.3.0
      ```
      `release.yml` builds Windows, macOS (universal) and Linux and attaches the installers to a **draft** release "Ambiance v0.3.0".
- [ ] Edit the draft before publishing:
  - Paste the 0.3.0 section of the changelog.
  - Drag in `docs/showcase.png` and `docs/demo.gif` (the release page is often the first thing people open).
  - Two install lines: the plugin command above, and "download the installer for your system below".
  - If the installers are unsigned (no secrets set, see `packaging/SIGNING.md`), say so and how to get past SmartScreen / Gatekeeper.
- [ ] Publish, marked as **latest**. Download each installer once to check it opens.
- [ ] Fill `packaging/homebrew/ambiance.rb` and `packaging/winget/Ambiance.Ambiance.yaml` with the version and SHA-256s
      (`gh release download v0.3.0 -D /tmp/amb && sha256sum /tmp/amb/*`), then publish the cask in `sytem643/homebrew-tap` and open the winget-pkgs PR.

## 4. Make it welcoming

- [ ] Pin the repository on your profile (Profile → Customize your pins).
- [ ] Seed 5 to 8 **good first issues**, labeled `good first issue` + `theme`, each with: the idea, a reference link (palette repo and its license, or a photo source), and a pointer to `CONTRIBUTING.md` and `docs/theme.schema.json`. Ideas:
  - Palette tributes (check the license is MIT or similar first): Kanagawa, Ayu, Night Owl.
  - Cities at night: Berlin, Hong Kong, Istanbul, Mexico City.
  - Seasonal: Lunar New Year, spring.
  - Non-theme: more spinner verbs or quotes for an existing theme; a screenshot of a terminal not yet in the README table.
- [ ] Discussions: an Announcements **welcome post** (what Ambiance is, where to ask, how to propose a theme, the roadmap in three lines), pinned.
- [ ] Show and tell: a **"Show your setup"** thread ("post a screenshot of your themed session: terminal, theme, style"), pinned. Seed it with your own screenshot.

## 5. Directories and curated lists

Submit once per list, with the same plain one-liner, for example:
`Ambiance - per-session themes for Claude Code: pixel-art banner, session label and a status line that reacts to tests, plus a desktop app that themes the terminal.`

- [ ] **Anthropic's plugin directory** (claude.ai, Cowork and Claude Code through account sync): submit from the developer portal at <https://claude.ai/directory/manage> (needs a paid claude.ai plan). Run the pre-submission checklist first: <https://claude.com/docs/plugins/pre-submission-checklist>. Check the component support table, since the status line and hooks are Claude Code features. The official `claude-plugins-official` marketplace does not take submissions; the community marketplace (`anthropics/claude-plugins-community`) is fed by these submissions, not by PRs.
- [ ] **[hesreallyhim/awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code)**: web issue form only ("Recommend a new resource"), no PR, no `gh`, submitted by a human. The repo must be **at least 14 days old** (from the first commit) with commits after the first day, or have 100+ stars. One line, describes what it does, no emoji, no sales pitch. Put a date in your calendar.
- [ ] **[jqueryscript/awesome-claude-code](https://github.com/jqueryscript/awesome-claude-code)**, **[ccplugins/awesome-claude-code-plugins](https://github.com/ccplugins/awesome-claude-code-plugins)**, **[composio-community/awesome-claude-plugins](https://github.com/composio-community/awesome-claude-plugins)**: read each `CONTRIBUTING`, usually a one-line PR.
- [ ] **[tauri-apps/awesome-tauri](https://github.com/tauri-apps/awesome-tauri)**: Applications section, PR, once the release is out.
- [ ] Palette communities (Dracula, Catppuccin, Rosé Pine, Nord…): their official ports live in their own organizations, so don't submit as a port. Share in their showcase channels at most, and credit them (already in `docs/CREDITS.md`).

## 6. Communities

Space the posts over a few days, answer every comment, and never ask for upvotes.

- [ ] **r/unixporn**: read the sidebar rules first (they are strict and change). Setups go under the Screenshot flair, themes and tools under Material. Titles look like `[Ghostty] Ambiance: a theme per Claude Code session`. Post a native image or video, not a link, and add the details (terminal, font, theme, link) in a top comment.
- [ ] **r/ClaudeAI**, **r/ClaudeCode**: check their self-promotion rules; lead with the problem (telling sessions apart), not the pixel art.
- [ ] Ghostty / Windows Terminal / kitty communities: "show and tell" spaces only.
- [ ] X, Bluesky, Mastodon: upload `docs/demo.gif` natively, one sentence, then the link. The social card shows when the link is pasted.

## 7. Show HN

Rules: <https://news.ycombinator.com/showhn.html>. Ambiance qualifies (something people can run, no signup).

- **Title** (80 characters max, plain, no superlatives): `Show HN: Ambiance – themes for Claude Code sessions, with pixel art and shaders` (79 characters)
- **URL**: the GitHub repository.
- **First comment** right after posting, 150 to 250 words:
  1. The problem: several Claude Code sessions that look the same, typing in the wrong one.
  2. What it does: a label and a mood-aware status line per session; optional pixel art, wallpapers and shaders.
  3. How it works: a plugin (hooks + status line, no network), a Tauri app that writes Windows Terminal fragments, iTerm2 dynamic profiles and Ghostty themes without touching existing settings; themes are plain JSON, art generated by Python scripts.
  4. What's off by default (persona, sounds in compact/minimal) and that it's an unofficial project.
  5. What feedback you want (terminals to support, theme ideas).
- **Timing**: a weekday morning, US Pacific time (Tuesday to Thursday, 8 to 10 am PT is the usual advice). Keep the next 3 to 4 hours free to answer.
- Don't send the direct link to friends to vote: HN's ring detection penalizes it.

## 8. Launch post outline

For a blog, dev.to or a pinned X/Bluesky thread:

1. **Hook**: "I run three Claude Code sessions at once and kept typing in the wrong one."
2. **GIF**: `docs/demo.gif`.
3. **What you get**, three bullets: a label per session, a status line that reacts to tests, one theme per project via `.ambiance.json`.
4. **The fun part** (optional): 33 themes, pixel art, wallpapers, live shaders.
5. **Install**: the plugin command and the releases link.
6. **How it's built**: one paragraph, a link to the scripts.
7. **Call for themes**: link to the theme issue template and the good first issues.
8. **Credits**: the palette projects and the photographers (`docs/CREDITS.md`); unofficial, not affiliated with Anthropic.

## 9. First week

- [ ] Answer new issues within a day; label and thank.
- [ ] Watch Insights → Traffic (referrers) to see which channel worked.
- [ ] Ship quick fixes as v0.3.1 rather than waiting.
- [ ] If listed in awesome-claude-code, add their badge to the README.

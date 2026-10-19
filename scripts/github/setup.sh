#!/usr/bin/env bash
# Configures the GitHub repository: description, topics, features and labels.
# Idempotent: run it again whenever this file changes.
#
# Usage: REPO=owner/name scripts/github/setup.sh   (needs `gh auth login`, admin rights)
#
# Not covered by the API, to do by hand (see docs/LAUNCH.md):
#   - Settings → General → Social preview: upload docs/social-preview.png.
#   - Pinning the repository on your profile.
set -euo pipefail

REPO="${REPO:-sytem643/claude-code-themes}"

command -v gh >/dev/null || { echo "gh is required: https://cli.github.com" >&2; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "Run 'gh auth login' first." >&2; exit 1; }

echo "Configuring $REPO"

# ---------- About ----------

DESCRIPTION="Themes for Claude Code sessions: a plugin with animated pixel-art banners, session labels and a status line that reacts to your tests, plus a desktop app that themes your terminal (Windows Terminal, iTerm2, Ghostty, kitty) with palettes, wallpapers and live shaders. 33 themes."

# Empty homepage: the README is the landing page. Set HOMEPAGE to override.
HOMEPAGE="${HOMEPAGE:-}"

gh repo edit "$REPO" \
  --description "$DESCRIPTION" \
  --homepage "$HOMEPAGE" \
  --enable-issues \
  --enable-discussions \
  --enable-wiki=false \
  --enable-projects=false \
  --delete-branch-on-merge \
  --allow-update-branch

# ---------- Topics ----------
# GitHub allows 20: lowercase, digits and hyphens, 50 characters at most.

TOPICS=(
  claude-code
  claude-code-plugin
  claude
  anthropic
  themes
  terminal-themes
  color-schemes
  pixel-art
  windows-terminal
  iterm2
  ghostty
  kitty
  terminal
  shaders
  wallpapers
  tauri
  ricing
  developer-tools
  productivity
  cli
)

# Replaces the whole list, so removed topics disappear too.
topic_args=()
for topic in "${TOPICS[@]}"; do
  topic_args+=(-f "names[]=$topic")
done
gh api --method PUT "repos/$REPO/topics" -H "Accept: application/vnd.github+json" "${topic_args[@]}" >/dev/null
echo "  topics: ${#TOPICS[@]}"

# ---------- Security ----------
# The issue template links to private vulnerability reporting.

gh api --method PUT "repos/$REPO/private-vulnerability-reporting" >/dev/null
gh api --method PUT "repos/$REPO/vulnerability-alerts" >/dev/null
gh api --method PUT "repos/$REPO/automated-security-fixes" >/dev/null

# ---------- Labels ----------
# name|color|description. --force updates labels that already exist.

LABELS=(
  "theme|ff7edb|A new theme or a change to one"
  "bug|d73a4a|Something doesn't work"
  "enhancement|5e9cff|A new feature or an improvement"
  "documentation|0075ca|README, docs or comments"
  "good first issue|7057ff|A good place to start contributing"
  "help wanted|008672|Extra attention is welcome"
  "app|e8c887|The desktop app (Tauri)"
  "plugin|bd93f9|The Claude Code plugin"
  "dependencies|0366d6|Dependency updates"
  "question|d876e3|Better asked in Discussions"
  "duplicate|cfd3d7|Already reported"
  "wontfix|ffffff|Out of scope"
)

for entry in "${LABELS[@]}"; do
  IFS="|" read -r name color description <<<"$entry"
  gh label create "$name" --repo "$REPO" --color "$color" --description "$description" --force >/dev/null
  echo "  label: $name"
done

echo "Done. Upload docs/social-preview.png by hand: https://github.com/$REPO/settings"

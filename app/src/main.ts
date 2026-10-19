import { getVersion } from '@tauri-apps/api/app'
import { invoke } from '@tauri-apps/api/core'
import { listen } from '@tauri-apps/api/event'
import { ask, open } from '@tauri-apps/plugin-dialog'

import { INSTALL_COMMAND, REPO_URL } from './config'
import { EFFECTS, startEffect } from './effects'
import { pixelSvg, type PixelArt } from './pixel'

const POLL_MS = 2000

type Override = {
  backgroundImage?: string | null
  backgroundImageOpacity?: number
  shader?: string | null
  sounds?: boolean
}

type Theme = {
  id: string
  name: string
  tagline?: string
  description?: string
  universe?: string
  author?: string
  emoji?: string
  colors?: { accent?: string; secondary?: string; muted?: string }
  banner?: string[]
  pixelArt?: PixelArt
  quotes?: string[]
  spinnerVerbs?: string[]
  status?: { idle?: string; working?: string }
  moods?: Record<string, { status?: string; quotes?: string[] }>
  persona?: string[]
  sounds?: Record<string, string>
  wallpapers?: { name: string; file: string }[]
  terminal?: Record<string, string> & {
    effects?: { backgroundImage?: string; backgroundImageOpacity?: number; shader?: string | null }
  }
  isBundled?: boolean
  override?: Override
}

type Session = {
  id: string
  cwd: string
  theme: string | null
  mood?: string
  isWorking: boolean
  startedAt: number
  stats?: { turns: number; tools: number; errors: number }
}

type GalleryEntry = {
  id: string
  name: string
  tagline?: string
  description?: string
  emoji?: string
  author?: string
  universe?: string
  colors?: Theme['colors']
  background?: string
  preview?: string
}

type View = 'sessions' | 'themes' | 'discover' | 'create' | 'projects' | 'launch' | 'settings'

const state = {
  view: 'sessions' as View,
  themes: [] as Theme[],
  sessions: [] as Session[],
  config: {} as {
    defaultTheme?: string | null
    style?: 'full' | 'compact' | 'minimal'
    persona?: boolean
    sounds?: boolean
    banner?: boolean
    projects?: Record<string, string>
  },
  isPluginInstalled: false,
  platform: '',
  version: '',
  dataDir: '',
  launchDir: load('launchDir') ?? '',
  launchTheme: load('launchTheme'),
  openMenu: null as string | null,
  sessionsKey: '',
  tick: 0,
  pixelTick: 0,
  editing: null as string | null,
  intensity: 0.5,
  gallery: null as null | { source: string; index: { weekly?: string; themes: GalleryEntry[] } },
  installing: null as string | null,
  prompt: '',
  generating: false,
  draft: null as Theme | null,
  family: 'all',
}

const assets = new Map<string, Promise<string | undefined>>()
const thumbs = new Map<string, Promise<string | undefined>>()
let stopEffect: () => void = () => undefined

const TITLES: Record<View, [string, string]> = {
  sessions: ['Sessions', 'Your open Claude Code sessions. Switch their theme on the fly.'],
  themes: ['Themes', 'Wallpapers, effects, sounds and pixel art: make every theme yours.'],
  discover: ['Discover', 'Community themes, one click to install.'],
  create: ['Create', 'Describe a vibe, Claude designs the theme.'],
  projects: ['Projects', 'Every project opens Claude Code in its own theme.'],
  launch: ['New session', 'Open Claude Code in the terminal, already themed.'],
  settings: ['Settings', 'Default theme, plugin, sounds and terminal.'],
}

const STYLE_HINTS = {
  full: 'An animated pixel-art banner above the prompt, and the mood sounds.',
  compact: 'A one-line banner above the prompt.',
  minimal: 'Only the status line, the session label and the terminal colors.',
}

const ICON = {
  chevron: '<svg class="chevron" viewBox="0 0 24 24"><path d="m7 10 5 5 5-5"/></svg>',
  check: '<svg class="check" viewBox="0 0 24 24"><path d="m5 12.5 4.5 4.5L19 7.5"/></svg>',
  folder: '<svg viewBox="0 0 24 24"><path d="M3.5 7.5a2 2 0 0 1 2-2h4l2 2h7a2 2 0 0 1 2 2v7.5a2 2 0 0 1-2 2h-13a2 2 0 0 1-2-2Z"/></svg>',
  terminal: '<svg viewBox="0 0 24 24"><rect x="3" y="4.5" width="18" height="15" rx="3"/><path d="m7 10 3 2.5L7 15M12.5 15H17"/></svg>',
  star: '<svg viewBox="0 0 24 24"><path d="m12 4 2.4 5 5.4.6-4 3.7 1.1 5.3L12 16l-4.9 2.6 1.1-5.3-4-3.7 5.4-.6Z"/></svg>',
  copy: '<svg viewBox="0 0 24 24"><rect x="8" y="8" width="11" height="11" rx="2.5"/><path d="M16 8V6.5A1.5 1.5 0 0 0 14.5 5h-8A1.5 1.5 0 0 0 5 6.5v8A1.5 1.5 0 0 0 6.5 16H8"/></svg>',
  rocket: '<svg viewBox="0 0 24 24"><path d="M5 19c0-3 1-5 3-6M12 15l-3-3c1.5-4.5 5-7.5 10-8-.5 5-3.5 8.5-8 10Z"/><circle cx="14.5" cy="9.5" r="1.4"/></svg>',
  brush: '<svg viewBox="0 0 24 24"><path d="M14.5 4.5 19.5 9.5 11 18l-5-5Z"/><path d="M6 13c-2 0-3 1.5-3 3.5V20h3.5C8.5 20 10 19 10 17"/></svg>',
  sparkles: '<svg viewBox="0 0 24 24"><path d="M12 3.5 13.6 8.4 18.5 10 13.6 11.6 12 16.5 10.4 11.6 5.5 10 10.4 8.4Z"/><path d="M18.5 15.5l.8 2.2 2.2.8-2.2.8-.8 2.2-.8-2.2-2.2-.8 2.2-.8Z"/></svg>',
  play: '<svg viewBox="0 0 24 24"><path d="M8 5.5v13l10-6.5Z"/></svg>',
  close: '<svg viewBox="0 0 24 24"><path d="m7 7 10 10M17 7 7 17"/></svg>',
  download: '<svg viewBox="0 0 24 24"><path d="M12 4v11M7.5 10.5 12 15l4.5-4.5M5 19.5h14"/></svg>',
  image: '<svg viewBox="0 0 24 24"><rect x="3.5" y="5" width="17" height="14" rx="2.5"/><circle cx="9" cy="10" r="1.6"/><path d="m4 17 5-4.5 4 3.5 3-2.5 4 3.5"/></svg>',
}

function load(key: string): string | null {
  try {
    return localStorage.getItem(`ambiance.${key}`)
  } catch {
    return null
  }
}

function save(key: string, value: string | null) {
  try {
    if (value === null) localStorage.removeItem(`ambiance.${key}`)
    else localStorage.setItem(`ambiance.${key}`, value)
  } catch {
    // A display preference only: we can do without it.
  }
}

const esc = (value: unknown) =>
  String(value ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!)

const themeById = (id: string | null | undefined) => state.themes.find(t => t.id === id)

const folderName = (path: string) => path.split(/[\\/]/).filter(Boolean).pop() ?? path

function ago(ms: number): string {
  const minutes = Math.floor((Date.now() - ms) / 60000)
  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${minutes} min ago`
  const hours = Math.floor(minutes / 60)
  return hours < 24 ? `${hours} h ago` : `${Math.floor(hours / 24)} d ago`
}

function hud(text: string) {
  const el = document.getElementById('hud')!
  el.textContent = text
  el.classList.add('is-shown')
  window.clearTimeout(Number(el.dataset.timer))
  el.dataset.timer = String(window.setTimeout(() => el.classList.remove('is-shown'), 2600))
}

async function call<T>(command: string, args?: Record<string, unknown>): Promise<T | undefined> {
  try {
    return await invoke<T>(command, args)
  } catch (error) {
    hud(`Error: ${String(error)}`)
    return undefined
  }
}

/** A theme file as a data URL, asked for once and then cached. */
function cachedInvoke(cache: Map<string, Promise<string | undefined>>, command: string, themeId: string, path: string) {
  const key = `${themeId}|${path}`
  let pending = cache.get(key)
  if (pending === undefined) {
    pending = invoke<string>(command, { id: themeId, path }).catch(() => undefined)
    cache.set(key, pending)
  }
  return pending
}

const asset = (themeId: string, path: string) => cachedInvoke(assets, 'theme_asset', themeId, path)

/** A wallpaper for the previews: a small cached copy, made once by the app. */
const thumb = (themeId: string, path: string) => cachedInvoke(thumbs, 'theme_thumb', themeId, path)

/** The wallpaper in effect for a theme: the user's own, another one from the theme, or its default. */
function wallpaperOf(theme: Theme): string | null {
  const custom = theme.override?.backgroundImage
  if (custom === null) return null
  if (typeof custom === 'string') return custom.startsWith('theme:') ? custom.slice('theme:'.length) : custom
  return theme.terminal?.effects?.backgroundImage ?? null
}

function shaderOf(theme: Theme): string | null {
  const custom = theme.override?.shader
  return custom !== undefined ? custom : (theme.terminal?.effects?.shader ?? null)
}

// Wallpapers load when their card scrolls near the screen, not all at once.
const wallObserver = new IntersectionObserver(
  entries => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue
      const el = entry.target as HTMLElement
      wallObserver.unobserve(el)
      void thumb(el.dataset.wallTheme!, el.dataset.wallPath!).then(url => {
        if (url !== undefined) el.style.backgroundImage = `url("${url}")`
      })
    }
  },
  { rootMargin: '400px' },
)

function hydrateImages() {
  document.querySelectorAll<HTMLElement>('[data-wall-theme]').forEach(el => wallObserver.observe(el))
}

/** Sounds follow the style unless the user chose: on in the full style. */
function soundsOn(): boolean {
  return state.config.sounds ?? (state.config.style ?? 'full') === 'full'
}

// ---------- Rendering ----------

function termVars(theme: Theme): string {
  const t = theme.terminal ?? {}
  const c = theme.colors ?? {}
  return [
    `--t-bg:${t.background ?? '#1e1e1e'}`,
    `--t-fg:${t.foreground ?? '#e5e5e5'}`,
    `--t-accent:${c.accent ?? t.blue ?? '#7aa2ff'}`,
    `--t-secondary:${c.secondary ?? t.purple ?? '#c099ff'}`,
    `--t-muted:${c.muted ?? t.brightBlack ?? '#999'}`,
  ].join(';')
}

function logo(theme: Theme): string {
  if (theme.pixelArt?.frames?.length) {
    return `<span class="term-pixel" data-pixel="${esc(theme.id)}">${pixelSvg(theme.pixelArt, state.pixelTick)}</span>`
  }
  return theme.banner?.length ? `<pre class="term-art">${esc(theme.banner.join('\n'))}</pre>` : ''
}

function preview(theme: Theme, seed = 0, options: { wall?: boolean } = {}): string {
  const verbs = theme.spinnerVerbs?.length ? theme.spinnerVerbs : ['Thinking']
  const quotes = theme.quotes?.length ? theme.quotes : [theme.name]
  const verb = verbs[(seed + state.tick) % verbs.length]
  const quote = quotes[seed % quotes.length]
  const t = theme.terminal ?? {}
  const wall = options.wall === false ? null : wallpaperOf(theme)
  const palette = ['red', 'green', 'yellow', 'blue', 'purple', 'cyan'].map(k => `<i style="background:${esc(t[k] ?? 'transparent')}"></i>`).join('')
  return `
    <div class="term" style="${esc(termVars(theme))}">
      <div class="term-bar"><i></i><i></i><i></i><span>${esc(theme.name)} — claude</span></div>
      <div class="term-body">
        ${wall ? `<div class="term-wall" data-wall-theme="${esc(theme.id)}" data-wall-path="${esc(wall)}" style="opacity:${theme.override?.backgroundImageOpacity ?? theme.terminal?.effects?.backgroundImageOpacity ?? 0.6}"></div>` : ''}
        <div class="term-content">
          <div class="term-banner">
            ${logo(theme)}
            <div>
              <div class="term-title">${esc(theme.name.toUpperCase())}${theme.tagline ? ` · ${esc(theme.tagline)}` : ''}</div>
              <div class="term-quote">“${esc(quote)}”</div>
            </div>
          </div>
          <div class="term-you"><b>›</b> fix the login bug</div>
          <div class="term-spin"><em>✻</em> <span data-verb="${esc(theme.id)}">${esc(verb)}</span>…</div>
          <div class="term-status">${esc(theme.emoji ?? '')} ${esc(theme.name)} · ${esc(theme.status?.working ?? 'working')}</div>
          <div class="term-palette">${palette}</div>
        </div>
      </div>
    </div>`
}

function swatch(theme: Theme | undefined): string {
  if (theme === undefined) return '<span class="swatch is-none">–</span>'
  const bg = theme.terminal?.background ?? '#222'
  const accent = theme.colors?.accent ?? '#888'
  return `<span class="swatch" style="background:linear-gradient(135deg, ${esc(bg)} 55%, ${esc(accent)})">${esc(theme.emoji ?? '')}</span>`
}

function picker(menuId: string, selected: string | null, noneLabel = 'No theme'): string {
  const current = themeById(selected)
  const isOpen = state.openMenu === menuId
  const items = state.themes
    .map(
      t => `
      <button class="menu-item" data-pick="${esc(menuId)}" data-theme="${esc(t.id)}">
        ${swatch(t)}
        <span><div>${esc(t.name)}</div><div class="menu-sub">${esc(t.tagline ?? '')}</div></span>
        ${t.id === selected ? ICON.check : ''}
      </button>`,
    )
    .join('')
  return `
    <div class="picker">
      <button class="picker-button" data-menu="${esc(menuId)}">
        ${swatch(current)}<span>${esc(current?.name ?? noneLabel)}</span>${ICON.chevron}
      </button>
      ${
        isOpen
          ? `<div class="menu">${items}<div class="menu-sep"></div>
              <button class="menu-item" data-pick="${esc(menuId)}" data-theme="">
                ${swatch(undefined)}<span>${esc(noneLabel)}</span>${selected === null ? ICON.check : ''}
              </button></div>`
          : ''
      }
    </div>`
}

function moodLabel(session: Session): string {
  const theme = themeById(session.theme)
  const mood = session.mood && session.mood !== 'idle' ? theme?.moods?.[session.mood]?.status : undefined
  return mood ?? (session.isWorking ? (theme?.status?.working ?? 'working') : (theme?.status?.idle ?? 'idle'))
}

function renderSessions(): string {
  if (state.sessions.length === 0) {
    return `
      <div class="empty">
        ${ICON.terminal}
        <h2>No open sessions</h2>
        <p>Claude Code sessions with the Ambiance plugin show up here automatically.</p>
        <button class="btn is-primary" data-go="launch">Start a session</button>
      </div>`
  }
  const rows = state.sessions
    .map(s => {
      const dot = s.mood === 'error' ? 'is-error' : s.mood === 'success' ? 'is-on' : s.isWorking ? 'is-working' : 'is-on'
      const stats = s.stats ? ` · ${s.stats.turns} turns` : ''
      return `
      <div class="row">
        <span class="dot ${dot}"></span>
        <div class="row-main">
          <div class="row-title">${esc(folderName(s.cwd))}</div>
          <div class="row-sub">${esc(moodLabel(s))} · opened ${esc(ago(s.startedAt))}${stats} · ${esc(s.cwd)}</div>
        </div>
        ${picker(`session:${s.id}`, s.theme)}
      </div>`
    })
    .join('')
  const count = state.sessions.length
  return `<div class="section-title">${count} open session${count > 1 ? 's' : ''}</div>
    <div class="group">${rows}</div>
    <p class="row-note" style="margin:12px 4px">The banner, status line and spinner switch instantly; Claude's tone, from the next message. Wallpaper and terminal colors apply to new sessions.</p>`
}

function renderThemes(): string {
  if (state.themes.length === 0) {
    return `<div class="empty">${ICON.star}<h2>No themes installed</h2><p>Head to Discover or Create.</p></div>`
  }
  // Families: palette tributes, originals, seasonal themes.
  const familyOf = (t: Theme) =>
    t.universe?.includes('Seasonal')
      ? 'Seasonal'
      : t.universe === 'City'
        ? 'Cities'
        : !t.universe || t.universe.startsWith('Original')
          ? 'Originals'
          : t.universe === 'Palette tribute'
            ? 'Palette tributes'
            : t.universe
  const ORDER = ['Palette tributes', 'Cities', 'Originals', 'Seasonal']
  const families = [...new Set(state.themes.map(familyOf))].sort((a, b) => (ORDER.indexOf(a) + 1 || 99) - (ORDER.indexOf(b) + 1 || 99))
  const shown = state.family === 'all' ? state.themes : state.themes.filter(t => familyOf(t) === state.family)
  const chip = (id: string, label: string, count: number) =>
    `<button class="chip ${state.family === id ? 'is-selected' : ''}" data-family="${esc(id)}">${esc(label)} <span class="chip-count">${count}</span></button>`
  const filters = [
    chip('all', 'All', state.themes.length),
    ...families.map(f => chip(f, f, state.themes.filter(t => familyOf(t) === f).length)),
  ].join('')
  return `<div class="chips theme-filters">${filters}</div>
  <div class="gallery">${shown
    .map(
      (t, i) => `
      <article class="theme-card">
        ${preview(t, i)}
        <div class="theme-meta">
          <div style="flex:1">
            <div class="theme-name">${esc(t.emoji ?? '')} ${esc(t.name)}</div>
            <div class="theme-desc">${esc(t.description ?? t.tagline ?? '')}</div>
          </div>
          ${t.universe ? `<span class="tag">${esc(t.universe)}</span>` : ''}
        </div>
        <div class="theme-actions">
          <button class="btn" data-edit="${esc(t.id)}">${ICON.brush} Customize</button>
          ${state.config.defaultTheme === t.id ? `<span class="tag">${ICON.star} Default</span>` : `<button class="btn is-quiet" data-default="${esc(t.id)}">Set as default</button>`}
          <span class="spacer"></span>
          <button class="btn is-primary" data-launch-with="${esc(t.id)}">${ICON.rocket} Launch</button>
        </div>
      </article>`,
    )
    .join('')}</div>`
}

function renderEditor(theme: Theme): string {
  const current = theme.override?.backgroundImage
  const own = typeof current === 'string' && !current.startsWith('theme:') ? current : null
  const selectedWall = wallpaperOf(theme)
  const walls = (theme.wallpapers ?? []).map(
    w => `
      <button class="wall ${selectedWall === w.file ? 'is-selected' : ''}" data-wall="theme:${esc(w.file)}">
        <span class="wall-image" data-wall-theme="${esc(theme.id)}" data-wall-path="${esc(w.file)}"></span>
        <span class="wall-name">${esc(w.name)}</span>
      </button>`,
  )
  if (own !== null) {
    walls.push(`
      <button class="wall is-selected" data-wall="${esc(own)}">
        <span class="wall-image" data-wall-theme="${esc(theme.id)}" data-wall-path="${esc(own)}"></span>
        <span class="wall-name">My image</span>
      </button>`)
  }
  walls.push(`
      <button class="wall ${selectedWall === null ? 'is-selected' : ''}" data-wall="none">
        <span class="wall-image is-none">–</span><span class="wall-name">No wallpaper</span>
      </button>`)

  const shader = shaderOf(theme)
  const opacity = theme.override?.backgroundImageOpacity ?? theme.terminal?.effects?.backgroundImageOpacity ?? 0.6
  const sounds = Object.entries(theme.sounds ?? {})
  const soundLabels: Record<string, string> = { start: 'Arrival', success: 'Success', error: 'Failure' }

  return `
    <div class="sheet-backdrop" data-close-sheet></div>
    <section class="sheet" role="dialog" aria-label="Customize ${esc(theme.name)}">
      <header class="sheet-head">
        <div>
          <h2>${esc(theme.emoji ?? '')} ${esc(theme.name)}</h2>
          <p>These settings stay on your computer.</p>
        </div>
        <button class="icon-btn" data-close-sheet aria-label="Close">${ICON.close}</button>
      </header>
      <div class="sheet-body">
        <div class="sheet-preview">
          ${preview(theme)}
          <canvas class="effect-canvas" id="effect-canvas"></canvas>
        </div>

        <div class="section-title">Wallpaper</div>
        <div class="walls">${walls.join('')}</div>
        <div class="group" style="margin-top:12px">
          <div class="row">
            <div class="row-main">
              <div class="row-title">Your own image</div>
              <div class="row-sub">PNG, JPG, WebP, animated GIF, BMP, TIFF or ICO. Ambiance crops it, softens it and tints it with the theme's colors so text stays readable.</div>
            </div>
            <button class="btn" id="pick-wallpaper">${ICON.image} Choose…</button>
          </div>
          <div class="row">
            <div class="row-main">
              <div class="row-title">From the web</div>
              <div class="row-sub">Paste an image link (right-click an image, then “Copy image address”). Any format above works, WebP included.</div>
            </div>
          </div>
          <div class="row">
            <input class="input" id="wallpaper-url" type="url" placeholder="https://…/image.webp" spellcheck="false" />
            <button class="btn" id="import-wallpaper">${ICON.image} Import</button>
          </div>
          <div class="row">
            <div class="row-main"><div class="row-title">Adaptation</div><div class="row-sub">From a light to a strong tint</div></div>
            <input type="range" class="slider" id="intensity" min="0" max="1" step="0.05" value="${state.intensity}" />
          </div>
          <div class="row">
            <div class="row-main"><div class="row-title">Wallpaper strength</div><div class="row-sub">Opacity in the terminal</div></div>
            <input type="range" class="slider" id="opacity" min="0.1" max="1" step="0.05" value="${opacity}" />
          </div>
        </div>

        <div class="section-title">Animated effect</div>
        <div class="segmented">
          ${EFFECTS.map(fx => `<button class="${fx.id === shader ? 'is-selected' : ''}" data-effect="${fx.id ?? ''}">${esc(fx.name)}</button>`).join('')}
        </div>

        ${
          sounds.length
            ? `<div class="section-title">Mood sounds</div>
          <div class="group">
            <div class="row">
              <div class="row-main"><div class="row-title">Play sounds</div><div class="row-sub">When a test passes or fails, or when the theme arrives.</div></div>
              <label class="switch"><input type="checkbox" id="theme-sounds" ${theme.override?.sounds === false ? '' : 'checked'} /><span></span></label>
            </div>
            <div class="row">${sounds.map(([kind]) => `<button class="btn" data-play="${esc(kind)}">${ICON.play} ${esc(soundLabels[kind] ?? kind)}</button>`).join('')}</div>
          </div>`
            : ''
        }

        <div class="sheet-foot">
          ${theme.isBundled ? '' : `<button class="btn is-danger" id="delete-theme">Delete</button><button class="btn" id="share-theme">${ICON.sparkles} Submit to the gallery</button>`}
          <span class="spacer"></span>
          <button class="btn is-primary" data-launch-with="${esc(theme.id)}">${ICON.rocket} Try it in the terminal</button>
        </div>
      </div>
    </section>`
}

function renderDiscover(): string {
  if (state.gallery === null) return '<div class="empty"><div class="spinner"></div><p>Loading the gallery…</p></div>'
  const installed = new Set(state.themes.map(t => t.id))
  const list = state.gallery.index.themes ?? []
  const weekly = list.find(t => t.id === state.gallery?.index.weekly)
  const card = (t: GalleryEntry) => `
    <article class="discover-card" style="--d-bg:${esc(t.background ?? '#222')};--d-accent:${esc(t.colors?.accent ?? '#888')}">
      <div class="discover-art">${themeById(t.id)?.pixelArt ? `<span data-pixel="${esc(t.id)}">${pixelSvg(themeById(t.id)!.pixelArt!, state.pixelTick)}</span>` : `<span class="discover-emoji">${esc(t.emoji ?? '✦')}</span>`}</div>
      <div class="discover-meta">
        <div class="theme-name">${esc(t.name)}</div>
        <div class="theme-desc">${esc(t.description || t.tagline || '')}</div>
        <div class="row-note">${esc(t.universe ?? '')}${t.author ? ` · by ${esc(t.author)}` : ''}</div>
      </div>
      ${
        installed.has(t.id)
          ? `<button class="btn" data-edit="${esc(t.id)}">${ICON.check} Installed</button>`
          : `<button class="btn is-primary" data-install="${esc(t.id)}" ${state.installing ? 'disabled' : ''}>${state.installing === t.id ? 'Installing…' : `${ICON.download} Install`}</button>`
      }
    </article>`
  return `
    ${state.gallery.source === 'local' ? '<p class="row-note" style="margin:0 4px 14px">Offline gallery: only the themes bundled with Ambiance are listed. It fills up once the GitHub repository is online.</p>' : ''}
    ${weekly ? `<div class="section-title">Theme of the week</div><div class="weekly">${card(weekly)}</div>` : ''}
    <div class="section-title">All themes</div>
    <div class="discover-grid">${list.map(card).join('')}</div>
    <div class="group" style="margin-top:24px">
      <div class="row">
        <div class="row-main"><div class="row-title">Submit your theme</div><div class="row-sub">Create it here, then share it: it lands on GitHub, ready to join the gallery.</div></div>
        <button class="btn" data-go="create">${ICON.sparkles} Create a theme</button>
      </div>
    </div>`
}

const IDEAS = [
  'Cyberpunk in the rain, pink and cyan neon',
  'Elven forest under the moonlight',
  'Abandoned space station, red alarms',
  'Pirate ship in a storm, treasure and lanterns',
  'Wizard library, candles and grimoires',
  'Eighties arcade, chiptune and neon',
]

function renderCreate(): string {
  const draft = state.draft
  return `
    <div class="create">
      <div>
        <div class="section-title">Your idea</div>
        <div class="group"><div class="row">
          <textarea class="textarea" id="prompt" rows="3" placeholder="e.g. an ice dragon in the mountains under the northern lights" ${state.generating ? 'disabled' : ''}>${esc(state.prompt)}</textarea>
        </div></div>
        <div class="chips">${IDEAS.map(idea => `<button class="chip" data-idea="${esc(idea)}">${esc(idea)}</button>`).join('')}</div>
        <div class="launch-cta" style="margin-top:16px">
          <button class="btn is-primary is-large" id="generate" ${state.generating ? 'disabled' : ''}>${state.generating ? '<span class="spinner is-small"></span> Claude is designing your theme…' : `${ICON.sparkles} Generate the theme`}</button>
        </div>
        <p class="row-note" style="margin:12px 4px">Generation runs through your own Claude Code (your subscription, no API key needed) and takes about a minute. Colors are checked and fixed to stay readable.</p>
      </div>
      <div class="launch-side">
        <div class="section-title" style="margin-bottom:0">Preview</div>
        ${draft ? preview(draft, 0, { wall: false }) : '<div class="group"><div class="row row-note">Your theme will appear here.</div></div>'}
        ${
          draft
            ? `<div class="theme-desc">${esc(draft.emoji ?? '')} <b>${esc(draft.name)}</b> · ${esc(draft.tagline ?? '')}<br>${esc(draft.persona?.join(' ') ?? '')}</div>
               <div class="launch-cta">
                 <button class="btn is-primary" id="save-draft">${ICON.check} Keep this theme</button>
                 <button class="btn" id="generate-again">Try another one</button>
               </div>`
            : ''
        }
      </div>
    </div>`
}

function renderProjects(): string {
  const projects = Object.entries(state.config.projects ?? {})
  const rows = projects
    .map(
      ([dir, id]) => `
      <div class="row">
        <div class="row-main"><div class="row-title">${esc(folderName(dir))}</div><div class="row-sub mono">${esc(dir)}</div></div>
        ${picker(`project:${dir}`, id, 'Remove')}
      </div>`,
    )
    .join('')
  return `
    <div class="section-title">Linked projects</div>
    <div class="group">
      ${rows || '<div class="row row-note">No projects yet.</div>'}
      <div class="row"><span class="spacer"></span><button class="btn" id="add-project">${ICON.folder} Add a project…</button></div>
    </div>
    <p class="row-note" style="margin:12px 4px">A session opened in this folder (or a subfolder) gets this theme. To share it with your team, add a <code>.ambiance.json</code> file at the repository root instead: <code>{ "theme": "dracula" }</code>. Tip: a red theme for production, and you'll never wonder which terminal you're typing in again.</p>`
}

function renderLaunch(): string {
  const selected = themeById(state.launchTheme)
  const tiles = [
    ...state.themes.map(
      t => `
      <button class="tile ${t.id === state.launchTheme ? 'is-selected' : ''}" data-tile="${esc(t.id)}">
        <span class="tile-art" style="background:linear-gradient(140deg, ${esc(t.terminal?.background ?? '#222')} 50%, ${esc(t.colors?.accent ?? '#888')})">${t.pixelArt ? pixelSvg(t.pixelArt, 0, 'pixel is-tile') : esc(t.emoji ?? '')}</span>
        <span class="tile-name">${esc(t.name)}</span>
      </button>`,
    ),
    `<button class="tile ${state.launchTheme === null ? 'is-selected' : ''}" data-tile="">
        <span class="tile-art" style="background:var(--fill)">–</span>
        <span class="tile-name">No theme</span>
      </button>`,
  ].join('')

  return `
    <div class="launch">
      <div>
        <div class="section-title">Project folder</div>
        <div class="group">
          <div class="row">
            <div class="field" style="flex:1">
              <input class="input mono" id="launch-dir" placeholder="C:\\Users\\…\\my-project" value="${esc(state.launchDir)}" spellcheck="false" />
              <button class="btn" id="pick-dir">${ICON.folder} Choose…</button>
            </div>
          </div>
        </div>
        <div class="section-title">Theme</div>
        <div class="group"><div class="tiles">${tiles}</div></div>
      </div>
      <div class="launch-side">
        <div class="section-title" style="margin-bottom:0">Preview</div>
        ${selected ? preview(selected) : '<div class="group"><div class="row row-note">Claude Code will open with its usual look.</div></div>'}
        <div class="launch-cta">
          <button class="btn is-primary is-large" id="launch" ${state.launchDir.trim() === '' ? 'disabled' : ''}>${ICON.terminal} Open in the terminal</button>
        </div>
      </div>
    </div>`
}

function renderSettings(): string {
  return `
    <div class="section-title">General</div>
    <div class="group">
      <div class="row">
        <div class="row-main"><div class="row-title">Default theme</div><div class="row-sub">For sessions opened without a chosen theme.</div></div>
        ${picker('default', state.config.defaultTheme ?? null)}
      </div>
    </div>

    <div class="section-title">In Claude Code</div>
    <div class="group">
      <div class="row">
        <div class="row-main"><div class="row-title">Style</div><div class="row-sub">${esc(STYLE_HINTS[state.config.style ?? 'full'])}</div></div>
        <div class="segmented is-compact">
          ${(['full', 'compact', 'minimal'] as const).map(style => `<button class="${(state.config.style ?? 'full') === style ? 'is-selected' : ''}" data-style="${style}">${style[0]!.toUpperCase()}${style.slice(1)}</button>`).join('')}
        </div>
      </div>
      <div class="row">
        <div class="row-main"><div class="row-title">Persona</div><div class="row-sub">Claude answers in the theme's tone. Never in code, commits or files.</div></div>
        <label class="switch"><input type="checkbox" id="persona" ${state.config.persona === true ? 'checked' : ''} /><span></span></label>
      </div>
      <div class="row">
        <div class="row-main"><div class="row-title">Mood sounds</div><div class="row-sub">A short sound when a check passes or fails. Ambiance stays in the system tray to play them.</div></div>
        <label class="switch"><input type="checkbox" id="sounds" ${soundsOn() ? 'checked' : ''} /><span></span></label>
      </div>
    </div>
    <p class="row-note" style="margin:10px 4px">Open sessions pick these up within two seconds. In a session, <code>/ambiance style</code>, <code>/ambiance persona</code> and <code>/ambiance sounds</code> do the same.</p>

    <div class="section-title">Plugin Claude Code</div>
    <div class="group">
      <div class="row">
        <span class="dot ${state.isPluginInstalled ? 'is-on' : 'is-warn'}"></span>
        <div class="row-main">
          <div class="row-title">${state.isPluginInstalled ? 'Ambiance plugin installed' : 'Ambiance plugin not detected'}</div>
          <div class="row-sub">Without it, Claude Code can't read the themes. Install it once, from a terminal:</div>
        </div>
      </div>
      <div class="row">
        <code class="cmd">${esc(INSTALL_COMMAND)}</code>
        <button class="btn" data-copy="${esc(INSTALL_COMMAND)}">${ICON.copy} Copy</button>
      </div>
    </div>

    <div class="section-title">Terminal</div>
    <div class="group">
      <div class="row">
        <div class="row-main">
          <div class="row-title">${state.platform === 'windows' ? 'Windows Terminal profiles' : state.platform === 'macos' ? 'iTerm2 profiles and Ghostty themes' : 'Ghostty and kitty themes'}</div>
          <div class="row-sub">One “Claude · theme” profile per theme: colors, wallpaper, animated effect.</div>
        </div>
        <button class="btn" id="sync-terminal">Update</button>
      </div>
    </div>

    <div class="section-title">Data</div>
    <div class="group">
      <div class="row">
        <div class="row-main"><div class="row-title">Ambiance folder</div><div class="row-sub mono">${esc(state.dataDir)}</div></div>
        <button class="btn" id="open-data">${ICON.folder} Open</button>
      </div>
    </div>

    <p class="row-note" style="margin:22px 4px">Ambiance ${esc(state.version)} · <a href="#" data-url="${esc(REPO_URL)}">${esc(REPO_URL.replace('https://', ''))}</a> · Unofficial community project. Palette tributes are credited to their authors in docs/CREDITS.md.</p>`
}

function render() {
  const [title, subtitle] = TITLES[state.view]
  document.getElementById('view-title')!.textContent = title
  document.getElementById('view-subtitle')!.textContent = subtitle
  document.querySelectorAll<HTMLElement>('.nav-item').forEach(el => el.classList.toggle('is-active', el.dataset.view === state.view))

  const count = document.getElementById('session-count')!
  count.hidden = state.sessions.length === 0
  count.textContent = String(state.sessions.length)

  document.getElementById('plugin-pill')!.innerHTML = `
    <div class="pill"><span class="dot ${state.isPluginInstalled ? 'is-on' : 'is-warn'}"></span>
    ${state.isPluginInstalled ? 'Plugin active' : 'Plugin not installed'}</div>`

  const view = document.getElementById('view')!
  const scroll = view.scrollTop
  const renderers: Record<View, () => string> = {
    sessions: renderSessions,
    themes: renderThemes,
    discover: renderDiscover,
    create: renderCreate,
    projects: renderProjects,
    launch: renderLaunch,
    settings: renderSettings,
  }
  view.innerHTML = renderers[state.view]()
  view.scrollTop = scroll

  const sheet = document.getElementById('sheet-root')!
  const editing = themeById(state.editing)
  stopEffect()
  sheet.innerHTML = editing ? renderEditor(editing) : ''
  if (editing) {
    const canvas = document.getElementById('effect-canvas') as HTMLCanvasElement | null
    if (canvas) stopEffect = startEffect(canvas, shaderOf(editing))
  }
  hydrateImages()
}

function go(view: View) {
  state.view = view
  state.openMenu = null
  const el = document.getElementById('view')!
  el.style.animation = 'none'
  void el.offsetWidth
  el.style.animation = ''
  el.scrollTop = 0
  render()
  if (view === 'discover' && state.gallery === null) void loadGallery()
}

// ---------- Data ----------

async function refreshSessions(force = false) {
  const sessions = (await invoke<Session[]>('list_sessions').catch(() => undefined)) ?? []
  const key = JSON.stringify(sessions.map(s => [s.id, s.theme, s.isWorking, s.mood, s.cwd, s.stats?.turns]))
  if (!force && key === state.sessionsKey) return
  state.sessions = sessions
  state.sessionsKey = key
  // An open menu or sheet is not redrawn under the cursor.
  if (state.openMenu === null && state.editing === null && !isTyping()) render()
}

const isTyping = () => document.activeElement instanceof HTMLTextAreaElement || document.activeElement instanceof HTMLInputElement

async function refreshThemes() {
  state.themes = (await call<Theme[]>('list_themes')) ?? []
}

async function refreshAll() {
  await refreshThemes()
  state.config = (await call<typeof state.config>('get_config')) ?? {}
  const plugin = await call<{ installed: boolean; dataDir: string; platform: string }>('plugin_status')
  state.isPluginInstalled = plugin?.installed ?? false
  state.dataDir = plugin?.dataDir ?? ''
  state.platform = plugin?.platform ?? ''
  state.version = await getVersion().catch(() => '')
  document.body.classList.toggle('platform-macos', state.platform === 'macos')
  if (state.launchTheme !== null && themeById(state.launchTheme) === undefined) state.launchTheme = null
  await refreshSessions(true)
  render()
}

async function loadGallery() {
  state.gallery = (await call<typeof state.gallery>('gallery_index')) ?? { source: 'local', index: { themes: [] } }
  if (state.view === 'discover') render()
}

async function pickTheme(menuId: string, themeId: string | null) {
  state.openMenu = null
  if (menuId === 'default') {
    await call('set_default_theme', { theme: themeId })
    state.config.defaultTheme = themeId
    hud(themeId ? `${themeById(themeId)?.name} is now the default theme` : 'No default theme')
  } else if (menuId.startsWith('session:')) {
    const sessionId = menuId.slice('session:'.length)
    await call('assign_theme', { sessionId, theme: themeId })
    const session = state.sessions.find(s => s.id === sessionId)
    if (session) session.theme = themeId
    const theme = themeById(themeId)
    hud(theme ? `${theme.emoji ?? ''} ${theme.name} applied to the session` : 'Theme removed from the session')
  } else if (menuId.startsWith('project:')) {
    const dir = menuId.slice('project:'.length)
    await call('set_project', { dir, theme: themeId })
    state.config = (await call<typeof state.config>('get_config')) ?? state.config
    hud(themeId ? `${folderName(dir)} will open in ${themeById(themeId)?.name}` : `${folderName(dir)} removed`)
  }
  render()
}

async function updateOverride(themeId: string, patch: Override) {
  const theme = themeById(themeId)
  if (!theme) return
  const next = await call<Override>('set_override', { id: themeId, value: { ...theme.override, ...patch } })
  if (next) theme.override = next
  render()
}

async function launch() {
  const dir = state.launchDir.trim()
  if (dir === '') return
  try {
    await invoke('launch_session', { dir, theme: state.launchTheme })
    save('launchDir', dir)
    hud(`Session opened in ${folderName(dir)}`)
  } catch (error) {
    hud(`Couldn't open the session: ${String(error)}`)
  }
}

async function generate() {
  const description = state.prompt.trim()
  if (description === '' || state.generating) return
  state.generating = true
  render()
  try {
    state.draft = await invoke<Theme>('generate_theme', { description })
    hud(`${state.draft.emoji ?? ''} ${state.draft.name} is ready`)
  } catch (error) {
    hud(`Generation failed: ${String(error)}`)
  }
  state.generating = false
  render()
}

async function applyWallpaper(themeId: string, command: string, args: Record<string, unknown>) {
  const next = await call<Override>(command, { id: themeId, intensity: state.intensity, ...args })
  if (next) {
    const theme = themeById(themeId)
    if (theme) theme.override = next
    hud('Wallpaper applied. It will show up in your next sessions.')
  }
  render()
}

async function playSound(themeId: string, file: string) {
  const url = await asset(themeId, file)
  if (url) void new Audio(url).play().catch(() => undefined)
}

// ---------- Interactions ----------

document.addEventListener('click', async event => {
  const target = event.target as HTMLElement
  const el = target.closest<HTMLElement>('button, [data-go], [data-close-sheet], [data-url]')

  if (!target.closest('.picker') && state.openMenu !== null) {
    state.openMenu = null
    render()
  }
  if (el === null) return
  if (el.tagName === 'A') event.preventDefault()

  const data = el.dataset
  if (data.closeSheet !== undefined) {
    state.editing = null
    return render()
  }
  if (data.url) return void call('open_url', { url: data.url })
  if (data.view) return go(data.view as View)
  if (data.go) return go(data.go as View)
  if (data.menu) {
    state.openMenu = state.openMenu === data.menu ? null : data.menu
    return render()
  }
  if (data.pick !== undefined) return pickTheme(data.pick, data.theme ? data.theme : null)
  if (data.tile !== undefined) {
    state.launchTheme = data.tile === '' ? null : data.tile
    save('launchTheme', state.launchTheme)
    return render()
  }
  if (data.default) return pickTheme('default', data.default)
  if (data.edit) {
    state.editing = data.edit
    return render()
  }
  if (data.launchWith) {
    state.launchTheme = data.launchWith
    state.editing = null
    save('launchTheme', data.launchWith)
    return go('launch')
  }
  if (data.copy) {
    await navigator.clipboard.writeText(data.copy).catch(() => undefined)
    return hud('Command copied')
  }
  if (data.wall && state.editing) {
    return updateOverride(state.editing, { backgroundImage: data.wall === 'none' ? null : data.wall })
  }
  if (data.effect !== undefined && state.editing) {
    return updateOverride(state.editing, { shader: data.effect === '' ? null : data.effect })
  }
  if (data.play && state.editing) {
    const file = themeById(state.editing)?.sounds?.[data.play]
    return file ? playSound(state.editing, file) : undefined
  }
  if (data.style) {
    state.config.style = data.style as 'full' | 'compact' | 'minimal'
    await call('set_preference', { key: 'style', value: data.style })
    return render()
  }
  if (data.family) {
    state.family = data.family
    return render()
  }
  if (data.idea) {
    state.prompt = data.idea
    return render()
  }
  if (data.install) {
    state.installing = data.install
    render()
    const done = await call('gallery_install', { id: data.install })
    state.installing = null
    if (done !== undefined) {
      await refreshThemes()
      hud(`${themeById(data.install)?.name ?? data.install} installed`)
    }
    return render()
  }

  switch (el.id) {
    case 'pick-dir': {
      const dir = await open({ directory: true, multiple: false, defaultPath: state.launchDir || undefined })
      if (typeof dir === 'string') {
        state.launchDir = dir
        render()
      }
      return
    }
    case 'launch':
      return launch()
    case 'pick-wallpaper': {
      const theme = state.editing
      if (!theme) return
      const file = await open({ multiple: false, filters: [{ name: 'Images', extensions: ['png', 'jpg', 'jpeg', 'webp', 'bmp', 'gif', 'tif', 'tiff', 'ico', 'tga'] }] })
      if (typeof file !== 'string') return
      hud('Adapting the image…')
      return applyWallpaper(theme, 'set_wallpaper', { path: file })
    }
    case 'import-wallpaper': {
      const theme = state.editing
      const url = document.querySelector<HTMLInputElement>('#wallpaper-url')?.value.trim() ?? ''
      if (!theme || url === '') return hud('Paste an image link first')
      hud('Downloading the image…')
      return applyWallpaper(theme, 'set_wallpaper_url', { url })
    }
    case 'delete-theme': {
      const id = state.editing
      if (!id) return
      const name = themeById(id)?.name ?? id
      const isConfirmed = await ask(`Delete the ${name} theme? This cannot be undone.`, { title: 'Delete theme', kind: 'warning' })
      if (!isConfirmed) return
      await call('delete_theme', { id })
      state.editing = null
      await refreshThemes()
      return render()
    }
    case 'share-theme': {
      const theme = themeById(state.editing)
      if (!theme) return
      const { isBundled: _bundled, override: _override, ...shared } = theme
      await navigator.clipboard.writeText(JSON.stringify(shared, null, 2)).catch(() => undefined)
      hud('theme.json copied: paste it into the GitHub form')
      const title = encodeURIComponent(`Theme: ${theme.name}`)
      return void call('open_url', { url: `${REPO_URL}/issues/new?template=theme.yml&title=${title}` })
    }
    case 'generate':
    case 'generate-again':
      return generate()
    case 'save-draft': {
      if (!state.draft) return
      const id = await call<string>('save_theme', { theme: state.draft })
      if (id) {
        await refreshThemes()
        state.draft = null
        state.prompt = ''
        state.editing = id
        hud('Theme added to your collection')
        go('themes')
      }
      return
    }
    case 'add-project': {
      const dir = await open({ directory: true, multiple: false })
      if (typeof dir !== 'string') return
      const first = state.themes[0]
      if (first === undefined) return hud('Install a theme first')
      state.openMenu = `project:${dir}`
      state.config.projects = { ...state.config.projects, [dir]: first.id }
      await call('set_project', { dir, theme: first.id })
      return render()
    }
    case 'sync-terminal': {
      const result = await call<string>('sync_terminal')
      const messages: Record<string, string> = {
        written: 'Terminal profiles updated',
        unchanged: 'Terminal profiles are already up to date',
        unsupported: 'Not available on this system yet',
      }
      return result && hud(messages[result] ?? result)
    }
    case 'open-data':
      return void call('open_data_dir')
  }
})

document.addEventListener('change', async event => {
  const target = event.target as HTMLInputElement
  if (target.id === 'sounds' || target.id === 'persona') {
    state.config[target.id] = target.checked
    await call('set_preference', { key: target.id, value: target.checked })
  } else if (target.id === 'theme-sounds' && state.editing) {
    await updateOverride(state.editing, { sounds: target.checked })
  } else if (target.id === 'opacity' && state.editing) {
    await updateOverride(state.editing, { backgroundImageOpacity: Number(target.value) })
  } else if (target.id === 'intensity') {
    state.intensity = Number(target.value)
  }
})

document.addEventListener('input', event => {
  const target = event.target as HTMLInputElement | HTMLTextAreaElement
  if (target.id === 'launch-dir') {
    state.launchDir = target.value
    document.getElementById('launch')?.toggleAttribute('disabled', target.value.trim() === '')
  } else if (target.id === 'prompt') {
    state.prompt = target.value
  } else if (target.id === 'opacity') {
    document.querySelectorAll<HTMLElement>('.sheet .term-wall').forEach(el => (el.style.opacity = target.value))
  }
})

document.addEventListener('keydown', event => {
  if (event.key === 'Escape') {
    if (state.openMenu !== null) state.openMenu = null
    else if (state.editing !== null) state.editing = null
    render()
  }
  const id = (event.target as HTMLElement).id
  if (event.key === 'Enter' && id === 'launch-dir') void launch()
  if (event.key === 'Enter' && id === 'wallpaper-url') document.getElementById('import-wallpaper')?.click()
  if (event.key === 'Enter' && id === 'prompt' && !event.shiftKey) {
    event.preventDefault()
    void generate()
  }
})

// The spinner verbs cycle in the previews, without a full redraw.
setInterval(() => {
  state.tick += 1
  document.querySelectorAll<HTMLElement>('[data-verb]').forEach((el, i) => {
    const verbs = (themeById(el.dataset.verb) ?? (state.draft?.id === el.dataset.verb ? state.draft : undefined))?.spinnerVerbs
    if (verbs?.length) el.textContent = verbs[(state.tick + i) % verbs.length]!
  })
}, 2200)

// The pixel art animates, like in Claude Code's banner.
setInterval(() => {
  state.pixelTick += 1
  document.querySelectorAll<HTMLElement>('[data-pixel]').forEach(el => {
    const theme = themeById(el.dataset.pixel) ?? (state.draft?.id === el.dataset.pixel ? state.draft : undefined)
    if (theme?.pixelArt) el.innerHTML = pixelSvg(theme.pixelArt, state.pixelTick)
  })
}, 333)

setInterval(() => void refreshSessions(), POLL_MS)
window.addEventListener('focus', () => void refreshAll())

// The bundled themes are copied in the background at startup: refresh once done.
void listen('themes-installed', () => void refreshAll())
void refreshAll()

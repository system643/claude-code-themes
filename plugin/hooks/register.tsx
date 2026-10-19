// Ambiance's engine: every Claude Code session gets a theme (animated pixel-art
// banner, status line, spinner, end-of-turn line, moods, persona) and can switch
// to another one live when the app assigns it.
//
// Files shared with the app, under ~/.ambiance/:
//   themes/<id>/theme.json   installed themes (take precedence over the plugin's)
//   sessions/<id>.json       written here: the session, its theme, a heartbeat
//   events/<id>.json         written here: the latest mood, for the app's sounds
//   assign/<id>.json         written by the app: { theme, at }
//   config.json              preferences shared by the app and /ambiance:
//                            { defaultTheme, projects, style, persona, sounds, banner }
// And in a project: .ambiance.json ({ "theme": "<id>" }), here or in a parent.
import type { EngineInterface, Register } from 'claude-code'

type Frame = readonly string[]

type Mood = 'idle' | 'error' | 'success'

// full: pixel-art banner; compact: a one-line banner; minimal: no banner and no
// themed spinner, only the status line, the session label and the terminal colors.
type Style = 'full' | 'compact' | 'minimal'

const STYLES: readonly Style[] = ['full', 'compact', 'minimal']

type MoodSpec = { status?: string; quotes: readonly string[]; frames: readonly Frame[] }

type PixelArt = { palette: Record<string, number>; fps: number; frames: readonly Frame[]; width: number; height: number }

type Theme = {
  id: string
  name: string
  tagline: string
  emoji: string
  colors: { accent: string; secondary: string; muted: string }
  banner: readonly string[]
  pixelArt?: PixelArt
  moods: Partial<Record<Mood, MoodSpec>>
  quotes: readonly string[]
  spinnerVerbs: readonly string[]
  durationLines: readonly string[]
  status: { idle: string; working: string }
  welcome: string
  persona: readonly string[]
  sounds: Partial<Record<string, string>>
  dir: string
}

const POLL_MS = 2000
const HEARTBEAT_MS = 5000
const NARROW = 60
const PANE = 'ambiance-companion'
const DEFAULT_COLOR = 0x01000000
const UPPER_HALF = 0x2580
const LOWER_HALF = 0x2584
// The commands whose result changes the theme's mood: a test, build or lint run
// at the start of a command (`cd app && npm test` counts, `cat tests/a.py` or
// `git commit -m "fix tests"` do not).
const CHECKS =
  /(?:^|&&|\|\||[;|(])\s*(?:\w+=\S*\s+)*(?:npx\s+|bunx\s+|uv run\s+|python3? -m\s+)?(?:pytest|jest|vitest|mocha|tsc|eslint|cargo (?:test|build|check|clippy)|go (?:test|build|vet)|(?:npm|pnpm|yarn|bun) (?:run )?(?:test|build|lint)|make)\b/

// Rules appended to every persona: a community theme cannot remove them.
const PERSONA_RULES = [
  'Rules that take precedence over this tone:',
  '- Substance before style: accuracy, concision and clarity come first.',
  '- Never put theme references in code, names, comments, commit messages, written files or commands.',
  '- No theme references when the topic is serious: major errors, data loss, security, personal or sensitive matters.',
  "- Reply in the user's language.",
  '- This tone only applies to your replies to the human, not to reports between agents.',
]

// The session's state. A module reload resets it, then session.start reads
// it back (store, assignment files).
const session = {
  catalogue: [] as Theme[],
  theme: undefined as Theme | undefined,
  dataDir: '',
  id: '',
  cwd: '',
  startedAt: 0,
  endedAt: undefined as number | undefined,
  assignedAt: 0,
  quote: 0,
  frame: 0,
  mood: 'idle' as Mood,
  isWorking: false,
  isPersonaOn: true,
  isBannerHidden: false,
  isMuted: true,
  style: 'full' as Style,
  bandRequestId: '',
  isPaneOpen: false,
  animation: undefined as { cancel: () => void } | undefined,
  timers: [] as { cancel: () => void }[],
  stats: { turns: 0, tools: 0, errors: 0 },
}

const strings = (value: unknown): string[] =>
  Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : []

const text = (value: unknown, fallback: string): string =>
  typeof value === 'string' && value !== '' ? value : fallback

function hexColor(value: unknown): number | undefined {
  if (typeof value !== 'string' || !/^#[0-9a-fA-F]{6}$/.test(value)) return undefined
  return parseInt(value.slice(1), 16)
}

function frames(value: unknown, width: number, height: number): Frame[] {
  if (!Array.isArray(value)) return []
  return value
    .map(frame => strings(frame))
    .filter(frame => frame.length === height && frame.every(row => row.length === width))
}

function parsePixelArt(raw: any): PixelArt | undefined {
  const first = strings(raw?.frames?.[0])
  const height = first.length
  const width = first[0]?.length ?? 0
  if (width === 0 || width > 48 || height === 0 || height > 32 || typeof raw?.palette !== 'object') return undefined
  const palette: Record<string, number> = {}
  for (const [key, color] of Object.entries(raw.palette as Record<string, unknown>)) {
    const parsed = hexColor(color)
    if (key.length === 1 && parsed !== undefined) palette[key] = parsed
  }
  const list = frames(raw.frames, width, height)
  if (list.length === 0) return undefined
  const fps = typeof raw.fps === 'number' ? Math.min(Math.max(raw.fps, 1), 12) : 3
  return { palette, fps, frames: list, width, height }
}

function parseTheme(raw: unknown, dir: string): Theme | undefined {
  if (typeof raw !== 'object' || raw === null) return undefined
  const t = raw as Record<string, any>
  if (typeof t.id !== 'string' || !/^[a-z0-9-]+$/.test(t.id)) return undefined

  const name = text(t.name, t.id)
  const quotes = strings(t.quotes)
  const pixelArt = parsePixelArt(t.pixelArt)
  const moods: Theme['moods'] = {}
  for (const mood of ['idle', 'error', 'success'] as const) {
    const spec = t.moods?.[mood]
    if (typeof spec !== 'object' || spec === null) continue
    moods[mood] = {
      status: typeof spec.status === 'string' ? spec.status : undefined,
      quotes: strings(spec.quotes),
      frames: pixelArt === undefined ? [] : frames(spec.frames, pixelArt.width, pixelArt.height),
    }
  }

  return {
    id: t.id,
    name,
    tagline: text(t.tagline, ''),
    emoji: text(t.emoji, '✦'),
    colors: {
      accent: text(t.colors?.accent, '#D97757'),
      secondary: text(t.colors?.secondary, '#E8A87C'),
      muted: text(t.colors?.muted, '#999999'),
    },
    banner: strings(t.banner).slice(0, 4),
    pixelArt,
    moods,
    quotes: quotes.length > 0 ? quotes : [name],
    spinnerVerbs: strings(t.spinnerVerbs),
    durationLines: strings(t.durationLines).filter(line => line.includes('{d}')),
    status: { idle: text(t.status?.idle, 'ready'), working: text(t.status?.working, 'working') },
    welcome: text(t.welcome, `${name} theme applied.`),
    persona: strings(t.persona),
    sounds: Object.fromEntries(
      Object.entries(typeof t.sounds === 'object' && t.sounds !== null ? t.sounds : {}).filter(
        (entry): entry is [string, string] => typeof entry[1] === 'string' && !entry[1].includes('..'),
      ),
    ),
    dir,
  }
}

function pick<T>(list: readonly T[], seed: string): T {
  let hash = 0
  for (const char of seed) hash = (hash * 31 + char.charCodeAt(0)) | 0
  return list[Math.abs(hash) % list.length] as T
}

function formatDuration(ms: number): string {
  const seconds = Math.max(1, Math.round(ms / 1000))
  const minutes = Math.floor(seconds / 60)
  return minutes === 0 ? `${seconds}s` : `${minutes}m ${seconds % 60}s`
}

function base64(bytes: Uint8Array): string {
  let binary = ''
  for (let i = 0; i < bytes.length; i += 0x8000) binary += String.fromCharCode(...bytes.subarray(i, i + 0x8000))
  return btoa(binary)
}

// Pixel art as terminal cells: two pixels per cell, one as the text color
// (▀ or ▄), the other as the background. `scale` 2 doubles the width for the
// companion, for squarer proportions.
function rasterCells(art: PixelArt, frame: Frame, scale = 1): { cells: string; columns: number; rows: number } {
  const columns = art.width * scale
  const rows = Math.ceil(art.height / 2)
  const words = new Uint32Array(columns * rows * 3)
  const color = (y: number, x: number) => art.palette[frame[y]?.[x] ?? '.']
  for (let row = 0; row < rows; row++) {
    for (let column = 0; column < columns; column++) {
      const x = Math.floor(column / scale)
      const top = color(row * 2, x)
      const bottom = color(row * 2 + 1, x)
      const at = (row * columns + column) * 3
      if (top !== undefined) {
        words[at] = UPPER_HALF
        words[at + 1] = top
        words[at + 2] = bottom ?? DEFAULT_COLOR
      } else if (bottom !== undefined) {
        words[at] = LOWER_HALF
        words[at + 1] = bottom
        words[at + 2] = DEFAULT_COLOR
      } else {
        words[at] = 0x20
        words[at + 1] = DEFAULT_COLOR
        words[at + 2] = DEFAULT_COLOR
      }
    }
  }
  return { cells: base64(new Uint8Array(words.buffer)), columns, rows }
}

// Characters a Raster cell cannot hold: two columns wide, surrogates, the
// emoji variation selector.
const WIDE: readonly (readonly [number, number])[] = [
  [0x1100, 0x115f], // Hangul Jamo
  [0x2e80, 0xa4cf], // CJK radicals to Yi
  [0xac00, 0xd7a3], // Hangul syllables
  [0xd800, 0xdfff], // surrogates
  [0xf900, 0xfaff], // CJK compatibility ideographs
  [0xfe30, 0xfe4f], // CJK compatibility forms
  [0xff00, 0xff60], // fullwidth forms
]

const fitsOneCell = (code: number) =>
  code >= 0x20 && code <= 0xffff && code !== 0xfe0f && !WIDE.some(([from, to]) => code >= from && code <= to)

// A line of text as colored cells. The Raster guarantees the theme's exact
// color, however the terminal renders text styles.
function lineCells(text: string, color: string, width: number): { cells: string; columns: number; rows: number } {
  const fg = hexColor(color) ?? DEFAULT_COLOR
  const chars = [...text].filter(char => fitsOneCell(char.codePointAt(0) ?? 0))
  const room = Math.max(1, width)
  const shown = chars.length > room ? [...chars.slice(0, room - 1), '…'] : chars
  const columns = Math.max(1, shown.length)
  const words = new Uint32Array(columns * 3)
  shown.forEach((char, i) => {
    words[i * 3] = char.codePointAt(0) ?? 0x20
    words[i * 3 + 1] = fg
    words[i * 3 + 2] = DEFAULT_COLOR
  })
  return { cells: base64(new Uint8Array(words.buffer)), columns, rows: 1 }
}

function currentFrames(theme: Theme): readonly Frame[] {
  const moodFrames = theme.moods[session.mood]?.frames ?? []
  return moodFrames.length > 0 ? moodFrames : (theme.pixelArt?.frames ?? [])
}

function currentFrame(theme: Theme): Frame | undefined {
  const list = currentFrames(theme)
  return list[session.frame % Math.max(1, list.length)]
}

function currentQuote(theme: Theme): string {
  const moodQuotes = session.mood === 'idle' ? [] : (theme.moods[session.mood]?.quotes ?? [])
  const list = moodQuotes.length > 0 ? moodQuotes : theme.quotes
  return list[session.quote % list.length] ?? theme.name
}

function currentState(theme: Theme): string {
  const moodStatus = session.mood === 'idle' ? undefined : theme.moods[session.mood]?.status
  return moodStatus ?? (session.isWorking ? theme.status.working : theme.status.idle)
}

async function readJson($: EngineInterface, path: string): Promise<Record<string, unknown> | undefined> {
  try {
    const parsed: unknown = JSON.parse(await $.fs.read(path))
    return typeof parsed === 'object' && parsed !== null ? (parsed as Record<string, unknown>) : undefined
  } catch {
    return undefined
  }
}

async function loadCatalogue($: EngineInterface): Promise<Theme[]> {
  const byId = new Map<string, Theme>()
  for (const dir of [`${session.dataDir}/themes`, `${$.plugin.root}/themes`]) {
    const entries = await $.fs.list(dir).catch(() => [])
    for (const entry of entries) {
      if (entry.kind !== 'dir' || byId.has(entry.name)) continue
      const parsed = parseTheme(await readJson($, `${dir}/${entry.name}/theme.json`), `${dir}/${entry.name}`)
      if (parsed !== undefined) byId.set(parsed.id, parsed)
    }
  }
  return [...byId.values()].sort((a, b) => a.name.localeCompare(b.name))
}

// The project's theme: a .ambiance.json in the folder or a parent, otherwise
// the folder → theme mapping the app keeps in config.json.
async function projectTheme($: EngineInterface, config: Record<string, unknown> | undefined): Promise<unknown> {
  const parts = session.cwd.replace(/\\/g, '/').split('/')
  for (let depth = parts.length; depth > 0; depth--) {
    const file = await readJson($, `${parts.slice(0, depth).join('/')}/.ambiance.json`)
    if (typeof file?.theme === 'string') return file.theme
  }
  const projects = config?.projects
  if (typeof projects !== 'object' || projects === null) return undefined
  const cwd = session.cwd.replace(/\\/g, '/').toLowerCase()
  const match = Object.entries(projects as Record<string, unknown>)
    .map(([dir, id]) => [dir.replace(/\\/g, '/').replace(/\/$/, '').toLowerCase(), id] as const)
    .filter(([dir]) => cwd === dir || cwd.startsWith(`${dir}/`))
    .sort((a, b) => b[0].length - a[0].length)[0]
  return match?.[1]
}

function showStatus($: EngineInterface) {
  const { theme } = session
  $.ui.status(theme === undefined ? undefined : `${theme.emoji} ${theme.name} · ${currentState(theme)}`)
}

async function writeSession($: EngineInterface) {
  if (session.id === '' || session.dataDir === '') return
  const { endedAt } = session
  const record = {
    id: session.id,
    cwd: session.cwd,
    theme: session.theme?.id ?? null,
    mood: session.mood,
    persona: session.isPersonaOn,
    isWorking: session.isWorking,
    startedAt: session.startedAt,
    heartbeat: await $.clock.now(),
    stats: session.stats,
    ...(endedAt === undefined ? {} : { endedAt }),
  }
  await $.fs.write(`${session.dataDir}/sessions/${session.id}.json`, JSON.stringify(record, null, 2)).catch(() => {})
}

async function emit($: EngineInterface, type: string) {
  if (session.id === '' || session.theme === undefined) return
  const event = { type, theme: session.theme.id, at: await $.clock.now() }
  await $.fs.write(`${session.dataDir}/events/${session.id}.json`, JSON.stringify(event)).catch(() => {})
  void playSound($, type)
}

// The mood's sound. Claude Code only plays sounds on macOS: elsewhere, the
// Ambiance app plays it by reading the event file.
async function playSound($: EngineInterface, type: string) {
  const file = session.theme?.sounds[type]
  if (file === undefined || session.isMuted) return
  try {
    const { base64 } = await $.fs.read(`${session.theme?.dir}/${file}`, { as: 'bytes' })
    await $.audio.play({ base64, mime: file.endsWith('.ogg') ? 'audio/ogg' : 'audio/wav' }, { gain: 0.7 })
  } catch {
    // A missing or unreadable sound never disturbs the session.
  }
}

function animate($: EngineInterface) {
  const theme = session.theme
  const art = theme?.pixelArt
  if (theme === undefined || art === undefined) return
  const showsBand = session.bandRequestId !== '' && !session.isBannerHidden
  if (!showsBand && !session.isPaneOpen) return
  session.frame += 1
  const frame = currentFrame(theme)
  if (frame === undefined) return
  if (showsBand) void $.ui.blit({ requestId: session.bandRequestId, key: 'logo', ...rasterCells(art, frame) }).catch(() => {})
  if (session.isPaneOpen) void $.ui.blit({ requestId: PANE, key: 'big', ...rasterCells(art, frame, 2) }).catch(() => {})
}

function startAnimation($: EngineInterface) {
  session.animation?.cancel()
  session.animation = undefined
  session.frame = 0
  const art = session.theme?.pixelArt
  if (art !== undefined && art.frames.length > 1) {
    session.animation = $.clock.every(Math.round(1000 / art.fps), () => animate($))
  }
}

async function applyTheme($: EngineInterface, id: string | null, announce: boolean): Promise<boolean> {
  if (id !== null && !session.catalogue.some(item => item.id === id)) session.catalogue = await loadCatalogue($)
  const next = id === null ? undefined : session.catalogue.find(item => item.id === id)
  if (id !== null && next === undefined) return false

  session.theme = next
  session.mood = 'idle'
  session.quote = next === undefined ? 0 : Math.floor(Math.random() * next.quotes.length)
  startAnimation($)
  showStatus($)
  $.ui.invalidate('ui.render')
  if (announce && next !== undefined) $.ui.toast(`${next.emoji} ${next.welcome}`)
  await writeSession($)
  if (announce) await emit($, 'start')
  return true
}

async function setMood($: EngineInterface, mood: Mood) {
  if (session.theme === undefined || session.mood === mood) return
  session.mood = mood
  session.frame = 0
  session.quote = Math.floor(Math.random() * 1000)
  showStatus($)
  $.ui.invalidate('ui.render')
  await emit($, mood)
  await writeSession($)
}

async function pollAssignment($: EngineInterface) {
  const assignment = await readJson($, `${session.dataDir}/assign/${session.id}.json`)
  if (assignment === undefined || typeof assignment.at !== 'number' || assignment.at === session.assignedAt) return
  session.assignedAt = assignment.at
  await applyTheme($, typeof assignment.theme === 'string' ? assignment.theme : null, true)
}

// The banner's "hide" button only hides it in this session; `/ambiance banner`
// changes the saved preference for every session.
function hideBanner($: EngineInterface) {
  session.isBannerHidden = true
  $.ui.invalidate('ui.render')
}

function stopTimers() {
  for (const timer of session.timers) timer.cancel()
  session.timers = []
}

type Preferences = { style?: Style; persona?: boolean; sounds?: boolean; banner?: boolean }

// Applies the preferences found in config.json over the plugin options.
function applyPreferences(config: Record<string, unknown> | undefined, options: Record<string, unknown>) {
  const style = config?.style ?? options.style
  session.style = STYLES.find(item => item === style) ?? 'full'
  session.isPersonaOn = typeof config?.persona === 'boolean' ? config.persona : options.persona === true
  // Sounds follow the style unless the user chose: on in the full style.
  session.isMuted = !(typeof config?.sounds === 'boolean' ? config.sounds : options.sounds === true || session.style === 'full')
  session.isBannerHidden = typeof config?.banner === 'boolean' ? !config.banner : options.banner === false
}

async function savePreferences($: EngineInterface, changes: Preferences) {
  const path = `${session.dataDir}/config.json`
  const config = (await readJson($, path)) ?? {}
  await $.fs.write(path, JSON.stringify({ ...config, ...changes }, null, 2)).catch(() => {})
}

// The preferences the session last applied, to redraw only when they change.
let lastPreferences = ''

async function pollPreferences($: EngineInterface, options: Record<string, unknown>) {
  const config = await readJson($, `${session.dataDir}/config.json`)
  const key = JSON.stringify([config?.style, config?.persona, config?.sounds, config?.banner])
  if (key === lastPreferences) return
  lastPreferences = key
  applyPreferences(config, options)
  $.ui.invalidate('ui.render')
}

export const register: Register = (on, options) => {
  // The persona is opt-in; the sounds come with the full style.
  applyPreferences(undefined, options)

  on('session.start', async ($, e, next) => {
    const home = (await $.env.get('USERPROFILE')) ?? (await $.env.get('HOME')) ?? ''
    session.dataDir = `${home.replace(/\\/g, '/')}/.ambiance`
    session.id = await $.session.id()
    session.cwd = e.cwd
    session.startedAt = await $.clock.now()
    session.endedAt = undefined

    session.catalogue = await loadCatalogue($)

    // The starting theme: the one the app assigned (resumed or reloaded
    // session), else CLAUDE_THEME, else the project's, else the default.
    const assignment = await readJson($, `${session.dataDir}/assign/${session.id}.json`)
    const config = await readJson($, `${session.dataDir}/config.json`)
    applyPreferences(config, options)
    lastPreferences = JSON.stringify([config?.style, config?.persona, config?.sounds, config?.banner])
    if (typeof assignment?.at === 'number') session.assignedAt = assignment.at
    const candidates = [
      assignment?.theme,
      await $.env.get('CLAUDE_THEME'),
      await projectTheme($, config),
      options.defaultTheme,
      config?.defaultTheme,
    ]
    const first = candidates.find(
      (id): id is string => typeof id === 'string' && session.catalogue.some(item => item.id === id),
    )
    await applyTheme($, first ?? null, e.isInteractive)

    await $.command.register({
      name: 'ambiance',
      description: "This session's theme: switch, companion, sounds, persona, banner",
      argumentHint: '[theme | off | style full|compact|minimal | companion | sounds on|off | persona on|off | banner]',
    })

    // A resumed or cleared session starts again: its old timers go first.
    stopTimers()
    session.timers = [
      $.clock.every(POLL_MS, () => {
        void pollAssignment($)
        void pollPreferences($, options)
      }),
      $.clock.every(HEARTBEAT_MS, () => void writeSession($)),
    ]

    return next(e)
  })

  on('session.end', async ($, e, next) => {
    session.animation?.cancel()
    stopTimers()
    session.endedAt = await $.clock.now()
    await writeSession($)
    return next(e)
  })

  on('command.run', { command: 'ambiance' }, async ($, e) => {
    const [word = '', value = ''] = e.args.trim().toLowerCase().split(/\s+/)

    // Without on or off, persona and sounds toggle.
    if (word === 'persona') {
      session.isPersonaOn = value === 'on' || (value !== 'off' && !session.isPersonaOn)
      await savePreferences($, { persona: session.isPersonaOn })
      await writeSession($)
      return { text: `Persona ${session.isPersonaOn ? 'on' : 'off'} (from the next message).` }
    }

    if (word === 'banner') {
      session.isBannerHidden = !session.isBannerHidden
      await savePreferences($, { banner: !session.isBannerHidden })
      $.ui.invalidate('ui.render')
      return { text: session.isBannerHidden ? 'Banner hidden.' : 'Banner shown.' }
    }

    if (word === 'style') {
      const style = STYLES.find(item => item === value)
      if (style === undefined) return { text: `Style: ${session.style}. Choose one of: ${STYLES.join(', ')}.` }
      session.style = style
      await savePreferences($, { style })
      $.ui.invalidate('ui.render')
      const what = { full: 'pixel-art banner', compact: 'one-line banner', minimal: 'status line and session label only' }[style]
      return { text: `Style set to ${style} (${what}).` }
    }

    if (word === 'sound' || word === 'sounds') {
      session.isMuted = value === 'off' || (value !== 'on' && !session.isMuted)
      await savePreferences($, { sounds: !session.isMuted })
      return { text: session.isMuted ? 'Sounds muted.' : 'Sounds on (macOS; elsewhere, through the Ambiance app).' }
    }

    if (word === 'companion') {
      const { theme } = session
      if (theme === undefined) return { text: 'Pick a theme first: /ambiance <theme>.' }
      const opened = await $.ui.open({ id: PANE, title: `${theme.emoji} ${theme.name}` })
      session.isPaneOpen = opened.isPlaced
      return {
        text: opened.isPlaced
          ? `${theme.name} keeps you company in the side panel.`
          : 'The companion needs a wider terminal or fullscreen mode.',
      }
    }

    if (word === 'off' || word === 'none') {
      await applyTheme($, null, false)
      return { text: 'Theme removed from this session.' }
    }

    if (word !== '') {
      const isApplied = await applyTheme($, word, true)
      const { theme } = session
      return isApplied && theme !== undefined
        ? { text: `${theme.emoji} ${theme.name} applied to this session.` }
        : { text: `Theme "${word}" not found. Type /ambiance to see the list.` }
    }

    session.catalogue = await loadCatalogue($)
    const { theme } = session
    const rows = session.catalogue.map(
      item => `  ${item.id === theme?.id ? '●' : '○'} ${item.emoji} ${item.id.padEnd(14)} ${item.tagline}`,
    )
    return {
      text: [
        theme === undefined ? 'No theme on this session.' : `Current theme: ${theme.emoji} ${theme.name}`,
        '',
        ...rows,
        '',
        '  /ambiance <theme>         switch this session to a theme',
        '  /ambiance off             remove the theme',
        `  /ambiance style <style>   full, compact or minimal (now: ${session.style})`,
        '  /ambiance companion       open the animated companion in a side panel',
        `  /ambiance sounds on|off   mood sounds (${session.isMuted ? 'muted' : 'on'})`,
        `  /ambiance persona on|off  persona (${session.isPersonaOn ? 'on' : 'off'})`,
        `  /ambiance banner          ${session.isBannerHidden ? 'show' : 'hide'} the banner`,
      ].join('\n'),
    }
  })

  on('turn.start', ($, e, next) => {
    if (e.agentId === undefined) {
      session.isWorking = true
      session.stats.turns += 1
      session.mood = 'idle'
      showStatus($)
    }
    return next(e)
  })

  on('turn.complete', ($, e, next) => {
    if (e.agentId === undefined) {
      session.isWorking = false
      session.quote += 1
      showStatus($)
      $.ui.invalidate('ui.render')
    }
    return next(e)
  })

  // Moods: a failing check (tests, build) makes the theme angry, a passing
  // one makes it proud.
  on('tool.call', async ($, e, next) => {
    const ran = await next(e)
    session.stats.tools += 1
    if (e.tool === 'Bash' && CHECKS.test(e.command) && ran.deny === undefined) {
      if (ran.isError === true) {
        session.stats.errors += 1
        await setMood($, 'error')
      } else {
        await setMood($, 'success')
      }
    }
    return ran
  })

  on('prompt.compose', async ($, e, next) => {
    const composed = await next(e)
    const { theme } = session
    if (theme === undefined || !session.isPersonaOn || theme.persona.length === 0 || e.traits.includes('analysis')) {
      return composed
    }
    const persona = [`# Persona: ${theme.name} theme`, '', ...theme.persona, '', ...PERSONA_RULES].join('\n')
    return {
      sections: [...composed.sections, { id: 'ambiance:persona', text: persona, scope: 'session' as const }],
    }
  })

  // The theme's label at the right of the prompt footer: tells sessions apart
  // at a glance, in every style.
  on('ui.render', { component: 'SessionMode' }, ($, e, next) => {
    const { theme } = session
    if (theme === undefined) return next(e)
    return next({ ...e, props: { ...e.props, modes: [...e.props.modes, `${theme.emoji} ${theme.name}`] } })
  })

  on('ui.render', { component: 'Spinner' }, ($, e, next) => {
    const { theme } = session
    return theme !== undefined && session.style !== 'minimal' && theme.spinnerVerbs.length > 0 && e.surface === 'terminal'
      ? next({ ...e, props: { ...e.props, word: pick(theme.spinnerVerbs, e.props.word) } })
      : next(e)
  })

  on('ui.render', { component: 'TurnDuration' }, ($, e, next) => {
    const { theme } = session
    if (theme === undefined || session.style === 'minimal' || theme.durationLines.length === 0) return next(e)
    const { Text } = $.ui.resolve(e)
    const line = pick(theme.durationLines, e.props.word).replace('{d}', formatDuration(e.props.durationMs))
    return <Text color={theme.colors.muted}>✻ {line}</Text>
  })

  on('ui.render', { component: 'AbovePrompt' }, ($, e, next) => {
    const { theme } = session
    if (theme === undefined || session.isBannerHidden || session.style === 'minimal' || e.props.hasSurvey) return next(e)
    const quote = currentQuote(theme)

    if (e.surface === 'terminal') {
      const { Box, Text, Button, Raster } = $.ui.resolve(e)
      session.bandRequestId = e.requestId

      if (session.style === 'compact' || e.props.bodyColumns < NARROW || e.props.maxRows < 4) {
        return (
          <Box flexDirection="row" gap={1}>
            <Text color={theme.colors.secondary} bold>
              {theme.emoji} {theme.name}
            </Text>
            <Text color={theme.colors.muted} italic wrap="truncate-end">
              {quote}
            </Text>
          </Box>
        )
      }

      const art = theme.pixelArt
      const frame = currentFrame(theme)
      const logo =
        art !== undefined && frame !== undefined && e.props.maxRows >= Math.ceil(art.height / 2) ? (
          <Raster key="logo" {...rasterCells(art, frame)} />
        ) : (
          <Box flexDirection="column">
            {theme.banner.map((line, i) => (
              <Text key={`art-${i}`} color={theme.colors.accent}>
                {line}
              </Text>
            ))}
          </Box>
        )

      const room = e.props.bodyColumns - (art?.width ?? 14) - 3
      const title = `${theme.name.toUpperCase()}${theme.tagline === '' ? '' : ` · ${theme.tagline}`}`
      return (
        <Box flexDirection="row" gap={2} alignItems="center">
          {logo}
          <Box flexDirection="column">
            <Raster key="title" {...lineCells(title, theme.colors.secondary, room)} />
            <Raster key="quote" {...lineCells(`“${quote}”`, theme.colors.muted, room)} />
            <Box flexDirection="row" gap={1}>
              <Text dimColor>/ambiance to switch ·</Text>
              <Button key="hide" plain label="hide" onPress={() => hideBanner($)} />
            </Box>
          </Box>
        </Box>
      )
    }

    // Other surfaces (the desktop app) have no Raster: the ASCII drawing.
    const { Box, Text, Button } = $.ui.resolve(e)
    return (
      <Box flexDirection="row" gap={2}>
        <Box flexDirection="column">
          {theme.banner.map((line, i) => (
            <Text key={`art-${i}`} color={theme.colors.accent} mono>
              {line}
            </Text>
          ))}
        </Box>
        <Box flexDirection="column">
          <Text color={theme.colors.secondary} bold>
            {theme.name.toUpperCase()}
            {theme.tagline === '' ? '' : ` · ${theme.tagline}`}
          </Text>
          <Text color={theme.colors.muted} italic>
            “{quote}”
          </Text>
          <Button key="hide" plain label="hide" onPress={() => hideBanner($)} />
        </Box>
      </Box>
    )
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, ($, e) => {
    const { theme } = session
    const { Box, Text } = $.ui.resolve(e)
    if (theme === undefined) return <Text dimColor>No theme on this session.</Text>

    const { stats } = session
    const details = (
      <Box flexDirection="column">
        <Text color={theme.colors.secondary} bold>
          {theme.emoji} {theme.name.toUpperCase()}
        </Text>
        <Text color={theme.colors.muted}>{currentState(theme)}</Text>
        <Text color={theme.colors.muted} italic>
          “{currentQuote(theme)}”
        </Text>
        <Text dimColor>
          {stats.turns} turns · {stats.tools} tools · {stats.errors} failures
        </Text>
      </Box>
    )

    const art = theme.pixelArt
    const frame = currentFrame(theme)
    if (e.surface !== 'terminal' || art === undefined || frame === undefined || e.props.bodyColumns < art.width * 2) {
      return details
    }
    const { Raster } = $.ui.resolve(e)
    return (
      <Box flexDirection="column" gap={1}>
        <Raster key="big" {...rasterCells(art, frame, 2)} />
        {details}
      </Box>
    )
  })
}

import type { On, PromptComposeInput } from 'claude-code'
import { expect, mock, test } from 'claude-code/testing'

// POSIX-style paths: on Windows the engine resolves them on the current drive,
// and `slashes` drops the drive letter, so the same keys work on every system.
const HOME = '/home/test'
const DATA = `${HOME}/.ambiance`

const THEMES = {
  dracula: { id: 'dracula', name: 'Dracula', emoji: '🧛', quotes: ['The night is young.'], persona: ['Gothic tone.'], banner: ['/\\', '()', '\\/'] },
  nord: { id: 'nord', name: 'Nord', emoji: '❄️', quotes: ['Clear air, clear code.'], persona: ['Calm tone.'] },
  pixel: {
    id: 'pixel',
    name: 'Pixel',
    banner: ['ASCII'],
    quotes: ['Calm.'],
    pixelArt: { palette: { a: '#FF0000', b: '#00FF00' }, fps: 4, frames: [['ab', 'ba'], ['ba', 'ab']] },
    moods: {
      error: { status: 'angry', quotes: ['Missed!'], frames: [['aa', 'aa']] },
      success: { status: 'proud', quotes: ['Well done!'] },
    },
  },
}

const COMPOSE: PromptComposeInput = {
  model: 'claude-opus-5-5',
  promptModel: 'claude-opus-5-5',
  surfaces: ['terminal'],
  tools: [],
  outputStyle: null,
  traits: [],
}

const BAND = {
  hasSurvey: false,
  isWorking: false,
  maxRows: 10,
  bodyColumns: 100,
  scroll: { offset: 0, bodyRows: 10 },
  view: {},
}

const slashes = (path: string) => path.replace(/\\/g, '/').replace(/^[A-Za-z]:/, '')

// What stands beneath the plugin: an in-memory disk and the session calls.
function stage(on: On, env: Record<string, string>, files: Record<string, string> = {}) {
  const disk = new Map(Object.entries(files))
  const statuses: (string | undefined)[] = []
  const clock = mock.clock(on, { now: 1_000 })
  mock.store(on)
  mock.env(on, { USERPROFILE: HOME, ...env })

  on('session.id', () => ({ value: 'session-1' }))
  on('session.start', ($, e) => ({ cwd: e.cwd }))
  on('command.register', () => ({ value: { command: 'ambiance' } }))
  on('ui.status', ($, e) => {
    statuses.push(e.text)
    return { value: undefined }
  })
  on('ui.toast', () => ({ value: undefined }))
  on('ui.render', ($, e) => {
    const { Text } = $.ui.resolve(e)
    return <Text>engine</Text>
  })
  on('prompt.compose', () => ({ sections: [{ id: 'intro', text: 'Base.', scope: 'shared' as const }] }))
  on('fs.list', ($, e) => ({
    value:
      slashes(e.path).endsWith('/themes') && !slashes(e.path).startsWith(DATA)
        ? Object.keys(THEMES).map(name => ({ name, kind: 'dir' as const, size: 0, mtimeMs: 0, isLink: false }))
        : [],
  }))
  on('fs.read', ($, e) => {
    const id = /themes\/([a-z-]+)\/theme\.json$/.exec(slashes(e.path))?.[1]
    const theme = id === undefined ? undefined : THEMES[id as keyof typeof THEMES]
    if (theme !== undefined) return { value: JSON.stringify(theme) }
    const file = disk.get(slashes(e.path))
    if (file === undefined) return { deny: 'ENOENT' }
    return { value: file }
  })
  on('fs.write', ($, e) => {
    disk.set(slashes(e.path), e.text)
    return { value: undefined }
  })

  return { disk, statuses, clock }
}

const start = { cwd: '/project', surface: 'terminal' as const, isInteractive: true }

test('CLAUDE_THEME gives the session its theme and persona', { options: { persona: true } }, async ($, on) => {
  const { disk, statuses } = stage(on, { CLAUDE_THEME: 'dracula' })
  await $.session.start(start)

  expect(statuses.at(-1)).toBe('🧛 Dracula · ready')
  const { sections } = await $.prompt.compose(COMPOSE)
  expect(sections.map(section => section.id)).toEqual(['intro', 'ambiance:persona'])
  expect(sections[1]?.text).toContain('Gothic tone.')
  expect(JSON.parse(disk.get(`${DATA}/sessions/session-1.json`) ?? '{}').theme).toBe('dracula')
})

test('without a theme, the session stays untouched', async ($, on) => {
  const { statuses } = stage(on, {})
  await $.session.start(start)

  expect(statuses.at(-1)).toBe(undefined)
  const { sections } = await $.prompt.compose(COMPOSE)
  expect(sections.map(section => section.id)).toEqual(['intro'])
})

test('the theme switches live when the app assigns another one', { options: { persona: true } }, async ($, on) => {
  const { disk, statuses, clock } = stage(on, { CLAUDE_THEME: 'dracula' })
  await $.session.start(start)

  disk.set(`${DATA}/assign/session-1.json`, JSON.stringify({ theme: 'nord', at: 5 }))
  await clock.advance(2_000)

  expect(statuses.at(-1)).toBe('❄️ Nord · ready')
  const { sections } = await $.prompt.compose(COMPOSE)
  expect(sections[1]?.text).toContain('Calm tone.')
})

test('the persona is off by default', async ($, on) => {
  stage(on, { CLAUDE_THEME: 'dracula' })
  await $.session.start(start)

  const { sections } = await $.prompt.compose(COMPOSE)
  expect(sections.map(section => section.id)).toEqual(['intro'])
})

for (const surface of ['terminal', 'desktop'] as const) {
  test(`the banner shows and hides (${surface})`, async ($, on) => {
    stage(on, { CLAUDE_THEME: 'dracula' })
    await $.session.start(start)

    const band = await $.ui.mount({ plugin: 'ambiance', surface, component: 'AbovePrompt', props: BAND })
    // In the terminal, the title and quote are lines of colored cells.
    const title = surface === 'terminal' ? { type: 'Raster', key: 'title' } : { text: /DRACULA/ }
    expect(await band.find(title)).toBeDefined()
    if (surface === 'desktop') expect(await band.find({ text: /The night is young/ })).toBeDefined()

    await band.press({ key: 'hide' })
    expect(await band.find(title)).toBeUndefined()
  })
}

test('pixel art is a Raster in the terminal, ASCII elsewhere', async ($, on) => {
  stage(on, { CLAUDE_THEME: 'pixel' })
  await $.session.start(start)

  const terminal = await $.ui.mount({ plugin: 'ambiance', surface: 'terminal', component: 'AbovePrompt', props: BAND })
  const raster = await terminal.find({ type: 'Raster', key: 'logo' })
  expect(raster?.props).toMatchObject({ columns: 2, rows: 1 })

  const desktop = await $.ui.mount({ plugin: 'ambiance', surface: 'desktop', component: 'AbovePrompt', props: BAND })
  expect(await desktop.find({ type: 'Raster' })).toBeUndefined()
  expect(await desktop.find({ text: /ASCII/ })).toBeDefined()
})

test('a failing test makes the theme angry, a passing one makes it proud', async ($, on) => {
  const { statuses, disk } = stage(on, { CLAUDE_THEME: 'pixel' })
  let isFailing = true
  on('tool.call', () => (isFailing ? { isError: true as const, result: 'failed', text: 'failed' } : { result: 'ok', text: 'ok' }))
  await $.session.start(start)

  await $.tool.call({ tool: 'Bash', command: 'npm test' })
  expect(statuses.at(-1)).toBe('✦ Pixel · angry')
  expect(JSON.parse(disk.get(`${DATA}/events/session-1.json`) ?? '{}').type).toBe('error')

  isFailing = false
  await $.tool.call({ tool: 'Bash', command: 'cd app && npm run build' })
  expect(statuses.at(-1)).toBe('✦ Pixel · proud')
})

test('commands that only mention tests leave the mood alone', async ($, on) => {
  const { statuses } = stage(on, { CLAUDE_THEME: 'pixel' })
  on('tool.call', () => ({ isError: true as const, result: 'failed', text: 'failed' }))
  await $.session.start(start)

  await $.tool.call({ tool: 'Bash', command: 'git commit -m "fix the tests"' })
  await $.tool.call({ tool: 'Bash', command: 'test -f tests/a.py' })
  expect(statuses.at(-1)).toBe('✦ Pixel · ready')
})

test('a .ambiance.json in a parent folder sets the project theme', async ($, on) => {
  const { statuses } = stage(on, {}, { '/project/.ambiance.json': JSON.stringify({ theme: 'nord' }) })
  await $.session.start({ ...start, cwd: '/project/src/module' })

  expect(statuses.at(-1)).toBe('❄️ Nord · ready')
})

test('CLAUDE_THEME wins over the project theme', async ($, on) => {
  const { statuses } = stage(on, { CLAUDE_THEME: 'dracula' }, { '/project/.ambiance.json': JSON.stringify({ theme: 'nord' }) })
  await $.session.start({ ...start, cwd: '/project' })

  expect(statuses.at(-1)).toBe('🧛 Dracula · ready')
})

test('the minimal style keeps only the status line and the session label', { options: { style: 'minimal' } }, async ($, on) => {
  const { statuses } = stage(on, { CLAUDE_THEME: 'dracula' })
  await $.session.start(start)

  expect(statuses.at(-1)).toBe('🧛 Dracula · ready')
  const band = await $.ui.mount({ plugin: 'ambiance', surface: 'terminal', component: 'AbovePrompt', props: BAND })
  expect(await band.find({ text: /engine/ })).toBeDefined()
  expect(await band.find({ type: 'Raster' })).toBeUndefined()
})

test('the compact style draws a one-line banner', { options: { style: 'compact' } }, async ($, on) => {
  stage(on, { CLAUDE_THEME: 'pixel' })
  await $.session.start(start)

  const band = await $.ui.mount({ plugin: 'ambiance', surface: 'terminal', component: 'AbovePrompt', props: BAND })
  expect(await band.find({ type: 'Raster', key: 'logo' })).toBeUndefined()
  expect(await band.find({ text: /Pixel/ })).toBeDefined()
})

test('/ambiance style switches and remembers the style', async ($, on) => {
  stage(on, { CLAUDE_THEME: 'dracula' })
  await $.session.start(start)

  const ran = await $.command.run({ command: 'ambiance', args: 'style minimal', origin: { kind: 'composer' } } as never)
  expect(ran.text).toContain('minimal')
  const band = await $.ui.mount({ plugin: 'ambiance', surface: 'terminal', component: 'AbovePrompt', props: BAND })
  expect(await band.find({ type: 'Raster' })).toBeUndefined()
})

for (const surface of ['terminal', 'desktop'] as const) {
  test(`the session label joins the prompt footer (${surface})`, async ($, on) => {
    // Stands for the engine's footer, ahead of the generic stub in stage().
    on('ui.render', { component: 'SessionMode' }, ($, e) => {
      const { Text } = $.ui.resolve(e)
      return <Text>{e.props.modes.join(' & ')}</Text>
    })
    stage(on, { CLAUDE_THEME: 'dracula' })
    await $.session.start(start)

    const footer = await $.ui.mount({ plugin: 'ambiance', surface, component: 'SessionMode', props: { modes: ['focus'] } })
    expect(await footer.find({ text: 'focus & 🧛 Dracula' })).toBeDefined()
  })
}

test('preferences set by the app in config.json apply live', async ($, on) => {
  const { disk, clock } = stage(on, { CLAUDE_THEME: 'pixel' })
  await $.session.start(start)

  disk.set(`${DATA}/config.json`, JSON.stringify({ style: 'minimal' }))
  await clock.advance(2_000)
  const band = await $.ui.mount({ plugin: 'ambiance', surface: 'terminal', component: 'AbovePrompt', props: BAND })
  expect(await band.find({ type: 'Raster' })).toBeUndefined()
})

test('/ambiance writes its preferences to config.json for the app', async ($, on) => {
  const { disk } = stage(on, { CLAUDE_THEME: 'dracula' })
  await $.session.start(start)

  await $.command.run({ command: 'ambiance', args: 'sounds on', origin: { kind: 'composer' } } as never)
  expect(JSON.parse(disk.get(`${DATA}/config.json`) ?? '{}').sounds).toBe(true)
})

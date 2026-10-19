// Animated previews of the terminal effects (the Windows Terminal shaders),
// replayed on a canvas.

export const EFFECTS: { id: string | null; name: string }[] = [
  { id: null, name: 'None' },
  { id: 'stars', name: 'Stars' },
  { id: 'embers', name: 'Embers' },
  { id: 'snow', name: 'Snow' },
  { id: 'rain', name: 'Rain' },
  { id: 'petals', name: 'Petals' },
  { id: 'fireflies', name: 'Fireflies' },
  { id: 'bubbles', name: 'Bubbles' },
  { id: 'matrix', name: 'Matrix' },
  { id: 'crt', name: 'CRT' },
  { id: 'glow', name: 'Neon' },
]

type Particle = { x: number; y: number; r: number; speed: number; phase: number }

export function startEffect(canvas: HTMLCanvasElement, kind: string | null): () => void {
  const context = canvas.getContext('2d')
  if (context === null || kind === null) return () => undefined
  const ratio = window.devicePixelRatio || 1
  const width = (canvas.width = canvas.clientWidth * ratio)
  const height = (canvas.height = canvas.clientHeight * ratio)
  const counts: Record<string, number> = { stars: 90, embers: 70, snow: 110, rain: 140, matrix: 40, bubbles: 40, fireflies: 45, petals: 60 }
  const particles: Particle[] = Array.from({ length: counts[kind] ?? 45 }, () => ({
    x: Math.random() * width,
    y: Math.random() * height,
    r: (1.2 + Math.random() * 2) * ratio,
    speed: (0.2 + Math.random() * 0.8) * ratio,
    phase: Math.random() * Math.PI * 2,
  }))
  let frame = 0
  let running = true

  const wrap = (p: Particle, upward: boolean) => {
    if (upward && p.y < -10) Object.assign(p, { y: height + 10, x: Math.random() * width })
    if (!upward && p.y > height + 10) Object.assign(p, { y: -10, x: Math.random() * width })
  }

  const draw = (time: number) => {
    if (!running) return
    const t = time / 1000
    context.clearRect(0, 0, width, height)
    if (kind === 'crt') {
      context.fillStyle = 'rgba(0, 0, 0, 0.22)'
      for (let y = 0; y < height; y += 3 * ratio) context.fillRect(0, y, width, ratio)
      const vignette = context.createRadialGradient(width / 2, height / 2, height * 0.3, width / 2, height / 2, width * 0.75)
      vignette.addColorStop(0, 'rgba(0,0,0,0)')
      vignette.addColorStop(1, `rgba(0,0,0,${0.45 + 0.03 * Math.sin(t * 50)})`)
      context.fillStyle = vignette
      context.fillRect(0, 0, width, height)
    } else if (kind === 'glow') {
      const pulse = 0.18 + 0.08 * Math.sin(t * 1.5)
      const glow = context.createRadialGradient(width * 0.3, height * 0.5, 0, width * 0.3, height * 0.5, width * 0.6)
      glow.addColorStop(0, `rgba(160, 140, 255, ${pulse})`)
      glow.addColorStop(1, 'rgba(160, 140, 255, 0)')
      context.fillStyle = glow
      context.fillRect(0, 0, width, height)
    } else {
      for (const p of particles) {
        switch (kind) {
          case 'embers': {
            p.y -= p.speed * 0.9
            p.x += Math.sin(t + p.phase) * 0.3 * ratio
            wrap(p, true)
            const flicker = 0.55 + 0.45 * Math.sin(t * 7 + p.phase)
            context.fillStyle = `rgba(255, ${130 + Math.round(60 * flicker)}, 60, ${flicker * (0.35 + 0.65 * (p.y / height))})`
            context.shadowColor = 'rgba(255, 140, 50, 0.9)'
            context.shadowBlur = 6 * ratio
            break
          }
          case 'snow':
            p.y += p.speed * 0.6
            p.x += Math.sin(t * 0.8 + p.phase) * 0.4 * ratio
            wrap(p, false)
            context.fillStyle = 'rgba(225, 235, 255, 0.85)'
            break
          case 'petals':
            p.y += p.speed * 0.5
            p.x -= p.speed * 0.4 + Math.sin(t + p.phase) * 0.5 * ratio
            if (p.x < -10) p.x = width + 10
            wrap(p, false)
            context.fillStyle = 'rgba(255, 170, 195, 0.9)'
            context.beginPath()
            context.ellipse(p.x, p.y, p.r * 2, p.r, t + p.phase, 0, Math.PI * 2)
            context.fill()
            continue
          case 'rain':
            p.y += p.speed * 6
            wrap(p, false)
            context.strokeStyle = 'rgba(190, 210, 255, 0.75)'
            context.lineWidth = 1.4 * ratio
            context.beginPath()
            context.moveTo(p.x, p.y)
            context.lineTo(p.x, p.y + 12 * ratio)
            context.stroke()
            continue
          case 'matrix':
            p.y += p.speed * 3
            wrap(p, false)
            for (let k = 0; k < 8; k++) {
              context.fillStyle = k === 0 ? 'rgba(200, 255, 210, 0.95)' : `rgba(40, 220, 90, ${0.7 - k * 0.08})`
              context.fillRect(Math.round(p.x / (10 * ratio)) * 10 * ratio, p.y - k * 12 * ratio, 6 * ratio, 9 * ratio)
            }
            continue
          case 'bubbles':
            p.y -= p.speed * 0.8
            p.x += Math.sin(t * 2 + p.phase) * 0.4 * ratio
            wrap(p, true)
            context.strokeStyle = 'rgba(140, 230, 255, 0.7)'
            context.lineWidth = ratio
            context.beginPath()
            context.arc(p.x, p.y, p.r * 2.5, 0, Math.PI * 2)
            context.stroke()
            continue
          case 'fireflies': {
            p.x += Math.sin(t * 0.5 + p.phase) * 0.5 * ratio
            p.y += Math.cos(t * 0.4 + p.phase) * 0.4 * ratio
            const blink = Math.max(0, Math.sin(t * (1 + p.speed) + p.phase))
            context.fillStyle = `rgba(245, 230, 110, ${blink})`
            context.shadowColor = 'rgba(245, 230, 110, 0.9)'
            context.shadowBlur = 8 * ratio
            break
          }
          default: {
            const twinkle = 0.35 + 0.65 * (0.5 + 0.5 * Math.sin(t * (1 + p.speed) + p.phase))
            context.fillStyle = `rgba(200, 215, 255, ${twinkle})`
          }
        }
        context.beginPath()
        context.arc(p.x, p.y, p.r, 0, Math.PI * 2)
        context.fill()
        context.shadowBlur = 0
      }
    }
    frame = requestAnimationFrame(draw)
  }
  frame = requestAnimationFrame(draw)
  return () => {
    running = false
    cancelAnimationFrame(frame)
  }
}

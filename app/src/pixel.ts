// A theme's pixel art as SVG, for the app's previews.

export type PixelArt = { palette: Record<string, string>; fps?: number; frames: string[][] }

const cache = new Map<string, string>()

/** One pixel-art frame; neighboring pixels of the same color become a single rectangle. */
export function pixelSvg(art: PixelArt, frameIndex: number, className = 'pixel'): string {
  const frames = art.frames.filter(f => Array.isArray(f) && f.length > 0)
  const frame = frames[frameIndex % Math.max(1, frames.length)]
  if (frame === undefined) return ''
  const key = `${className}|${JSON.stringify(art.palette)}|${frame.join('/')}`
  const cached = cache.get(key)
  if (cached !== undefined) return cached

  const width = Math.max(...frame.map(row => row.length))
  const rects: string[] = []
  frame.forEach((row, y) => {
    let x = 0
    while (x < row.length) {
      const color = art.palette[row[x] ?? '.']
      let run = 1
      while (x + run < row.length && row[x + run] === row[x]) run++
      if (color !== undefined && /^#[0-9a-fA-F]{6}$/.test(color)) {
        rects.push(`<rect x="${x}" y="${y}" width="${run}" height="1" fill="${color}"/>`)
      }
      x += run
    }
  })
  const svg = `<svg class="${className}" viewBox="0 0 ${width} ${frame.length}" shape-rendering="crispEdges" aria-hidden="true">${rects.join('')}</svg>`
  cache.set(key, svg)
  return svg
}

// Design-token guard (PLT-001 AC1, AC11): raw colours, pixel sizes and arbitrary Tailwind
// colour/size values may only appear in src/styles/tokens.css (specs/ui-design-system.md).
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join, relative } from 'node:path'

const ROOT = new URL('../src', import.meta.url).pathname
const ALLOWED = new Set(['styles/tokens.css'])

const RULES = [
  { pattern: /#[0-9a-fA-F]{3,8}\b/, why: 'raw hex colour — use a colour token' },
  { pattern: /\b\d+(\.\d+)?px\b/, why: 'pixel value — use a spacing/size/text token' },
  { pattern: /\b(?:text|bg|border|fill|stroke|outline|ring)-\[/, why: 'arbitrary Tailwind value — use a token' },
  { pattern: /\brgba?\(|\bhsla?\(/, why: 'raw colour function — use a colour token' },
]

function* files(dir) {
  for (const name of readdirSync(dir)) {
    const path = join(dir, name)
    if (statSync(path).isDirectory()) yield* files(path)
    else if (/\.(tsx?|css)$/.test(name) && !/\.test\.tsx?$/.test(name)) yield path
  }
}

const problems = []
for (const file of files(ROOT)) {
  const rel = relative(ROOT, file)
  if (ALLOWED.has(rel)) continue
  readFileSync(file, 'utf8')
    .split('\n')
    .forEach((line, i) => {
      if (/^\s*(\/\/|\/?\*)/.test(line)) return // comments may mention sizes
      for (const { pattern, why } of RULES) {
        if (pattern.test(line)) problems.push(`src/${rel}:${i + 1}: ${why}\n    ${line.trim()}`)
      }
    })
}

if (problems.length) {
  console.error(`Design-token check failed (${problems.length}):\n${problems.join('\n')}`)
  process.exit(1)
}
console.log('Design-token check passed.')

import { test } from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'

const source = fs.readFileSync(new URL('../src/router/index.ts', import.meta.url), 'utf8')

test('the ordinary homepage opens running overview instead of digital twin', () => {
  assert.match(source, /path:\s*['"]\/['"]\s*,\s*redirect:\s*['"]\/general['"]/)
  assert.match(source, /path:\s*['"]\/general['"]\s*,\s*name:\s*['"]General['"]\s*,\s*component:/)
})

test('explicit digital twin deep links remain pages rather than redirecting to overview', () => {
  assert.match(source, /path:\s*['"]\/digital-twin['"]\s*,\s*\/\/[^\n]*\n\s*name:\s*['"]DigitalTwin['"][\s\S]*?component:/)
})

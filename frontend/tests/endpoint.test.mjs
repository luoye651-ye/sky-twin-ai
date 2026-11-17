import { test } from 'node:test'
import assert from 'node:assert/strict'
import { apiUrl } from '../src/api/endpoint.ts'
test('local API paths stay local and hosted paths use the configured HTTPS gateway', () => {
  const old = globalThis.window
  try {
    globalThis.window = {}
    assert.equal(apiUrl('/java-api/sky/snapshot'), '/java-api/sky/snapshot')
    globalThis.window = { SKYTWIN_DEPLOYMENT: { apiOrigin: 'https://gateway.example.test' } }
    assert.equal(apiUrl('/agent-api/chat'), 'https://gateway.example.test/agent-api/chat')
    assert.throws(() => apiUrl('https://evil.test'), /无效/)
    globalThis.window.SKYTWIN_DEPLOYMENT.apiOrigin = 'http://gateway.example.test'
    assert.throws(() => apiUrl('/agent-api/chat'), /HTTPS/)
  } finally { globalThis.window = old }
})

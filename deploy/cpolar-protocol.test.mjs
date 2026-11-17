import { test } from 'node:test'
import assert from 'node:assert/strict'
import { establishedHttpsOrigin } from './cpolar-protocol.mjs'
test('cpolar 3.3.12 logfmt supplies only the established HTTPS tunnel, never auth or dashboard URLs', () => {
  const sample = 'time="2026-11-16T19:15:51+08:00" level=info msg="[:tunnel server module] Tunnel established at https://968b1d0.r9.cpolar.cn"'
  assert.equal(establishedHttpsOrigin(sample), 'https://968b1d0.r9.cpolar.cn')
  for (const text of ['Tunnel established at http://968b1d0.r9.cpolar.cn', 'Tunnel established at https://evil.test', 'Authentication failed; visit https://dashboard.cpolar.com', 'Tunnel established at https://dashboard.cpolar.com', 'Tunnel established at https://cpolar.cn.evil.test', 'authenticated with tunnel server']) assert.equal(establishedHttpsOrigin(text), '', text)
})

// Anonymous localhost.run tunnel. Address changes register automatically with
// the fixed Sites API bridge. No API credentials or request bodies are logged.
import { spawn } from 'node:child_process'
import { writeFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const bridge = 'https://skytwin-ai-gateway.spicyangel15.chatgpt.site'
let child, stopped = false, current = '', pending = '', registering = false
async function register(origin) {
  pending = origin
  if (registering) return
  registering = true
  try {
    while (!stopped && pending) {
      const target = pending
      try {
        // Python follows the Windows system proxy; Node fetch does not. Use
        // the same HTTPS path that successfully reaches Sites on this machine.
        const registerProcess = spawn('python', [path.join(root, 'deploy/register-tunnel.py'), target], { windowsHide: true, stdio: 'ignore' })
        const code = await new Promise(resolve => { registerProcess.once('close', resolve); registerProcess.once('error', () => resolve(1)) })
        if (code !== 0) throw new Error('registration failed')
        if (pending === target) pending = ''
        current = target
        writeFileSync(path.join(root, '.runtime/public-tunnel-state.json'), JSON.stringify({ origin: current, bridge, updated: new Date().toISOString() }))
        console.log('Registered active tunnel with fixed API bridge')
      } catch { console.log('API bridge not ready; retrying registration'); await new Promise(resolve => setTimeout(resolve, 5000)) }
    }
  } finally { registering = false }
}
async function connect() {
  while (!stopped) {
    child = spawn('ssh', ['-o', 'BatchMode=yes', '-o', 'ConnectTimeout=12', '-o', 'StrictHostKeyChecking=accept-new', '-o', 'UserKnownHostsFile=' + path.join(root, '.runtime/tunnel-known-hosts').replaceAll('\\', '/'), '-o', 'ExitOnForwardFailure=yes', '-o', 'ServerAliveInterval=30', '-o', 'ServerAliveCountMax=3', '-T', '-R', '80:127.0.0.1:5181', 'nokey@localhost.run', '--', '--output', 'json'], { windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] })
    let buffer = ''
    child.stdout.on('data', chunk => {
      buffer += chunk.toString()
      const lines = buffer.split('\n'); buffer = lines.pop() || ''
      for (const line of lines) {
        const start = line.indexOf('{'); if (start < 0) continue
        try { const event = JSON.parse(line.slice(start).trim()); const domain = event?.data?.address; if (event.type === 'run.localhost.tunnel.registered' && /^[a-z0-9]+\.app\.lhr\.life$/.test(domain)) void register('https://' + domain) } catch { /* Ignore provider banners. */ }
      }
    })
    child.stderr.on('data', () => {})
    await new Promise(resolve => { child.once('close', resolve); child.once('error', resolve) })
    if (!stopped) { console.log('Tunnel disconnected; reconnecting'); await new Promise(resolve => setTimeout(resolve, 5000)) }
  }
}
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => { stopped = true; child?.kill() })
await connect()

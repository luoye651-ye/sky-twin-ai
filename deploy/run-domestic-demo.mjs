import { spawn } from 'node:child_process'
import { readFileSync, existsSync, writeFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { createDomesticServer } from './domestic-server.mjs'
import { establishedHttpsOrigin } from './cpolar-protocol.mjs'
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const executable = path.join(root, '.runtime/cpolar-portable/cpolar/cpolar.exe')
const config = path.join(root, '.runtime/cpolar-skytwin.yml')
if (!existsSync(executable) || !existsSync(config)) throw new Error('Prepare the official cpolar client and run configure-domestic-demo.ps1 first')
if (!/authtoken:\s*"[^"\r\n]{16,}"/.test(readFileSync(config, 'utf8'))) throw new Error('Project cpolar authentication has not been configured')
const environment = { ...process.env }
for (const key of Object.keys(environment)) if (/^(https?|all|socks)_proxy$/i.test(key)) delete environment[key]
let stopped = false, child, site, current = ''
let update = Promise.resolve()
const delay = ms => new Promise(resolve => setTimeout(resolve, ms))
function activate(origin) {
  update = update.then(async () => {
    if (stopped || !origin || current === origin) return
    site?.close()
    site = await createDomesticServer({ publicOrigin: origin })
    current = origin
    writeFileSync(path.join(root, '.runtime/domestic-demo.json'), JSON.stringify({ publicOrigin: origin, updated: new Date().toISOString(), provider: 'cpolar', region: 'cn' }, null, 2))
    console.log('Domestic demo ready: ' + origin)
  }).catch(() => { console.log('Domestic website activation is pending; check local port 5182') })
  return update
}
async function connect() {
  while (!stopped) {
    child = spawn(executable, ['http', '-config=' + config, '-region=cn', '-proto=https', '-inspect-addr=false', '-log=stdout', '-log-level=INFO', '-tunnelName=skytwin', '127.0.0.1:5182'], { env: environment, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] })
    // 3.3.12 uses logfmt, not -log-format=json. Parse only tunnel-established
    // URL events; disable its HTTP inspector entirely so login bodies cannot
    // be captured by a local debug dashboard. Never echo authentication logs.
    const receive = () => {
      let buffer = ''
      return chunk => {
        buffer += chunk.toString()
        const lines = buffer.split('\n'); buffer = lines.pop() || ''
        if (buffer.length > 65536) buffer = ''
        for (const line of lines) {
          const origin = establishedHttpsOrigin(line)
          if (origin) void activate(origin)
        }
      }
    }
    child.stdout.on('data', receive()); child.stderr.on('data', receive())
    await new Promise(resolve => { child.once('close', resolve); child.once('error', resolve) })
    if (!stopped) { site?.close(); site = undefined; current = ''; console.log('cpolar disconnected; retrying without a proxy'); await delay(5000) }
  }
}
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => { stopped = true; child?.kill(); site?.close() })
await connect()

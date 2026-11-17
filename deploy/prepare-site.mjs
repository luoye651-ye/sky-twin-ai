import { cpSync, mkdirSync, readFileSync, writeFileSync, existsSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const origin = process.argv[2]
if (!origin || new URL(origin).origin !== origin || !origin.startsWith('https://')) throw new Error('Pass the current HTTPS tunnel origin')
const site = path.join(root, 'deploy/sites-skytwin')
if (existsSync(path.join(site, 'web'))) throw new Error('Existing prepared web directory must be archived before refreshing; nothing overwritten')
mkdirSync(path.join(site, 'web'), { recursive: true })
cpSync(path.join(root, 'frontend/dist'), path.join(site, 'web'), { recursive: true })
writeFileSync(path.join(site, 'web/deployment-config.js'), 'window.SKYTWIN_DEPLOYMENT = ' + JSON.stringify({ apiOrigin: origin }) + ';\n')
const manifestPath = path.join(site, '.openai/hosting.json')
const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'))
manifest.static.not_found_handling = 'single-page-application'
writeFileSync(manifestPath, JSON.stringify(manifest, null, 2) + '\n')
writeFileSync(path.join(root, '.runtime/public-deployment.json'), JSON.stringify({ projectId: manifest.project_id, siteOrigin: 'https://skytwin-ai-demo.spicyangel15.chatgpt.site', apiOrigin: origin, preparedUtc: new Date().toISOString() }, null, 2) + '\n')
console.log('Prepared Site assets; no local credentials or backend files copied')

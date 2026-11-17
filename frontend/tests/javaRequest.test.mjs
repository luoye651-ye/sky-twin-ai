import { test } from 'node:test'
import assert from 'node:assert/strict'
import { javaRequest, getSkyToken, setSkyToken } from '../src/api/sky.ts'

globalThis.document = { cookie: '' }

test('independent demo login and logout preserve the real platform cookie', () => {
  const old=globalThis.document, jar=new Map();let demo=false
  globalThis.document={querySelector:()=>demo?{getAttribute:()=> 'isolated'}:null,
    get cookie(){return [...jar].map(([k,v])=>`${k}=${v}`).join('; ')},
    set cookie(text){const [pair]=text.split(';');const [name,value]=pair.split('=');if(text.includes('Max-Age=0'))jar.delete(name);else jar.set(name,value)}}
  try {
    setSkyToken('real-fixture');demo=true;setSkyToken('demo-fixture')
    assert.equal(getSkyToken(),'demo-fixture');setSkyToken()
    assert.equal(getSkyToken(),undefined);demo=false;assert.equal(getSkyToken(),'real-fixture')
  } finally {globalThis.document=old}
})

test('Java requests distinguish unavailable services from business errors', async (t) => {
  const originalFetch = globalThis.fetch
  t.after(() => { globalThis.fetch = originalFetch })

  await t.test('empty proxy error explains how to start the backend', async () => {
    globalThis.fetch = async () => new Response('', { status: 500 })
    await assert.rejects(javaRequest('/captchaImage'), /后端服务暂不可用.*500.*start\.ps1/)
  })

  await t.test('HTML response reports invalid API output', async () => {
    globalThis.fetch = async () => new Response('<html>index</html>', { status: 200 })
    await assert.rejects(javaRequest('/captchaImage'), /接口返回格式异常/)
  })

  await t.test('network failure has a readable message', async () => {
    globalThis.fetch = async () => { throw new TypeError('Failed to fetch') }
    await assert.rejects(javaRequest('/captchaImage'), /无法连接服务/)
  })

  await t.test('JSON business errors keep the server message', async () => {
    globalThis.fetch = async () => Response.json({ code: 500, msg: '验证码错误' })
    await assert.rejects(javaRequest('/login', 'POST', {}), /验证码错误/)
  })

  await t.test('successful captcha is returned unchanged', async () => {
    const captcha = { code: 200, uuid: 'test-uuid', img: 'test-image', captchaEnabled: true }
    globalThis.fetch = async () => Response.json(captcha)
    assert.deepEqual(await javaRequest('/captchaImage'), captcha)
  })

  await t.test('null JSON is treated as invalid output', async () => {
    globalThis.fetch = async () => Response.json(null)
    await assert.rejects(javaRequest('/captchaImage'), /接口返回格式异常/)
  })
})

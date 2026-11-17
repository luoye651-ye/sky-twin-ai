<script setup lang="ts">
import { onMounted, reactive, shallowRef } from 'vue'
import { useSkyStore } from '../../stores/sky'
import { javaRequest } from '../../api/sky'
import { isolatedDemo } from '../../utils/runtime'
const sky = useSkyStore()
const form = reactive({ username: '', password: '', code: '', uuid: '' })
const image = shallowRef('')
const captchaEnabled = shallowRef(true)
const submitting = shallowRef(false)
const error = shallowRef('')
async function captcha() {
  error.value = ''; image.value = ''; form.uuid = ''; form.code = ''
  try { const data = await javaRequest('/captchaImage'); form.uuid = data.uuid; image.value = data.img ? `data:image/png;base64,${data.img}` : ''; captchaEnabled.value = data.captchaEnabled }
  catch (e) { error.value = e instanceof Error ? e.message : '验证码加载失败' }
}
async function submit() {
  submitting.value = true; error.value = ''
  try { await sky.login(form); if (!sky.authorized) error.value = sky.error }
  catch (e) { error.value = e instanceof Error ? e.message : '登录失败'; await captcha() }
  finally { submitting.value = false }
}
onMounted(captcha)
</script>
<template>
  <section class="auth-layout"><form class="auth-card" @submit.prevent="submit">
    <span class="eyebrow">SKYTWIN · SIMULATION</span><h1>进入低空指挥中心</h1><p>{{ isolatedDemo ? '独立样例环境：使用本机生成的demo账号密码，不连接真实Java业务，不调用外部模型。' : '使用若依账号登录，两端共享业务数据与操作权限。' }}</p>
    <el-alert v-if="error || sky.error" :title="error || sky.error" type="error" :closable="false" />
    <label>账号<el-input v-model="form.username" autocomplete="username" placeholder="若依账号" /></label>
    <label>密码<el-input v-model="form.password" type="password" autocomplete="current-password" show-password /></label>
    <label v-if="captchaEnabled">验证码<div class="captcha-row"><el-input v-model="form.code" placeholder="填写验证码" /><button type="button" class="captcha-button" aria-label="刷新验证码" @click="captcha"><img v-if="image" :src="image" alt="登录验证码" /><span v-else>重新加载</span></button></div></label>
    <el-button type="primary" native-type="submit" :loading="submitting || sky.loading" class="login-button">登录指挥中心</el-button>
    <a href="http://127.0.0.1:5174" target="_blank" rel="noopener noreferrer">打开若依业务管理 ↗</a>
  </form></section>
</template>
<style scoped>
.auth-layout { min-height: 100%; display: grid; place-items: center; background: radial-gradient(ellipse at 50% 0%, #0a3449, #050d18 65%); padding: 24px; }
.auth-card { width: min(440px,100%); padding: 36px; border: 1px solid #225574; background: #091b2bef; border-radius: 12px; box-shadow: 0 0 55px #02beff12; }
.eyebrow { color: #58d3ff; letter-spacing: 3px; font-size: 11px; }.auth-card h1 { font-size: 25px; }.auth-card p { color: #92a9bc; line-height: 1.7; }
.auth-card label { display: grid; gap: 10px; margin: 20px 0; font-size: 14px; }.captcha-row { display: flex; gap: 12px; }
.captcha-button { border: 0; padding: 0; background: white; cursor: pointer; min-width: 120px; }.captcha-button img { width: 120px; height: 38px; vertical-align: middle; }
.login-button { width: 100%; margin-bottom: 20px; }.auth-card a { color: #58d3ff; font-size: 13px; }
</style>

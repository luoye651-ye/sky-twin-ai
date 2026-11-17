<script setup lang="ts">
import { RouterView } from 'vue-router'
import AppHeader from './components/layout/AppHeader.vue'
import { onMounted, onUnmounted } from 'vue'
import AuthPanel from './components/business/AuthPanel.vue'
import { useSkyStore } from './stores/sky'
import { isolatedDemo } from './utils/runtime'
const sky = useSkyStore()
onMounted(() => sky.initialize())
onUnmounted(() => sky.disconnect())
</script>

<template>
<!-- 整体容器 -->
  <div class="layout">
    <!-- 顶部导航栏 -->
    <AppHeader v-if="!isolatedDemo"/><div v-else class="account-bar">SkyTwin · 独立合成样例演示 · 禁止实机/真实业务操作</div>
    <!-- 页面内容区域，访问哪个路由就显示哪个页面 -->
    <main class="content">
      <AuthPanel v-if="!sky.authorized" />
      <template v-else>
        <div class="account-bar"><span>{{ sky.username }} · {{ sky.canOperate ? '可调度' : '只读' }}</span><a href="http://127.0.0.1:5174" target="_blank" rel="noopener noreferrer">业务管理 ↗</a><button @click="sky.logout().catch(() => {})">退出登录</button></div>
        <div class="route-body"><RouterView /></div>
      </template>
    </main>
  </div>
</template>

<style scoped>
.layout {
  display: flex;
  flex-direction: column;

  width: 100%;
  height: 100vh;

  overflow: hidden;
  background: #050d18;
}

.content {
  flex: 1;
  min-width: 0;
  min-height: 0;

  overflow: auto;
}
.account-bar { height: 36px; display: flex; justify-content: flex-end; align-items: center; gap: 20px; padding: 0 20px; color: #8facbf; font-size: 12px; border-bottom: 1px solid #163a52; }
.account-bar a { color: #58d3ff; }.account-bar button { background: none; border: 0; color: #8facbf; cursor: pointer; }.route-body { height: calc(100% - 36px); min-height: 0; }
</style>

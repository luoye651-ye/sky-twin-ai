<script setup name="SkyTwinHome">
import { useRouter } from 'vue-router'

const router = useRouter()
const consoleUrl = 'http://127.0.0.1:5173'
</script>

<template>
  <div class="app-container">
    <el-card shadow="never" class="project-home">
      <h1 class="project-title">SkyTwin 业务管理</h1>
      <p class="project-description">
        城市低空智能管控平台的运营管理入口，基于 RuoYi Vue 3 与 Spring Boot 3。
      </p>
      <p class="project-description">
        用户、角色、菜单权限、字典、操作日志和代码生成器已可使用。
        已接入飞行器、站点、五类任务、异常事件、任务摘要报告及业务操作记录。
      </p>
      <div class="project-actions">
        <el-button type="primary" @click="router.push('/sky-twin/tasks')">统一任务管理</el-button>
        <el-button @click="router.push('/sky-twin/aircraft')">飞行器管理</el-button>
        <el-button @click="router.push('/sky-twin/stations')">站点管理</el-button>
        <el-button type="primary" @click="router.push('/system/user')">用户管理</el-button>
        <el-button @click="router.push('/system/role')">角色权限</el-button>
        <el-button @click="router.push('/tool/gen')">代码生成</el-button>
        <a :href="consoleUrl" target="_blank" rel="noopener noreferrer" class="console-link">
          打开 SkyTwin 指挥中心 ↗
        </a>
      </div>
      <p class="project-note">
        指挥中心与后台共享 Java 业务数据，位置和任务状态由服务端仿真更新。当前不连接真实飞行器。
      </p>
    </el-card>
  </div>
</template>

<style scoped>
.project-home { max-width: 1100px; }
.project-title { margin: 4px 0 20px; font-size: 28px; }
.project-description { line-height: 1.9; color: var(--el-text-color-regular); }
.project-actions { display: flex; align-items: center; flex-wrap: wrap; gap: 12px; margin: 26px 0; }
.project-actions :deep(.el-button + .el-button) { margin-left: 0; }
.console-link { color: var(--el-color-primary); padding: 8px 0; }
.project-note { font-size: 13px; color: var(--el-text-color-secondary); line-height: 1.7; }
</style>

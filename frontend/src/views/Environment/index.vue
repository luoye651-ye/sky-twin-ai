<script setup lang="ts">
import { computed, defineAsyncComponent } from 'vue'
import { useRoute } from 'vue-router'
import PatrolWorkspace from '../../components/patrol/PatrolWorkspace.vue'
// Preserve historical incident links while replacing the normal environment entry.
const EnvironmentWorkspace = defineAsyncComponent(() => import('../../components/environment/EnvironmentWorkspace.vue'))
const route = useRoute()
const historicalDiscovery = computed(() => route.query.mode === 'evidence' || typeof route.query.discoveryId === 'string' && !!route.query.discoveryId)
</script>
<template>
  <nav class="environment-tabs"><RouterLink to="/environment">离线影像巡逻</RouterLink><RouterLink to="/environment?mode=evidence">上传检测 / 发现与处置</RouterLink></nav>
  <EnvironmentWorkspace v-if="historicalDiscovery" />
  <PatrolWorkspace v-else />
</template>

<style scoped>.environment-tabs{display:flex;gap:20px;padding:12px 24px}.environment-tabs a{color:#71cfe8}</style>

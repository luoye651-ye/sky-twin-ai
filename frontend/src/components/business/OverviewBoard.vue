<script setup lang="ts">
import { useSkyStore } from '../../stores/sky'
import OverviewDashboard from '../overview/OverviewDashboard.vue'
const sky = useSkyStore()
</script>
<template>
  <OverviewDashboard :snapshot="sky.snapshot" :connected="sky.connected" :error="sky.error" />
</template>

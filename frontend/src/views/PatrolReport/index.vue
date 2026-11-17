<script setup lang="ts">
import { useSkyStore } from '../../stores/sky'
import ReportsPanel from '../../components/business/ReportsPanel.vue'
import EnvironmentalReportList from '../../components/environment/EnvironmentalReportList.vue'
const sky = useSkyStore()
</script>
<template><EnvironmentalReportList /><ReportsPanel :reports="sky.snapshot.reports" /></template>

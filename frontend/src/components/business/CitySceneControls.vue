<script setup lang="ts">
import type { CityAppearance } from '../../views/DigitalTwin/cityAppearance'
defineProps<{ appearance: CityAppearance; traffic: boolean }>()
const emit = defineEmits<{ appearance: [mode: CityAppearance]; view: [mode: 'river' | 'district' | 'overview']; traffic: [visible: boolean] }>()
</script>
<template>
  <div class="view-controls">
    <div class="control-row" aria-label="场景外观">
      <button v-for="item in ([['dusk','暮色'],['day','日景'],['source','素模']] as const)" :key="item[0]" class="scene-button" :class="{ selected: appearance === item[0] }" :aria-pressed="appearance === item[0]" @click="emit('appearance', item[0])">{{ item[1] }}</button>
      <button class="scene-button" :aria-pressed="traffic" @click="emit('traffic', !traffic)">仿真车流：{{ traffic ? '开' : '关' }}</button>
    </div>
    <div class="control-row" aria-label="区域视角">
      <button class="scene-button" @click="emit('view', 'river')">钱塘江景</button>
      <button class="scene-button" @click="emit('view', 'district')">滨江城区</button>
      <button class="scene-button" @click="emit('view', 'overview')">全域总览</button>
    </div>
  </div>
</template>
<style scoped>
.view-controls { position: absolute; top: 18px; right: 18px; display: grid; gap: 7px; justify-items: end; }
.control-row { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 5px; }
.scene-button { color: #a9e1fa; border: 1px solid #28546d; border-radius: 4px; background: #0b2031ed; padding: 7px 10px; cursor: pointer; font-size: 12px; }
.scene-button.selected { color: #e1f8ff; border-color: #42bce6; background: #0c5475; }
@media (max-width: 1100px) { .view-controls { left: 20px; right: 20px; } }
</style>

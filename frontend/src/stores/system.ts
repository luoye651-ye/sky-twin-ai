// stores/system.ts
import { defineStore } from 'pinia'
import { shallowRef } from 'vue'

export const useSystemStore = defineStore('system', () => {
  const simulationEnabled = shallowRef(true)

  function toggleSimulation() {
    simulationEnabled.value = !simulationEnabled.value
  }

  return {
    simulationEnabled,
    toggleSimulation
  }
})
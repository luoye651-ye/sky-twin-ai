<script setup lang="ts">
import { shallowRef, useTemplateRef, watch } from 'vue'
import { useSkyStore } from '../../stores/sky'
import { useFlightNavigation } from '../../composables/useFlightNavigation'
import FleetPanel from '../business/FleetPanel.vue'
import CityViewport from '../business/CityViewport.vue'
import FlightNavigationPanel from './FlightNavigationPanel.vue'

const sky = useSkyStore()
const { tasks, selected, selectedId, display, trackError, selectTask } = useFlightNavigation()
const viewport = useTemplateRef('viewport')
const selectedAircraftId = shallowRef('')
function locateAircraft(id: string) {
  selectedAircraftId.value = id
  viewport.value?.focusAircraft(id)
}
watch(() => sky.snapshot.aircraft, aircraft => {
  if (selectedAircraftId.value && !aircraft.some(a => a.id === selectedAircraftId.value)) selectedAircraftId.value = ''
})
function locate() {
  const p = display.value?.navigation.position
  if (p) viewport.value?.focusPosition(p.longitude, p.latitude, p.altitude)
}
</script>

<template>
  <div class="digital-twin">
    <FleetPanel :aircraft="sky.snapshot.aircraft" :tasks="sky.snapshot.tasks" :connected="sky.connected" :selected-id="selectedAircraftId" @locate="locateAircraft" />
    <CityViewport ref="viewport" :aircraft="sky.snapshot.aircraft" :stations="sky.snapshot.stations" :tasks="sky.snapshot.tasks" :zones="sky.snapshot.airspaceZones" :flight-navigation="display" :selected-aircraft-id="selectedAircraftId">
      <template #overlay>
        <FlightNavigationPanel :tasks="tasks" :selected="selected" :selected-id="selectedId" :available="!!display" :connected="sky.connected" :track-error="trackError" @select="selectTask" @focus-route="viewport?.focusNavigation()" @locate="locate" />
      </template>
    </CityViewport>
  </div>
</template>

<style scoped>
.digital-twin { height:100%; min-height:650px; display:grid; grid-template-columns:310px minmax(0,1fr); gap:12px; padding:12px; }
@media(max-width:1100px) { .digital-twin { grid-template-columns:240px minmax(0,1fr); } }
@media(max-width:700px) { .digital-twin { grid-template-columns:minmax(0,1fr); }.digital-twin :deep(.fleet-panel) { display:none; } }
</style>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  state: {
    surge: number
    sway: number
    yaw: number
    u: number
    v: number
    r: number
  }
}>()

const speed = computed(() => Math.sqrt(props.state.u**2 + props.state.v**2).toFixed(2))
</script>

<template>
  <div class="dashboard">
    <h2>Ship Dashboard</h2>
    <div class="metrics">
      <div class="metric">
        <span class="label">Speed</span>
        <span class="value">{{ speed }} m/s</span>
      </div>
      <div class="metric">
        <span class="label">Heading</span>
        <span class="value">{{ (state.yaw * 180 / Math.PI).toFixed(1) }}°</span>
      </div>
      <div class="metric">
        <span class="label">Surge (x)</span>
        <span class="value">{{ state.surge.toFixed(2) }} m</span>
      </div>
      <div class="metric">
        <span class="label">Sway (y)</span>
        <span class="value">{{ state.sway.toFixed(2) }} m</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dashboard {
  background: #f0f0f0;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
}

.metrics {
  display: flex;
  gap: 20px;
}

.metric {
  display: flex;
  flex-direction: column;
}

.label {
  font-size: 0.8em;
  color: #666;
}

.value {
  font-size: 1.2em;
  font-weight: bold;
}
</style>

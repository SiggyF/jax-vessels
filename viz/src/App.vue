<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import Ship3D from './components/Ship3D.vue'
import ShipDashboard from './components/ShipDashboard.vue'

// Simulated state
const state = ref({
  surge: 0,
  sway: 0,
  yaw: 0,
  u: 0,
  v: 0,
  r: 0
})

// Simulated animation loop
let animationId: number
const animate = () => {
  // Simple harmonic motion simulation
  const t = Date.now() / 1000
  state.value.surge = Math.sin(t) * 2
  state.value.sway = Math.cos(t * 0.5) * 1
  state.value.yaw = Math.sin(t * 0.2) * 0.5
  state.value.u = Math.cos(t) * 2
  state.value.v = -Math.sin(t * 0.5) * 0.5
  state.value.r = Math.cos(t * 0.2) * 0.1
  
  animationId = requestAnimationFrame(animate)
}

onMounted(() => {
  animate()
})

onUnmounted(() => {
  cancelAnimationFrame(animationId)
})
</script>

<template>
  <div class="container">
    <header>
      <h1>Ship Dynamics Visualization</h1>
    </header>
    
    <main>
      <ShipDashboard :state="state" />
      <Ship3D 
        :position="[state.surge, 0, state.sway]" 
        :rotation="[0, state.yaw, 0]" 
      />
    </main>
  </div>
</template>

<style>
body {
  margin: 0;
  font-family: 'Inter', sans-serif;
  background: #fcfcfc;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

header {
  margin-bottom: 30px;
  border-bottom: 2px solid #eee;
}

h1 {
  color: #333;
}
</style>

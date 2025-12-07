<script setup lang="ts">
import { TresCanvas } from '@tresjs/core'
import { OrbitControls } from '@tresjs/cientos'

// Props for ship state
defineProps<{
  position: [number, number, number]
  rotation: [number, number, number]
}>()
</script>

<template>
  <div class="canvas-container">
    <TresCanvas clear-color="#82DBC5" window-size>
      <TresPerspectiveCamera :position="[10, 10, 10]" :look-at="[0, 0, 0]" />
      <OrbitControls />
      
      <TresAmbientLight :intensity="1" />
      <TresDirectionalLight :position="[10, 10, 10]" :intensity="1" />
      
      <!-- Ship Model Placeholder (Box) if GLTF not loaded -->
      <TresMesh :position="position" :rotation="rotation">
        <TresBoxGeometry :args="[2, 1, 0.5]" />
        <TresMeshStandardMaterial color="orange" />
      </TresMesh>
      
      <!-- Grid -->
      <TresGridHelper :args="[100, 100]" />
    </TresCanvas>
  </div>
</template>

<style scoped>
.canvas-container {
  width: 100%;
  height: 600px;
  border-radius: 8px;
  overflow: hidden;
}
</style>

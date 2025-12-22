<script setup lang="ts">
import MainMenuTop from '../components/layout/MainMenuTop.vue';
import MainMenuBottom from '../components/layout/MainMenuBottom.vue';
</script>
  
<template>
  <div class="layout-root-container">
    <MainMenuTop />
    <div class="main-content">
      <p>Main Content</p>
    </div>
    <MainMenuBottom />
  </div>
</template>

<style scoped>
.layout-root-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.main-content {
  flex: 1;
  overflow: auto;
}
</style>
<script setup lang="ts">
import MainMenuTop from '../components/layout/MainMenuTop.vue';
import MainMenuBottom from '../components/layout/MainMenuBottom.vue';
</script>
  
<template>
  <div class="layout-root-container">
    <MainMenuTop />
    <div class="layout-main-container">
      <div class="layout-main-container left-sidebar">Left Sidebar</div>
      <div class="layout-main-container content">Main Content</div>
      <div class="layout-main-container right-sidebar">Right Sidebar</div>
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

.layout-main-container {
  flex: 1;
  overflow: auto;
  display: flex;
  flex-direction: row;
}

.layout-main-container.left-sidebar {
  flex: 1;
  background-color: rgb(141, 90, 134);
}

.layout-main-container.content {
  flex: 4;
  background-color: rgb(125, 137, 131);
}

.layout-main-container.right-sidebar {
  flex: 1;
  background-color: rgb(109, 180, 144);
}
</style>
<script setup lang="ts">
import HomeMenuTop from '@/views/home/HomeMenuTop.vue';
import HomeMenuBottom from '@/views/home/HomeMenuBottom.vue';
</script>
  
<template>
  <div class="layout-root-container">
    <HomeMenuTop />
    <div class="layout-main-container">
      <div class="layout-main-container left-sidebar">Left Sidebar</div>
      <div class="layout-main-container content">
        <Flow />
      </div>
      <div class="layout-main-container right-sidebar">Right Sidebar</div>
    </div>
    <HomeMenuBottom />
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
  border-right: 1px solid var(--color-layout-border);
  /* background-color: rgb(141, 90, 134); */
}

.layout-main-container.content {
  flex: 4;
  /* background-color: rgb(125, 137, 131); */
}

.layout-main-container.right-sidebar {
  flex: 1;
  border-left: 1px solid var(--color-layout-border);
  /* background-color: rgb(109, 180, 144); */
}
</style>
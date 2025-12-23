<script setup lang="ts">
import HomeMenuTop from '@/views/home/HomeMenuTop.vue';
import HomeMenuBottom from '@/views/home/HomeMenuBottom.vue';
import HomeSidebarL from '@/views/home/HomeSidebarL.vue';
import HomeSidebarR from '@/views/home/HomeSidebarR.vue';
import HomePage from '@/views/home/HomePage.vue';
import ResizableContainer from '@/components/ResizableContainer.vue';
</script>
  
<template>
  <div class="layout-root-container">
    <HomeMenuTop />
    <ResizableContainer class="layout-main-container" direction="row">
      <HomeSidebarL weight="1"/>
      <HomePage weight="4"/>
      <HomeSidebarR weight="1"/>
    </ResizableContainer>
    <HomeMenuBottom />
  </div>
</template>

<style scoped>
.layout-root-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
}
</style>
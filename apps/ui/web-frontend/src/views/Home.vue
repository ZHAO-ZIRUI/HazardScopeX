<script setup lang="ts">
import HomeMenuTop from '@/views/home/HomeMenuTop.vue';
import HomeMenuBottom from '@/views/home/HomeMenuBottom.vue';
import HomeJobSidebar from '@/views/home/HomeJobSidebar.vue';
import HomePropsSidebar from '@/views/home/HomePropsSidebar.vue';
import HomeFlow from '@/views/home/HomeFlow.vue';
import ResizableContainer from '@/components/ResizableContainer.vue';
</script>
  
<template>
  <div class="layout-root-container">
    <HomeMenuTop />
    <ResizableContainer class="layout-main-container" direction="row">
      <HomeJobSidebar weight="1"/>
      <HomeFlow weight="4"/>
      <HomePropsSidebar weight="1"/>
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
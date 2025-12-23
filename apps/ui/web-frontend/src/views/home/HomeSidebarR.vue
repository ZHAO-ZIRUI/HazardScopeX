<script setup lang="ts">
import { computed } from 'vue';
import { useHomePageSelectorStore } from '@/stores/homePageSelector';
import { sidebarRComponents, defaultPage } from '@/views/home/pageMappings';

const store = useHomePageSelectorStore();

const currentSidebarR = computed(() => {
  return sidebarRComponents[store.currentPage] || sidebarRComponents[defaultPage];
});
</script>
<template>
  <component :is="currentSidebarR" />
</template>
<style scoped>

</style>
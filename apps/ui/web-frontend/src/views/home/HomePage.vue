<script setup lang="ts">
import { computed } from 'vue';
import { useHomePageSelectorStore } from '@/stores/homePageSelector';
import { pageComponents, defaultPage } from '@/views/home/pageMappings';

const store = useHomePageSelectorStore();

const currentPageComponent = computed(() => {
  return pageComponents[store.currentPage] || pageComponents[defaultPage];
});
</script>
<template>
  <component :is="currentPageComponent" />
</template>
<style scoped>

</style>
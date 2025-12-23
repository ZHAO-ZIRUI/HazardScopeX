<script setup lang="ts">
import { computed } from 'vue';
import { 
  AssemblyLine as IconAssemblyLine,
  Data as IconData,
  RoadCone as IconRoadCone,
  Setting as IconSetting,
  Experiment as IconExperiment,
  Server as IconServer,
} from '@icon-park/vue-next';
import { useHomePageSelectorStore } from '@/stores/homePageSelector';
import { iconToPageMap, sidebarLComponents, defaultPage, type IconType } from '@/views/home/pageMappings';

const store = useHomePageSelectorStore();

const handleIconClick = (iconType: IconType) => {
  const page = iconToPageMap[iconType];
  if (page) {
    store.setCurrentPage(page);
  }
};

const currentSidebarL = computed(() => {
  return sidebarLComponents[store.currentPage] || sidebarLComponents[defaultPage];
});
</script>
<template>
  <div class="container">
    <div class="header">
      <div class="header-item" @click="handleIconClick('IconAssemblyLine')" :class="{ 'active': store.currentPage === 'flow' }">
        <IconAssemblyLine />
      </div>
      <div class="header-item" @click="handleIconClick('IconExperiment')" :class="{ 'active': store.currentPage === 'experiment' }">
        <IconExperiment />
      </div>
      <div class="header-item" @click="handleIconClick('IconData')" :class="{ 'active': store.currentPage === 'dataset' }">
        <IconData />
      </div>
      <div class="header-item" @click="handleIconClick('IconRoadCone')" :class="{ 'active': store.currentPage === 'factors' }">
        <IconRoadCone />
      </div>
      <div class="header-item" @click="handleIconClick('IconServer')" :class="{ 'active': store.currentPage === 'runner' }">
        <IconServer />
      </div>
      <div class="header-item" @click="handleIconClick('IconSetting')" :class="{ 'active': store.currentPage === 'setting' }">
        <IconSetting />
      </div>
    </div>
    <div class="body">
      <component :is="currentSidebarL" />
    </div>
  </div>
  
</template>
<style scoped>

.container {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.header {
  display: flex;
  justify-content: center;
  align-items: center;
  /* border-bottom: 1px solid var(--color-layout-border); */
  margin-bottom: 4px;
}

.body {
  flex: 1;
}

.header-item {
  color: var(--color-button);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  border-radius: 5px;
  margin: 4px;
  padding: 6px;
  aspect-ratio: 1;
  min-width: 32px;
  min-height: 32px;
}

.header-item.active {
  background-color: var(--color-button-bg-active);
}

.header-item:hover {
  background-color: var(--color-button-bg-hover);
}
</style>
<script setup lang="ts">
import { Send as IconSend, Save as IconSave } from '@icon-park/vue-next';
import ResizableContainer from '@/components/ResizableContainer.vue';
import ToggleContainer from '@/components/ToggleContainer.vue';
</script>
<template>
  <div class="container">
    <div class="header">
    <div class="header-item" ><IconSave /></div>
    <div class="header-item" ><IconSend /></div>
  </div>
  <div class="body">
    <ResizableContainer direction="column">
      <ToggleContainer name="FILE">
        <div>ITEM 1</div>
        <div>ITEM 2</div>
      </ToggleContainer>
      <ToggleContainer name="JOBS">
        <div>ITEM 3</div>
        <div>ITEM 4</div>
      </ToggleContainer>
    </ResizableContainer>
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

.header-item:hover {
  background-color: var(--color-button-hover);
}
</style>
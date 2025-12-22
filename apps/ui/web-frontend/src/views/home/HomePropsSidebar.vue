<script setup lang="ts">
import ResizableContainer from '@/components/ResizableContainer.vue';
import ToggleContainer from '@/components/ToggleContainer.vue';
</script>
<template>
  <div class="home-props-sidebar">
    <ResizableContainer direction="column">
      <ToggleContainer name="NODE">
        <div>ITEM 1</div>
        <div>ITEM 2</div>
      </ToggleContainer>
      <ToggleContainer name="PROJECT">
        <div>ITEM 3</div>
        <div>ITEM 4</div>
      </ToggleContainer>
    </ResizableContainer>
  </div>
</template>
<style scoped>
.home-props-sidebar {
  display: flex;
  height: 100%;
  flex-direction: column;
}
</style>
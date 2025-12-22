<script setup lang="ts">
import { Down as IconDown, Right as IconRight } from '@icon-park/vue-next';
import { inject, onMounted, ref } from 'vue';

interface ToggleContainerProps {
    name: string;
    alwaysUpperCase?: boolean;
}

const props = withDefaults(defineProps<ToggleContainerProps>(), {
    alwaysUpperCase: true,
});

// 常量定义
const TRANSITION_DURATION = '0.2s';

// 状态管理
const isOpen = ref(true);
const registerToggleState = inject<((isOpen: boolean) => number) | undefined>('registerToggleState');
const updateToggleState = inject<((index: number, isOpen: boolean) => void) | undefined>('updateToggleState');
let currentIndex: number | null = null;

/**
 * 切换折叠/展开状态
 */
const toggle = () => {
    isOpen.value = !isOpen.value;
    if (updateToggleState && currentIndex !== null) {
        updateToggleState(currentIndex, isOpen.value);
    }
};

onMounted(() => {
    if (registerToggleState) {
        currentIndex = registerToggleState(isOpen.value);
    }
});
</script>
<template>
  <div class="toggle-container">
    <div class="toggle-container-header" @click="toggle">
      <div class="toggle-container-title">
        <component 
          :is="isOpen ? IconDown : IconRight" 
          class="toggle-container-icon"
          :class="{ 'icon-rotated': !isOpen }"
        />
        <span>{{ props.alwaysUpperCase ? props.name.toUpperCase() : props.name }}</span>
      </div>
    </div>
    <div 
      class="toggle-container-body"
      :class="{ 'toggle-container-body-collapsed': !isOpen }"
    >
      <slot />
    </div>
  </div>
</template>
<style scoped>
.toggle-container {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.toggle-container-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  flex-shrink: 0;
}

.toggle-container-title {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--color-text-secondary);
}

.toggle-container-title span {
  font-weight: bold;
  font-size: 0.8rem;
}

.toggle-container-icon {
  width: 14px;
  height: 14px;
  display: flex;
  align-items: center;
  stroke-width: 3;
  transition: transform 0.2s ease-out;
}

.toggle-container-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
  min-height: 0;
  overflow: auto;
  opacity: 1;
  max-height: 100%;
  transition: opacity 0.2s ease-out, max-height 0.2s ease-out, flex 0.2s ease-out;
}

.toggle-container-body-collapsed {
  opacity: 0;
  overflow: hidden;
  flex: 0;
  max-height: 0;
  min-height: 0;
}
</style>
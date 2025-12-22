<script setup lang="ts">
import { onBeforeUnmount, onMounted, provide, ref } from 'vue';
import type { MenuGroupId, MenuContext } from './menu.ts';

const activeGroupId = ref<MenuGroupId | null>(null);
const containerRef = ref<HTMLElement | null>(null);

const toggleGroup = (id: MenuGroupId) => {
  activeGroupId.value = activeGroupId.value === id ? null : id;
};

const closeAll = () => {
  activeGroupId.value = null;
};

provide<MenuContext>('menuContext', {
  activeGroupId,
  toggleGroup,
  closeAll,
});

// #region 处理点击非菜单区域时的窗口关闭操作
const onDocumentClick = (event: MouseEvent) => {
  const root = containerRef.value;
  if (!root) {
    return;
  }
  const target = event.target as Node | null;
  if (!target) {
    return;
  }
  if (!root.contains(target)) {
    closeAll();
  }
};

onMounted(() => {
  document.addEventListener('click', onDocumentClick);
});

onBeforeUnmount(() => {
  document.removeEventListener('click', onDocumentClick);
});
// #endregion
</script>
<template>
  <div ref="containerRef" class="menu container">
    <slot />
  </div>
</template>
<style scoped>
@import '../../assets/menu.css';
</style>
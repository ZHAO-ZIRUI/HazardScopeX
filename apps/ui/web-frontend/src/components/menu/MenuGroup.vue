<script setup lang="ts">
import { computed, inject } from 'vue';
import type { MenuGroupId, MenuContext } from './menu.ts';

interface MenuGroupProps {
  name: string;
}

const props = defineProps<MenuGroupProps>();
const id: MenuGroupId = Symbol('menu-group-id');
const menuContext = inject<MenuContext | undefined>('menuContext');

const isActive = computed(() => {
  if (!menuContext) {
    return false;
  }
  return menuContext.activeGroupId.value === id;
});

const handleToggle = () => {
  if (!menuContext) {
    return;
  }
  menuContext.toggleGroup(id);
};
</script>
<template>
  <div class="menu menu-group">
    <div class="menu menu-group menu-item" :class="{ 'active': isActive }" @click.stop="handleToggle">
      <p>{{ props.name }}</p>
    </div>
    <div v-if="isActive" class="menu-group-items">
      <slot />
    </div>
  </div>
</template>
<style scoped>
@import '../../assets/menu.css';

.menu-group.menu-item {
  cursor: pointer;
}

.menu-group-items {
  display: flex;
  flex-direction: column;
  position: absolute;
  top: 100%;
  left: 0;
}

.menu.menu-group {
  position: relative;
  align-items: center;
}
</style>
<script setup lang="ts">
interface MenuItemProps {
  name?: string;
}

const props = defineProps<MenuItemProps>();
</script>
<template>
  <div class="menu menu-item" :class="{ 'is-divider': !props.name }">
    <p v-if="props.name">{{ props.name }}</p>
  </div>
</template>
<style scoped>
@import '@/assets/menu.css';
</style>
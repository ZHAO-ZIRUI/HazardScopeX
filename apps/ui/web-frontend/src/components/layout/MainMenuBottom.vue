<script setup lang="ts">
import MenuContainer from '../menu/MenuContainer.vue';
import MenuItem from '../menu/MenuItem.vue';

</script>
<template>
  <MenuContainer class="bottom">
    ◆ DEVELOPING MODE
  </MenuContainer>
</template>

<style scoped>
@import '../../assets/menu.css';

.bottom{
  padding-left: 0px !important;
  background-color: brown;
  border-top: 1px solid var(--color-menu-border);
}
</style>
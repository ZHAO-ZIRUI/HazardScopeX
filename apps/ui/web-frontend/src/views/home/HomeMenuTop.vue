<script setup lang="ts">
import IconTextLogo from '@/components/icons/IconTextLogo.vue';
import MenuContainer from '@/components/menu/MenuContainer.vue';
import MenuGroup from '@/components/menu/MenuGroup.vue';
import MenuItem from '@/components/menu/MenuItem.vue';
</script>
<template>
  <MenuContainer class="top">
    <MenuGroup name="Home">
      <MenuItem name="Home Sub Option 1" />
      <MenuItem name="Home Sub Option 2" />
      <MenuItem />
      <MenuItem name="Home Sub Option 3" />
      <MenuItem name="Home Sub Option 4" />
    </MenuGroup>
    <MenuGroup name="About">
      <MenuItem name="About Sub Option 1" />
      <MenuItem name="About Sub Option 2" />
    </MenuGroup>
    <IconTextLogo class="logo"/>
  </MenuContainer>
</template>

<style scoped>
@import '@/assets/menu.css';

.logo {
  flex: 1;
}

.top {
  border-bottom: 1px solid var(--color-menu-border);
}

</style>
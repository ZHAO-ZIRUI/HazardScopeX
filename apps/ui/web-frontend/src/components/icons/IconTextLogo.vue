<script setup lang="ts"></script>
<template>
    <div class="logo">
      <p>
        <span class="logo-h">H</span>
        <span>AZARDSCOPE</span>
        <span class="logo-x">X</span>
      </p>
    </div>
</template>
<style scoped>
.logo {
  --color-logo-primary: rgb(255, 255, 255);
  --color-logo-secondary: rgb(255, 0, 0);
  
  background-color: var(--color-menu-background);
  display: flex;
  justify-content: end;
  align-items: center;
  color: var(--color-logo-white);
  font-size: 0.8rem;
  user-select: none;
  cursor: default;
}

.logo p {
  text-decoration: underline;
  text-decoration-color: var(--color-logo-primary);
  text-decoration-thickness: 1px;
  text-underline-offset: 2px;
}

.logo p span {
  font-weight: bold;
  font-style: italic;
}

.logo .logo-h {
  font-size: 1.0rem;
}

.logo .logo-x {
  color: var(--color-logo-secondary);
  font-size: 1.0rem;
  font-weight: 800;
}
</style>
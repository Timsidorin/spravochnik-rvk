<template>
  <div class="main-screen">
    <AppSidebar />
    <main class="content">
      <slot />
    </main>
  </div>
</template>

<script setup>
import AppSidebar from './AppSidebar.vue'
</script>
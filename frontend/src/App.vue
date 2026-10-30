<template>
  <RouterView v-if="isGuestRoute" />
  <AppLayout v-else>
    <RouterView />
  </AppLayout>
  <Toast />
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppLayout from './components/AppLayout.vue'
import Toast from './components/Toast.vue'

const route = useRoute()
const isGuestRoute = computed(() => route.meta.bare === true)
</script>
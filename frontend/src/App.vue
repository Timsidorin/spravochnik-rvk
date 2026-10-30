<template>
  <RouterView v-if="isGuestRoute" />
  <AppLayout v-else>
    <RouterView />
  </AppLayout>
  <Toast />
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { apiGet } from './api'
import AppLayout from './components/AppLayout.vue'
import Toast from './components/Toast.vue'
import { useAuthStore } from './stores/auth'

const route = useRoute()
const auth = useAuthStore()
const isGuestRoute = computed(() => route.meta.bare === true)

onMounted(async () => {
  if (!auth.isAuthenticated) return
  try {
    auth.setUser(await apiGet('/api/auth/me', { noRedirect: true }))
  } catch {}
})
</script>
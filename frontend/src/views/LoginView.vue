<template>
  <div class="login-screen">
    <form class="login-card" @submit.prevent="onSubmit">
      
      <h1>РВК Справочник</h1>
      <p class="subtitle">Телефонный справочник организации</p>

      <label>
        <span>Логин</span>
        <input
          v-model="username"
          type="text"
          autocomplete="username"
          required
          :disabled="loading"
        />
      </label>

      <label>
        <span>Пароль</span>
        <input
          v-model="password"
          type="password"
          autocomplete="current-password"
          required
          placeholder="Домен AD"
          :disabled="loading"
        />
      </label>

      <button type="submit" :disabled="loading">
        {{ loading ? 'Входим...' : 'Войти' }}
      </button>

      <div class="error-msg">{{ error }}</div>
    </form>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { apiPost } from '../api'
import { useAuthStore } from '../stores/auth'
import { useToast } from '../composables/useToast'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const toast = useToast()

const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

async function onSubmit() {
  loading.value = true
  error.value = ''
  try {
    const data = await apiPost(
      '/api/auth/login',
      { username: username.value.trim(), password: password.value },
      { skipAuth: true }
    )
    auth.setSession({
      username: data.username,
      is_admin: data.is_admin,
    })
    toast.success(`Добро пожаловать, ${data.username}`)

    const target = route.query.redirect
    // Только внутренние пути: защита от open redirect вида ?redirect=//evil.example
    const redirect =
      typeof target === 'string' && target.startsWith('/') && !target.startsWith('//') && !target.includes('\\')
        ? target
        : '/'
    router.replace(redirect)
  } catch (e) {
    error.value = e.message || 'Не удалось войти'
  } finally {
    loading.value = false
  }
}
</script>
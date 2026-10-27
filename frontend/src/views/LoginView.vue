<template>
  <div class="login-screen">
    <form class="login-card" @submit.prevent="onSubmit">
      <div class="logo-mark">
        <svg viewBox="0 0 40 40" width="40" height="40">
          <defs>
            <linearGradient id="login-g" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0" stop-color="#00d4ff"/>
              <stop offset="1" stop-color="#0088cc"/>
            </linearGradient>
          </defs>
          <rect width="40" height="40" rx="12" fill="url(#login-g)"/>
          <path
            d="M12 20 L18 26 L28 14"
            stroke="white"
            stroke-width="3"
            fill="none"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
      </div>

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
    auth.setSession(data.access_token, {
      username: data.username,
      is_admin: data.is_admin,
    })
    toast.success(`Добро пожаловать, ${data.username}`)

    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    router.replace(redirect)
  } catch (e) {
    error.value = e.message || 'Не удалось войти'
  } finally {
    loading.value = false
  }
}
</script>
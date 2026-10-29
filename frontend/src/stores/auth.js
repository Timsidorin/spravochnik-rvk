import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

// Сам токен хранится в httpOnly-cookie и недоступен JS;
// здесь только данные для отображения в интерфейсе.
const USER_KEY = 'phonebook.user'
localStorage.removeItem('phonebook.token')

export const useAuthStore = defineStore('auth', () => {
  const user = ref(JSON.parse(localStorage.getItem(USER_KEY) || 'null'))

  const isAuthenticated = computed(() => !!user.value)
  const isAdmin = computed(() => !!user.value?.is_admin)

  function setSession(userInfo) {
    user.value = userInfo
    localStorage.setItem(USER_KEY, JSON.stringify(userInfo))
  }

  function logout() {
    user.value = null
    localStorage.removeItem(USER_KEY)
  }

  return { user, isAuthenticated, isAdmin, setSession, logout }
})

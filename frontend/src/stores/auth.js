import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

const TOKEN_KEY = 'phonebook.token'
const USER_KEY = 'phonebook.user'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem(TOKEN_KEY) || '')
  const user = ref(JSON.parse(localStorage.getItem(USER_KEY) || 'null'))

  const isAuthenticated = computed(() => !!token.value)
  const isAdmin = computed(() => !!user.value?.is_admin)
  const isSuperadmin = computed(() => !!user.value?.is_superadmin)

  function setUser(info) {
    user.value = {
      username: info.username,
      is_admin: info.is_admin,
      is_superadmin: info.is_superadmin,
    }
    localStorage.setItem(USER_KEY, JSON.stringify(user.value))
  }

  function setSession(accessToken, info) {
    token.value = accessToken
    localStorage.setItem(TOKEN_KEY, accessToken)
    setUser(info)
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  }

  return { token, user, isAuthenticated, isAdmin, isSuperadmin, setUser, setSession, logout }
})

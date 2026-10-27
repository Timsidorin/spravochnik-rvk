<template>
  <aside class="sidebar">
    <div class="brand">
      <div class="brand-icon">
        <svg viewBox="0 0 40 40" width="28" height="28">
          <defs>
            <linearGradient id="brand-g" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0" stop-color="#00d4ff"/>
              <stop offset="1" stop-color="#0088cc"/>
            </linearGradient>
          </defs>
          <rect width="40" height="40" rx="12" fill="url(#brand-g)"/>
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
      <div>
        <div class="brand-title">РВК Справочник</div>
        <div class="brand-sub">Телефонный справочник</div>
      </div>
    </div>

    <div class="search-wrap">
      <svg viewBox="0 0 24 24" width="16" height="16" class="search-icon">
        <path
          d="M11 4a7 7 0 1 0 4.9 12L21 21M11 4a7 7 0 1 1 0 14 7 7 0 0 1 0-14z"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
        />
      </svg>
      <input
        type="search"
        v-model="query"
        placeholder="Поиск по имени, логину, телефону..."
        @input="onSearchInput"
      />
    </div>

    <DepartmentTree />

    <div class="sidebar-footer">
      <div class="user-block">
        <div class="user-avatar">{{ userInitials }}</div>
        <div class="user-info">
          <div class="user-name">{{ auth.user?.username || '—' }}</div>
          <div class="user-role">{{ auth.isAdmin ? 'Администратор' : 'Сотрудник' }}</div>
        </div>
      </div>

      <button
        v-if="auth.isAdmin"
        class="import-btn"
        :class="{ loading: importing }"
        :disabled="importing"
        title="Импортировать из AD"
        @click="runImport"
      >
        ⟳
      </button>

      <button class="logout-btn" title="Выйти" @click="onLogout">⏻</button>
    </div>
  </aside>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { apiPost } from '../api'
import { useToast } from '../composables/useToast'
import DepartmentTree from './DepartmentTree.vue'

const auth = useAuthStore()
const router = useRouter()
const toast = useToast()

const query = ref('')
const importing = ref(false)

const userInitials = computed(() => {
  const n = auth.user?.username || '?'
  return n.slice(0, 2).toUpperCase()
})

let debounceTimer = null
function onSearchInput() {
  clearTimeout(debounceTimer)
  const q = query.value.trim()
  if (!q) {
    if (router.currentRoute.value.name === 'search') {
      router.push({ name: 'welcome' })
    }
    return
  }
  debounceTimer = setTimeout(() => {
    router.push({ name: 'search', query: { q } })
  }, 250)
}

async function runImport() {
  if (!confirm('Запустить синхронизацию с AD? Текущие данные будут перезаписаны.')) {
    return
  }
  importing.value = true
  try {
    const res = await apiPost('/api/admin/import')
    toast.success(`Импорт завершён: ${res.departments} отделов, ${res.employees} сотрудников`)
    window.dispatchEvent(new Event('tree:reload'))
  } catch (e) {
    toast.error(e.message)
  } finally {
    importing.value = false
  }
}

function onLogout() {
  auth.logout()
  router.push({ name: 'login' })
}
</script>
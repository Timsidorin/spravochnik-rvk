<template>
  <div class="search-results">
    <form v-if="!embedded" class="results-search" @submit.prevent="submitSearch">
      <input
        v-model="draft"
        type="search"
        placeholder="Фамилия, отдел или номер"
        aria-label="Поиск сотрудников и отделов"
        autocomplete="off"
      />
      <button type="submit">Найти</button>
    </form>
    <div v-if="loading" class="empty-content">Поиск...</div>

    <div v-else-if="!hasResults" class="search-empty">
      Ничего не найдено по запросу «{{ q }}»
    </div>

    <template v-else>
      <template v-if="result.departments.length">
        <h2>Отделы</h2>
        <div class="employee-grid">
          <div
            v-for="d in result.departments"
            :key="d.id"
            class="employee-card"
            @click="openDept(d.id)"
          >
            <div class="employee-card-inner">
              <div
                class="emp-avatar"
                style="background: linear-gradient(135deg, #00d4ff, #0088cc)"
              >
                🏢
              </div>
              <div class="emp-body">
                <div class="emp-name">{{ d.name }}</div>
                <div class="emp-title">{{ d.employees_count }} сотрудников</div>
              </div>
            </div>
          </div>
        </div>
      </template>

      <template v-if="result.employees.length">
        <h2>Сотрудники</h2>
        <div class="employee-grid">
          <EmployeeCard
            v-for="e in result.employees"
            :key="e.login"
            :emp="e"
          />
        </div>
      </template>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { apiGet } from '../api'
import { useToast } from '../composables/useToast'
import EmployeeCard from '../components/EmployeeCard.vue'

const route = useRoute()
const router = useRouter()
const toast = useToast()

const result = ref({ employees: [], departments: [] })
const loading = ref(false)

const props = defineProps({
  embedded: Boolean,
  searchQuery: { type: String, default: '' },
})
const q = computed(() => props.embedded ? props.searchQuery.trim() : String(route.query.q || '').trim())
const draft = ref(q.value)
watch(q, (value) => { draft.value = value })

function submitSearch() {
  router.replace({ name: 'search', query: { q: draft.value.trim() } })
}

const hasResults = computed(
  () => result.value.employees.length > 0 || result.value.departments.length > 0
)

let requestId = 0
async function search() {
  const id = ++requestId
  if (!q.value) {
    loading.value = false
    result.value = { employees: [], departments: [] }
    return
  }
  loading.value = true
  try {
    const data = await apiGet(
      `/api/departments/search?q=${encodeURIComponent(q.value)}`
    )
    if (id === requestId) result.value = data
  } catch (e) {
    if (id !== requestId) return
    toast.error(e.message)
    result.value = { employees: [], departments: [] }
  } finally {
    if (id === requestId) loading.value = false
  }
}

watch(q, search, { immediate: true })

function openDept(id) {
  router.push({ name: 'department', params: { id } })
}
</script>

<style scoped>
.results-search {
  display: flex;
  gap: 10px;
  margin: 0 auto 32px;
  max-width: 720px;
}
.results-search input {
  flex: 1;
  min-width: 0;
  padding: 14px 18px;
  font: inherit;
  font-size: 17px;
  color: var(--text-primary);
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--r-md);
}
.results-search button {
  padding: 12px 18px;
  background: var(--accent);
  color: var(--text-on-accent);
  border-radius: var(--r-md);
}
</style>
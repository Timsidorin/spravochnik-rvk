<template>
  <div class="search-results">
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

const q = computed(() => String(route.query.q || '').trim())

const hasResults = computed(
  () => result.value.employees.length > 0 || result.value.departments.length > 0
)

async function search() {
  if (!q.value) {
    result.value = { employees: [], departments: [] }
    return
  }
  loading.value = true
  try {
    result.value = await apiGet(
      `/api/departments/search?q=${encodeURIComponent(q.value)}`
    )
  } catch (e) {
    toast.error(e.message)
    result.value = { employees: [], departments: [] }
  } finally {
    loading.value = false
  }
}

watch(q, search, { immediate: true })

function openDept(id) {
  router.push({ name: 'department', params: { id } })
}
</script>
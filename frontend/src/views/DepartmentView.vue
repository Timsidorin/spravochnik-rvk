<template>
  <div v-if="loading" class="empty-content">Загрузка...</div>

  <div v-else-if="error" class="empty-content">
    <div class="empty-icon">⚠️</div>
    <h2>Не удалось загрузить отдел</h2>
    <p>{{ error }}</p>
  </div>

  <div v-else-if="dept" class="dept-view">
    <header class="dept-header">
      <h1>{{ dept.name }}</h1>
      <div class="dept-meta">{{ total }} сотрудников</div>
    </header>

    <section v-if="dept.head" class="head-section">
      <div class="section-label">Начальник отдела</div>
      <EmployeeCard :emp="dept.head" head />
    </section>

    <section v-if="dept.employees.length" class="employees-section">
      <div class="section-label">Сотрудники ({{ dept.employees.length }})</div>
      <div class="employee-grid">
        <EmployeeCard v-for="e in dept.employees" :key="e.login" :emp="e" />
      </div>
    </section>

    <div v-else class="empty-state">В отделе нет сотрудников</div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { apiGet } from '../api'
import { useToast } from '../composables/useToast'
import EmployeeCard from '../components/EmployeeCard.vue'

const props = defineProps({
  id: { type: [String, Number], required: true },
})

const toast = useToast()
const dept = ref(null)
const loading = ref(false)
const error = ref('')

const total = computed(
  () => (dept.value?.employees?.length || 0) + (dept.value?.head ? 1 : 0)
)

async function load() {
  loading.value = true
  error.value = ''
  dept.value = null
  try {
    dept.value = await apiGet(`/api/departments/${props.id}`)
  } catch (e) {
    error.value = e.message
    toast.error(e.message)
  } finally {
    loading.value = false
  }
}

watch(() => props.id, load, { immediate: true })
</script>
<template>
  <div v-if="loading" class="empty-content">Загрузка...</div>

  <div v-else-if="error" class="empty-content">
    <div class="empty-icon">⚠️</div>
    <h2>Не удалось загрузить сотрудника</h2>
    <p>{{ error }}</p>
  </div>

  <div v-else-if="emp" class="emp-detail">
    <div class="emp-detail-card">
      <div class="emp-detail-header">
        <div class="emp-detail-avatar" :style="avatarStyle">{{ initials }}</div>
        <div style="flex: 1; min-width: 0">
          <div class="emp-detail-name">{{ emp.full_name }}</div>
          <div class="emp-detail-title">{{ emp.title || '—' }}</div>
        </div>
      </div>

      <div class="detail-rows">
        <div class="detail-row">
          <div class="detail-label">Логин</div>
          <div class="detail-value">{{ emp.login }}</div>
        </div>

        <div v-if="deptInfo?.department_id" class="detail-row">
          <div class="detail-label">Отдел</div>
          <div class="detail-value">
            <a class="dept-link" @click="goToDept">{{ deptInfo.name }}</a>
          </div>
        </div>

        <div v-if="emp.email" class="detail-row">
          <div class="detail-label">Email</div>
          <div class="detail-value">
            <a :href="`mailto:${emp.email}`">{{ emp.email }}</a>
          </div>
        </div>

        <div v-for="p in phoneRows" :key="p.label" class="detail-row">
          <div class="detail-label">{{ p.label }}</div>
          <div class="detail-value">
            <a :href="`tel:${p.tel}`">{{ p.value }}</a>
          </div>
        </div>

        <div v-if="emp.office" class="detail-row">
          <div class="detail-label">Офис</div>
          <div class="detail-value">{{ emp.office }}</div>
        </div>
        <div v-if="emp.city" class="detail-row">
          <div class="detail-label">Город</div>
          <div class="detail-value">{{ emp.city }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { apiGet } from '../api'
import { useToast } from '../composables/useToast'

const props = defineProps({
  login: { type: String, required: true },
})

const router = useRouter()
const toast = useToast()

const emp = ref(null)
const deptInfo = ref(null)
const loading = ref(false)
const error = ref('')

const PALETTE = [
  ['#00d4ff', '#0088cc'],
  ['#8b5cf6', '#6d28d9'],
  ['#10b981', '#047857'],
  ['#f59e0b', '#b45309'],
  ['#ef4444', '#b91c1c'],
  ['#ec4899', '#be185d'],
  ['#06b6d4', '#0e7490'],
  ['#84cc16', '#4d7c0f'],
]

function colorFor(name) {
  let h = 0
  for (const c of name || '') h = (h * 31 + c.charCodeAt(0)) >>> 0
  return PALETTE[h % PALETTE.length]
}

const avatarStyle = computed(() => {
  const [c1, c2] = colorFor(emp.value?.full_name)
  return { background: `linear-gradient(135deg, ${c1}, ${c2})` }
})

const initials = computed(() => {
  const parts = (emp.value?.full_name || '').trim().split(/\s+/).filter(Boolean)
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase()
  return (emp.value?.full_name || '?').slice(0, 2).toUpperCase()
})

function formatPhone(raw) {
  if (!raw) return ''
  const s = String(raw).replace(/^tel:/i, '').trim()
  const m = s.match(/^(.*?);ext=(.*)$/i)
  return m ? `${m[1]} (доб. ${m[2]})` : s
}

const phoneRows = computed(() => {
  if (!emp.value) return []
  const rows = []
  const add = (label, value) => {
    if (!value) return
    rows.push({ label, value, tel: value.replace(/[^\d+]/g, '') })
  }
  add('Рабочий', emp.value.phone)
  add('Мобильный', emp.value.mobile)
  add('IP-телефон', emp.value.ip_phone)
  add('SIP / Teams', formatPhone(emp.value.sip_line))
  return rows
})

async function load() {
  loading.value = true
  error.value = ''
  emp.value = null
  deptInfo.value = null
  try {
    const [e, d] = await Promise.all([
      apiGet(`/api/employees/${encodeURIComponent(props.login)}`),
      apiGet(`/api/employees/${encodeURIComponent(props.login)}/department`),
    ])
    emp.value = e
    deptInfo.value = d
  } catch (e) {
    error.value = e.message
    toast.error(e.message)
  } finally {
    loading.value = false
  }
}

watch(() => props.login, load, { immediate: true })

function goToDept() {
  if (deptInfo.value?.department_id) {
    router.push({ name: 'department', params: { id: deptInfo.value.department_id } })
  }
}
</script>
<template>
  <div
    class="employee-card"
    @click="onClick"
    tabindex="0"
    @keydown.enter.prevent="onClick"
  >
    <div class="employee-card-inner">
      <div class="emp-avatar" :style="avatarStyle">{{ initials }}</div>

      <div class="emp-body">
        <div class="emp-name-row">
          <span class="emp-name">{{ emp.full_name }}</span>
          <span v-if="head" class="badge-head">Руководитель</span>
        </div>

        <div v-if="emp.title" class="emp-title">
          <span class="emp-title-text">{{ emp.title }}</span>
        </div>
        <div v-else class="emp-title emp-title-empty">
          Должность не указана
        </div>

        <div class="emp-phones">
          <span v-if="auth.isAdmin" class="emp-phone emp-phone-edit" @click.stop>
            <input
              v-model="phoneDraft"
              class="emp-phone-input"
              :placeholder="emp.phone ? '' : 'номер...'"
              :disabled="saving"
              @click.stop
              @keydown.enter.prevent="$event.target.blur()"
              @keydown.stop
              @blur="savePhone"
            />
          </span>
          <a
            v-for="p in phones"
            :key="p.label"
            class="emp-phone"
            :href="`tel:${p.tel}`"
            @click.stop
          >
            {{ p.label }}
          </a>
          <span v-if="!phones.length && !auth.isAdmin" class="emp-phone emp-phone-empty">нет номера</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { apiPut } from '../api'
import { useToast } from '../composables/useToast'

const props = defineProps({
  emp: { type: Object, required: true },
  head: { type: Boolean, default: false },
})

const router = useRouter()
const auth = useAuthStore()
const toast = useToast()

const phoneDraft = ref(props.emp.phone || '')
const saving = ref(false)
watch(() => props.emp.phone, (v) => (phoneDraft.value = v || ''))

async function savePhone() {
  const value = phoneDraft.value.trim()
  const original = props.emp.phone || ''
  if (value === original || saving.value) return
  saving.value = true
  try {
    const updated = await apiPut(
      `/api/admin/employees/${encodeURIComponent(props.emp.login)}/phones`,
      { phone: value }
    )
    Object.assign(props.emp, updated)
    phoneDraft.value = updated.phone || ''
  } catch (e) {
    toast.error(e.message)
    phoneDraft.value = original
  } finally {
    saving.value = false
  }
}

const PALETTE = [
  { bg: '#4c6ef5', fg: '#ffffff' },
  { bg: '#0ca678', fg: '#ffffff' },
  { bg: '#e8590c', fg: '#ffffff' },
  { bg: '#9c36b5', fg: '#ffffff' },
  { bg: '#1864ab', fg: '#ffffff' },
  { bg: '#2b8a3e', fg: '#ffffff' },
  { bg: '#c92a2a', fg: '#ffffff' },
  { bg: '#5f3dc4', fg: '#ffffff' },
  { bg: '#0b7285', fg: '#ffffff' },
  { bg: '#862e9c', fg: '#ffffff' },
]

function colorFor(name) {
  let h = 0
  for (const c of name || '') h = (h * 31 + c.charCodeAt(0)) >>> 0
  return PALETTE[h % PALETTE.length]
}

const avatarStyle = computed(() => {
  const c = colorFor(props.emp.full_name)
  return { background: c.bg, color: c.fg }
})

const initials = computed(() => {
  const parts = (props.emp.full_name || '').trim().split(/\s+/).filter(Boolean)
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase()
  return (props.emp.full_name || '?').slice(0, 2).toUpperCase()
})

function formatPhone(raw) {
  if (!raw) return ''
  const s = String(raw).replace(/^tel:/i, '').trim()
  const m = s.match(/^(.*?);ext=(.*)$/i)
  return m ? `${m[1]} доб.${m[2]}` : s
}

const phones = computed(() => {
  const e = props.emp
  const list = []
  // Для админа рабочий номер показывается инлайн-инпутом, чип не дублируем
  if (e.phone && !auth.isAdmin) list.push({ label: e.phone, tel: e.phone.replace(/[^\d+]/g, '') })
  if (e.mobile) list.push({ label: e.mobile, tel: e.mobile.replace(/[^\d+]/g, '') })
  if (e.ip_phone) list.push({ label: e.ip_phone, tel: e.ip_phone.replace(/[^\d+]/g, '') })
  if (e.other_phone) list.push({ label: e.other_phone, tel: e.other_phone.replace(/[^\d+]/g, '') })
  if (e.sip_line) {
    const v = formatPhone(e.sip_line)
    list.push({ label: v, tel: v.replace(/[^\d+]/g, '') })
  }
  return list.slice(0, 2)
})

function onClick() {
  router.push({ name: 'employee', params: { login: props.emp.login } })
}
</script>

<style scoped>
/* ============================================
   CARD
   ============================================ */
.employee-card {
  background: var(--bg-surface, #ffffff);
  border: 1px solid var(--border, #e7e5e4);
  border-radius: 12px;
  cursor: pointer;
  transition: border-color 150ms ease, box-shadow 150ms ease, transform 150ms ease;
  outline: none;
  position: relative;
  overflow: hidden;
}

.employee-card:hover {
  border-color: var(--border-strong, #d6d3d1);
  box-shadow: 0 4px 12px rgba(28, 25, 23, 0.06), 0 1px 3px rgba(28, 25, 23, 0.04);
  transform: translateY(-1px);
}

.employee-card:active {
  transform: translateY(0);
}

.employee-card:focus-visible {
  border-color: var(--text-primary, #1c1917);
  box-shadow: 0 0 0 3px rgba(28, 25, 23, 0.08);
}

/* ============================================
   LAYOUT
   ============================================ */
.employee-card-inner {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 16px 18px;
}

/* ============================================
   AVATAR
   ============================================ */
.emp-avatar {
  width: 42px;
  height: 42px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 13px;
  flex-shrink: 0;
  letter-spacing: 0.02em;
  box-shadow: 0 2px 4px rgba(28, 25, 23, 0.08);
}

/* ============================================
   BODY
   ============================================ */
.emp-body {
  flex: 1;
  min-width: 0;
}

.emp-name-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.emp-name {
  font-size: 14.5px;
  font-weight: 600;
  color: var(--text-primary, #1c1917);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  letter-spacing: -0.01em;
  line-height: 1.3;
}

/* Head badge — нейтральный, не «награда» */
.badge-head {
  display: inline-flex;
  align-items: center;
  font-size: 10px;
  font-weight: 600;
  color: var(--text-secondary, #57534e);
  background: var(--bg-subtle, #f5f5f4);
  border: 1px solid var(--border, #e7e5e4);
  padding: 2px 7px;
  border-radius: 4px;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  flex-shrink: 0;
  line-height: 1.4;
}

/* ============================================
   TITLE
   ============================================ */
.emp-title {
  display: flex;
  margin-bottom: 10px;
}

.emp-title-text {
  display: inline-block;
  font-size: 12px;
  font-weight: 500;
  color: #1e40af;
  background: #eff6ff;
  padding: 3px 9px;
  border-radius: 5px;
  line-height: 1.4;
  letter-spacing: -0.005em;
  max-width: 100%;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: background 150ms ease;
}

.employee-card:hover .emp-title-text {
  background: #dbeafe;
}

.emp-title-empty {
  font-size: 12px;
  color: var(--text-tertiary, #a8a29e);
  font-style: italic;
  padding: 3px 0;
}

/* ============================================
   PHONES
   ============================================ */
.emp-phones {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.emp-phone {
  display: inline-flex;
  align-items: center;
  font-size: 18px;
  line-height: 1.2;
  font-variant-numeric: tabular-nums;
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  color: #1d4ed8;
  text-decoration: none;
  padding: 0;
  font-weight: 800;
  letter-spacing: 0.02em;
  white-space: nowrap;
}

.emp-phone-empty {
  color: var(--text-tertiary, #a8a29e);
  font-family: inherit;
  font-weight: 400;
  font-size: 12px;
  font-style: italic;
  cursor: inherit;
}

.emp-phone-edit {
  cursor: text;
}

.emp-phone-edit:hover {
  text-decoration: none;
}

.emp-phone-input {
  appearance: none;
  -webkit-appearance: none;
  border: none;
  border-radius: 0;
  background: none;
  box-shadow: none;
  outline: none;
  font: inherit;
  font-variant-numeric: tabular-nums;
  color: inherit;
  caret-color: #1d4ed8;
  width: 140px;
  padding: 0;
  margin: 0;
  cursor: text;
}

.emp-phone-input:hover,
.emp-phone-input:focus,
.emp-phone-input:disabled {
  background: none;
  border: none;
  box-shadow: none;
  outline: none;
}

.emp-phone-input:-webkit-autofill {
  -webkit-box-shadow: 0 0 0 100px var(--bg-surface, #ffffff) inset;
  -webkit-text-fill-color: #1d4ed8;
}

.emp-phone-input::placeholder {
  color: var(--text-tertiary, #a8a29e);
  font-family: inherit;
  font-size: 13px;
  font-style: italic;
  font-weight: 400;
  letter-spacing: 0;
}

.emp-phone-input:disabled {
  opacity: 0.5;
}

.emp-phone:hover {
  color: #1e3a8a;
  text-decoration: underline;
  text-underline-offset: 3px;
}
</style>
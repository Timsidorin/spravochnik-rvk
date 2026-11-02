<template>
  <div
    class="employee-card"
    @click="onClick"
    tabindex="0"
    @keydown.enter.prevent="onClick"
  >
    <div class="employee-card-inner">
      <div
        class="emp-avatar"
        :class="{ 'emp-avatar-editable': auth.isAdmin }"
        :style="avatarStyle"
        :title="auth.isAdmin ? 'Сменить фото' : ''"
        @click.stop="auth.isAdmin && fileInput?.click()"
      >
        <img v-if="!photoFailed" :src="photoSrc" alt="" @error="photoFailed = true" />
        <span v-else>{{ avatarText }}</span>
        <input
          v-if="auth.isAdmin"
          ref="fileInput"
          type="file"
          accept="image/*"
          hidden
          @click.stop
          @change="uploadPhoto"
        />
      </div>

      <div class="emp-body">
        <div class="emp-name-row">
          <span class="emp-name">{{ emp.full_name }}</span>
          <span v-if="head" class="badge-head">Руководитель</span>
        </div>
        <a v-if="emp.email" class="emp-email" :href="`mailto:${emp.email}`" @click.stop>
          {{ emp.email }}
        </a>

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
            :key="p.key"
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
import { apiPut, apiUpload } from '../api'
import { useToast } from '../composables/useToast'
import { useAuthStore } from '../stores/auth'
import { formatPhone, initials, pickByName, photoUrl, toTel } from '../utils'

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

const AVATAR_COLORS = [
  '#4c6ef5', '#0ca678', '#e8590c', '#9c36b5', '#1864ab',
  '#2b8a3e', '#c92a2a', '#5f3dc4', '#0b7285', '#862e9c',
]
const avatarStyle = computed(() => ({
  background: pickByName(props.emp.full_name, AVATAR_COLORS),
  color: '#ffffff',
}))
const avatarText = computed(() => initials(props.emp.full_name))
const photoFailed = ref(false)
const photoVersion = ref(0)
const fileInput = ref(null)
const uploading = ref(false)
const photoSrc = computed(() => photoUrl(props.emp.login, photoVersion.value))
watch(() => props.emp.login, () => (photoFailed.value = false))

async function uploadPhoto(e) {
  const file = e.target.files?.[0]
  e.target.value = ''
  if (!file || uploading.value) return
  uploading.value = true
  try {
    Object.assign(
      props.emp,
      await apiUpload(
        `/api/admin/employees/${encodeURIComponent(props.emp.login)}/photo`, file
      )
    )
    photoFailed.value = false
    photoVersion.value = Date.now()
    toast.success('Фото сохранено в AD')
  } catch (err) {
    toast.error(err.message)
  } finally {
    uploading.value = false
  }
}

const DISPLAY_ORDER = ['phone', 'mobile', 'ip_phone', 'other_phone', 'sip_line']

const phones = computed(() =>
  DISPLAY_ORDER
    .filter((key) => props.emp[key] && !(key === 'phone' && auth.isAdmin))
    .map((key) => {
      const label = formatPhone(props.emp[key])
      return { key, label, tel: toTel(label) }
    })
    .slice(0, 2)
)

function onClick() {
  router.push({ name: 'employee', params: { login: props.emp.login } })
}
</script>

<style scoped>
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

.employee-card-inner {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 16px 18px;
}

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
  overflow: hidden;
}

.emp-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.emp-avatar-editable {
  cursor: pointer;
  position: relative;
}

.emp-avatar-editable::after {
  content: '';
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.25)
    url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='14' height='14' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4'/%3E%3Cpolyline points='17 8 12 3 7 8'/%3E%3Cline x1='12' y1='3' x2='12' y2='15'/%3E%3C/svg%3E")
    center / 40% no-repeat;
  opacity: 0;
  transition: opacity 120ms ease;
}

.emp-avatar-editable:hover::after {
  opacity: 1;
}

.emp-body {
  flex: 1;
  min-width: 0;
}

.emp-name-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 2px;
}

.emp-email {
  display: block;
  margin-bottom: 6px;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text-tertiary, #a8a29e);
  text-decoration: none;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.emp-email:hover {
  color: var(--text-secondary, #57534e);
  text-decoration: underline;
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
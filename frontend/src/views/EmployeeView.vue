<template>
  <div v-if="loading" class="emp-detail">
    <div class="emp-detail-card">
      <div class="emp-detail-header">
        <div class="skeleton-avatar shimmer"></div>
        <div class="skeleton-header-text">
          <div class="skeleton-line skeleton-name shimmer"></div>
          <div class="skeleton-line skeleton-title shimmer"></div>
        </div>
      </div>
      <div class="skeleton-rows">
        <div v-for="i in 5" :key="i" class="skeleton-row">
          <div class="skeleton-label shimmer"></div>
          <div class="skeleton-value shimmer" :style="{ width: (40 + i * 8) + '%' }"></div>
        </div>
      </div>
    </div>
  </div>

  <div v-else-if="error" class="emp-detail">
    <div class="emp-detail-card emp-detail-error">
      <div class="error-icon">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8" x2="12" y2="12"/>
          <line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
      </div>
      <h2 class="error-title">Не удалось загрузить</h2>
      <p class="error-text">{{ error }}</p>
      <button class="error-retry" @click="load">Попробовать снова</button>
    </div>
  </div>

  <div v-else-if="emp" class="emp-detail">
    <button v-if="deptInfo?.department_id" class="back-link" @click="goToDept">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
           stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M19 12H5M12 19l-7-7 7-7"/>
      </svg>
      {{ deptInfo.name }}
    </button>

    <div class="emp-detail-card">
      <div class="emp-detail-header">
        <div class="emp-detail-avatar" :style="{ background: avatarColor }">
          <img v-if="!photoFailed" :src="photoSrc" alt="" @error="photoFailed = true" />
          <span v-else>{{ avatarText }}</span>
        </div>
        <div v-if="auth.isAdmin" class="photo-actions">
          <button
            type="button"
            class="photo-action-btn"
            title="Загрузить фото в AD"
            :disabled="photoBusy"
            @click="fileInput?.click()"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
          </button>
          <button
            v-if="!photoFailed"
            type="button"
            class="photo-action-btn"
            title="Удалить фото"
            :disabled="photoBusy"
            @click="removePhoto"
          >
            ×
          </button>
          <input ref="fileInput" type="file" accept="image/*" hidden @change="uploadPhoto" />
        </div>
        <div class="emp-detail-info">
          <h1 class="emp-detail-name">{{ emp.full_name }}</h1>
          <a v-if="emp.email" class="emp-detail-email" :href="`mailto:${emp.email}`">{{ emp.email }}</a>
          <p class="emp-detail-title">{{ emp.title || 'Должность не указана' }}</p>
          <span class="emp-detail-login">@{{ emp.login }}</span>
        </div>
      </div>

      <div class="detail-section">
        <div class="section-heading">Контакты</div>

        <div v-if="emp.email" class="detail-row">
          <div class="detail-icon">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <rect x="2" y="4" width="20" height="16" rx="2"/>
              <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>
            </svg>
          </div>
          <div class="detail-label">Email</div>
          <div class="detail-value">
            <a :href="`mailto:${emp.email}`" class="detail-link">{{ emp.email }}</a>
          </div>
          <button class="copy-btn" title="Скопировать" @click="copyToClipboard(emp.email)">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect x="9" y="9" width="13" height="13" rx="2"/>
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
            </svg>
          </button>
        </div>

        <template v-if="auth.isAdmin">
          <div v-for="f in PHONE_FIELDS" :key="f.key" class="detail-row">
            <div class="detail-icon">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                   stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07
                         19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2
                         2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L8.09
                         9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339
                         1.85.573 2.81.7A2 2 0 0 1 22 16.92z"/>
              </svg>
            </div>
            <div class="detail-label">{{ f.label }}</div>
            <div class="detail-value">
              <input
                v-model="editForm[f.key]"
                class="phone-input"
                placeholder="—"
                :disabled="savingField === f.key"
                @blur="saveField(f.key)"
                @keydown.enter.prevent="$event.target.blur()"
              />
            </div>
            <span class="save-indicator" :class="{ visible: savedField === f.key }">✓</span>
          </div>
        </template>

        <template v-else>
          <div v-for="p in phoneRows" :key="p.key" class="detail-row">
            <div class="detail-icon">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                   stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07
                         19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2
                         2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L8.09
                         9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339
                         1.85.573 2.81.7A2 2 0 0 1 22 16.92z"/>
              </svg>
            </div>
            <div class="detail-label">{{ p.label }}</div>
            <div class="detail-value">
              <a v-if="p.value" :href="`tel:${p.tel}`" class="detail-link detail-phone">{{ p.value }}</a>
              <span v-else class="detail-empty-value">не указан</span>
            </div>
            <button v-if="p.value" class="copy-btn" title="Скопировать" @click="copyToClipboard(p.tel)">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                   stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="9" y="9" width="13" height="13" rx="2"/>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
              </svg>
            </button>
          </div>
        </template>
      </div>

      <div v-if="emp.office || emp.city || deptInfo?.department_id" class="detail-section">
        <div class="section-heading">Рабочее место</div>

        <div v-if="deptInfo?.department_id" class="detail-row">
          <div class="detail-icon">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
            </svg>
          </div>
          <div class="detail-label">Отдел</div>
          <div class="detail-value">
            <a class="detail-link dept-link" @click="goToDept">{{ deptInfo.name }}</a>
          </div>
        </div>

        <div v-if="emp.office" class="detail-row">
          <div class="detail-icon">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <rect x="4" y="2" width="16" height="20" rx="2"/>
              <path d="M9 22v-4h6v4M8 6h.01M16 6h.01M12 6h.01M8 10h.01M16 10h.01M12 10h.01M8 14h.01M16 14h.01M12 14h.01"/>
            </svg>
          </div>
          <div class="detail-label">Офис</div>
          <div class="detail-value">{{ emp.office }}</div>
        </div>

        <div v-if="emp.city" class="detail-row">
          <div class="detail-icon">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
              <circle cx="12" cy="10" r="3"/>
            </svg>
          </div>
          <div class="detail-label">Город</div>
          <div class="detail-value">{{ emp.city }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { apiDelete, apiGet, apiPut, apiUpload } from '../api'
import { useToast } from '../composables/useToast'
import { useRecent } from '../composables/useRecent'
import { useAuthStore } from '../stores/auth'
import { PHONE_FIELDS, formatPhone, initials, pickByName, photoUrl, toTel } from '../utils'

const props = defineProps({
  login: { type: String, required: true },
})

const router = useRouter()
const toast = useToast()
const auth = useAuthStore()
const { remember } = useRecent()

const emp = ref(null)
const deptInfo = ref(null)
const loading = ref(false)
const error = ref('')

const editForm = reactive({})
const savingField = ref('')
const savedField = ref('')

function fillEditForm() {
  for (const f of PHONE_FIELDS) editForm[f.key] = emp.value?.[f.key] || ''
}

let savedTimer = null
async function saveField(key) {
  const value = (editForm[key] || '').trim()
  const original = emp.value?.[key] || ''
  if (value === original || savingField.value) return
  savingField.value = key
  try {
    const updated = await apiPut(
      `/api/admin/employees/${encodeURIComponent(props.login)}/phones`,
      { [key]: value }
    )
    emp.value = updated
    fillEditForm()
    remember(updated)
    savedField.value = key
    clearTimeout(savedTimer)
    savedTimer = setTimeout(() => (savedField.value = ''), 1500)
  } catch (e) {
    toast.error(e.message)
    editForm[key] = original
  } finally {
    savingField.value = ''
  }
}

const AVATAR_COLORS = [
  '#44403c', '#57534e', '#78716c', '#292524',
  '#1c1917', '#6b7280', '#4b5563', '#374151',
]
const avatarColor = computed(() => pickByName(emp.value?.full_name, AVATAR_COLORS))
const avatarText = computed(() => initials(emp.value?.full_name))

const fileInput = ref(null)
const photoFailed = ref(false)
const photoBusy = ref(false)
const photoVersion = ref(0)
const photoSrc = computed(() => photoUrl(props.login, photoVersion.value))

async function uploadPhoto(e) {
  const file = e.target.files?.[0]
  e.target.value = ''
  if (!file) return
  photoBusy.value = true
  try {
    emp.value = await apiUpload(
      `/api/admin/employees/${encodeURIComponent(props.login)}/photo`, file
    )
    photoFailed.value = false
    photoVersion.value = Date.now()
    toast.success('Фото сохранено в AD')
  } catch (err) {
    toast.error(err.message)
  } finally {
    photoBusy.value = false
  }
}

async function removePhoto() {
  if (!confirm('Удалить фото из AD и справочника?')) return
  photoBusy.value = true
  try {
    await apiDelete(`/api/admin/employees/${encodeURIComponent(props.login)}/photo`)
    photoFailed.value = true
    photoVersion.value = Date.now()
    toast.success('Фото удалено')
  } catch (err) {
    toast.error(err.message)
  } finally {
    photoBusy.value = false
  }
}

const phoneRows = computed(() =>
  PHONE_FIELDS.map(({ key, label }) => {
    const value = formatPhone(emp.value?.[key])
    return { key, label, value, tel: toTel(value) }
  })
)

async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text)
    toast.success('Скопировано')
  } catch {
    toast.error('Не удалось скопировать')
  }
}

async function load() {
  loading.value = true
  error.value = ''
  emp.value = null
  deptInfo.value = null
  photoFailed.value = false
  try {
    const [e, d] = await Promise.all([
      apiGet(`/api/employees/${encodeURIComponent(props.login)}`),
      apiGet(`/api/employees/${encodeURIComponent(props.login)}/department`),
    ])
    emp.value = e
    deptInfo.value = d
    fillEditForm()
    remember(e)
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

<style scoped>
.emp-detail {
  max-width: 680px;
  margin: 0 auto;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(6px); }
  to   { opacity: 1; transform: none; }
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary, #57534e);
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px 0;
  margin-bottom: 16px;
  transition: color 120ms ease;
  font-family: inherit;
}

.back-link:hover {
  color: var(--text-primary, #1c1917);
}

.emp-detail-card {
  background: var(--bg-surface, #ffffff);
  border: 1px solid var(--border, #e7e5e4);
  border-radius: 16px;
  padding: 36px;
  box-shadow: var(--shadow-sm, 0 1px 3px rgba(28,25,23,0.04));
}

.emp-detail-header {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 32px;
  padding-bottom: 28px;
  border-bottom: 1px solid var(--border, #e7e5e4);
}

.emp-detail-avatar {
  width: 64px;
  height: 64px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 20px;
  color: #ffffff;
  flex-shrink: 0;
  letter-spacing: 0.02em;
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}

.emp-detail-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.photo-actions {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex-shrink: 0;
}

.photo-action-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  color: var(--text-tertiary, #a8a29e);
  background: var(--bg-subtle, #f5f5f4);
  border: 1px solid var(--border, #e7e5e4);
  border-radius: 8px;
  cursor: pointer;
  transition: all 120ms ease;
}

.photo-action-btn:hover:not(:disabled) {
  color: var(--text-primary, #1c1917);
  border-color: var(--border-strong, #d6d3d1);
}

.photo-action-btn:disabled {
  opacity: 0.5;
  cursor: default;
}

.emp-detail-info {
  flex: 1;
  min-width: 0;
}

.emp-detail-name {
  font-size: 22px;
  font-weight: 600;
  letter-spacing: -0.02em;
  color: var(--text-primary, #1c1917);
  line-height: 1.2;
  margin: 0 0 4px;
}

.emp-detail-email {
  display: inline-block;
  margin-bottom: 6px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-tertiary, #a8a29e);
  text-decoration: none;
  word-break: break-all;
}

.emp-detail-email:hover {
  color: var(--text-secondary, #57534e);
  text-decoration: underline;
}

.emp-detail-title {
  font-size: 14px;
  color: var(--text-secondary, #57534e);
  margin: 0 0 6px;
}

.emp-detail-login {
  font-size: 12px;
  color: var(--text-tertiary, #a8a29e);
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
}

.phone-input {
  width: 100%;
  padding: 0;
  margin: 0;
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 18px;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.02em;
  color: #1d4ed8;
  caret-color: #1d4ed8;
  appearance: none;
  -webkit-appearance: none;
  background: none;
  border: none;
  border-radius: 0;
  box-shadow: none;
  outline: none;
}

.phone-input:hover,
.phone-input:focus,
.phone-input:disabled {
  background: none;
  border: none;
  box-shadow: none;
  outline: none;
}

.phone-input:disabled {
  opacity: 0.5;
}

.phone-input:-webkit-autofill {
  -webkit-box-shadow: 0 0 0 100px var(--bg-surface, #ffffff) inset;
  -webkit-text-fill-color: #1d4ed8;
}

.phone-input::placeholder {
  color: var(--text-tertiary, #a8a29e);
  font-size: 13px;
  font-weight: 400;
  font-style: italic;
  letter-spacing: 0;
}

.save-indicator {
  width: 28px;
  font-size: 13px;
  color: var(--text-tertiary, #a8a29e);
  text-align: center;
  flex-shrink: 0;
  opacity: 0;
  transition: opacity 200ms ease;
}

.save-indicator.visible {
  opacity: 1;
  color: #0ca678;
}

.detail-section {
  margin-bottom: 28px;
}

.detail-section:last-child {
  margin-bottom: 0;
}

.section-heading {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-tertiary, #a8a29e);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 12px;
  padding-left: 39px;
}

.detail-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid var(--bg-subtle, #f5f5f4);
  position: relative;
}

.detail-row:last-child {
  border-bottom: none;
}

.detail-icon {
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-tertiary, #a8a29e);
  flex-shrink: 0;
}

.detail-label {
  width: 100px;
  flex-shrink: 0;
  font-size: 13px;
  color: var(--text-tertiary, #a8a29e);
}

.detail-value {
  flex: 1;
  font-size: 14px;
  color: var(--text-primary, #1c1917);
  word-break: break-word;
  min-width: 0;
}

.detail-link {
  color: var(--text-primary, #1c1917);
  text-decoration: none;
  border-bottom: 1px solid var(--border, #e7e5e4);
  transition: border-color 120ms ease;
}

.detail-link:hover {
  border-bottom-color: var(--text-primary, #1c1917);
  text-decoration: none;
}

.detail-phone {
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  font-weight: 800;
  font-size: 18px;
  letter-spacing: 0.02em;
  font-variant-numeric: tabular-nums;
  color: #1d4ed8;
  border-bottom: none;
}

.detail-phone:hover {
  color: #1e3a8a;
  text-decoration: underline;
  text-underline-offset: 3px;
}

.detail-empty-value {
  color: var(--border-strong, #d6d3d1);
  font-style: italic;
  font-size: 13px;
}

.dept-link {
  cursor: pointer;
  font-weight: 500;
}

.copy-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  border: none;
  background: transparent;
  color: var(--text-tertiary, #a8a29e);
  cursor: pointer;
  flex-shrink: 0;
  opacity: 0;
  transition: all 120ms ease;
}

.detail-row:hover .copy-btn {
  opacity: 1;
}

.copy-btn:hover {
  background: var(--bg-hover, #f5f5f4);
  color: var(--text-primary, #1c1917);
}

.detail-empty {
  text-align: center;
  padding: 32px 16px;
  color: var(--text-tertiary, #a8a29e);
  font-size: 13px;
}

.emp-detail-error {
  text-align: center;
  padding: 48px 32px;
}

.error-icon {
  color: var(--text-tertiary, #a8a29e);
  margin-bottom: 16px;
}

.error-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary, #1c1917);
  margin: 0 0 6px;
}

.error-text {
  font-size: 13px;
  color: var(--text-secondary, #57534e);
  margin: 0 0 20px;
}

.error-retry {
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-on-accent, #ffffff);
  background: var(--accent, #1c1917);
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-family: inherit;
  transition: background 120ms ease;
}

.error-retry:hover {
  background: var(--accent-hover, #292524);
}

.skeleton-avatar {
  width: 64px;
  height: 64px;
  border-radius: 14px;
  background: var(--bg-subtle, #f5f5f4);
  flex-shrink: 0;
}

.skeleton-header-text {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.skeleton-line {
  height: 14px;
  border-radius: 6px;
  background: var(--bg-subtle, #f5f5f4);
}

.skeleton-name {
  width: 55%;
  height: 20px;
}

.skeleton-title {
  width: 35%;
}

.skeleton-rows {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-top: 8px;
}

.skeleton-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.skeleton-label {
  width: 80px;
  height: 12px;
  border-radius: 4px;
  background: var(--bg-subtle, #f5f5f4);
}

.skeleton-value {
  height: 12px;
  border-radius: 4px;
  background: var(--bg-subtle, #f5f5f4);
}

.shimmer {
  position: relative;
  overflow: hidden;
}

.shimmer::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(255, 255, 255, 0.5) 50%,
    transparent 100%
  );
  animation: shimmer 1.6s ease-in-out infinite;
}

@keyframes shimmer {
  0%   { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

@media (max-width: 600px) {
  .emp-detail-card {
    padding: 24px 20px;
  }
  .emp-detail-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 14px;
  }
  .detail-row {
    flex-wrap: wrap;
    gap: 4px 12px;
  }
  .detail-icon {
    display: none;
  }
  .detail-label {
    width: 100%;
    font-size: 11px;
  }
  .section-heading {
    padding-left: 0;
  }
}
</style>
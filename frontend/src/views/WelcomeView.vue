<template>
  <div class="home">
    <!-- Big search -->
    <section class="hero">
      <h1 class="hero-title">Телефонный справочник</h1>
      <form class="hero-search" @submit.prevent="goSearch">
        <svg viewBox="0 0 24 24" width="20" height="20" class="hero-search-icon">
          <path
            d="M11 4a7 7 0 1 0 4.9 12L21 21M11 4a7 7 0 1 1 0 14 7 7 0 0 1 0-14z"
            fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"
          />
        </svg>
        <input
          ref="searchInput"
          v-model="query"
          type="search"
          placeholder="Фамилия, отдел или номер"
          autocomplete="off"
          @input="onInput"
        />
      </form>
    </section>

    <!-- Quick contacts -->
    <section v-if="contacts.length || auth.isAdmin" class="block">
      <div class="block-head">
        <h2>Частые номера</h2>
      </div>

      <div class="quick-grid">
        <div v-for="c in contacts" :key="c.id" class="quick-item">
          <template v-if="auth.isAdmin">
            <input
              v-model="drafts[c.id].name"
              class="quick-name-input"
              placeholder="Название"
              @blur="saveContact(c, 'name')"
              @keydown.enter.prevent="$event.target.blur()"
            />
            <input
              v-model="drafts[c.id].phone"
              class="quick-phone quick-phone-input"
              placeholder="номер"
              @blur="saveContact(c, 'phone')"
              @keydown.enter.prevent="$event.target.blur()"
            />
            <button class="quick-delete" title="Удалить" @click="removeContact(c)">×</button>
          </template>
          <template v-else>
            <div class="quick-name">{{ c.name }}</div>
            <a
              class="quick-phone"
              :href="`tel:${toTel(c.phone)}`"
              title="Нажмите, чтобы скопировать"
              @click.prevent="copy(c.phone)"
            >{{ c.phone }}</a>
          </template>
        </div>

        <!-- Admin: add new -->
        <form v-if="auth.isAdmin" class="quick-item quick-add" @submit.prevent="addContact">
          <input v-model="newContact.name" class="quick-name-input" placeholder="Новый: название" />
          <input v-model="newContact.phone" class="quick-phone quick-phone-input" placeholder="номер" />
          <button
            type="submit"
            class="quick-add-btn"
            :disabled="adding || !newContact.name.trim() || !newContact.phone.trim()"
          >
            Добавить
          </button>
        </form>
      </div>
    </section>

    <!-- Recent -->
    <section v-if="recent.length" class="block">
      <div class="block-head">
        <h2>Недавно просмотренные</h2>
        <button class="block-action" @click="clearRecent">Очистить</button>
      </div>

      <div class="recent-list">
        <RouterLink
          v-for="r in recent"
          :key="r.login"
          :to="{ name: 'employee', params: { login: r.login } }"
          class="recent-item"
        >
          <div class="recent-main">
            <div class="recent-name">{{ r.full_name }}</div>
            <div class="recent-title">{{ r.title || 'Должность не указана' }}</div>
          </div>
          <span v-if="r.phone" class="recent-phone">{{ r.phone }}</span>
          <span v-else class="recent-no-phone">нет номера</span>
        </RouterLink>
      </div>
    </section>

    <p v-if="!contacts.length && !recent.length && !auth.isAdmin" class="home-hint">
      Начните вводить фамилию, название отдела или номер — или выберите отдел в дереве слева.
    </p>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { apiGet, apiPost, apiPut, apiDelete } from '../api'
import { useAuthStore } from '../stores/auth'
import { useToast } from '../composables/useToast'
import { useRecent } from '../composables/useRecent'

const router = useRouter()
const auth = useAuthStore()
const toast = useToast()
const { recent, clear: clearRecent } = useRecent()

/* ---- Search ---- */
const query = ref('')
const searchInput = ref(null)
let debounceTimer = null

function goSearch() {
  clearTimeout(debounceTimer)
  const q = query.value.trim()
  if (q) router.push({ name: 'search', query: { q } })
}

function onInput() {
  clearTimeout(debounceTimer)
  if (query.value.trim()) debounceTimer = setTimeout(goSearch, 400)
}

/* ---- Quick contacts ---- */
const contacts = ref([])
const drafts = reactive({})
const newContact = reactive({ name: '', phone: '' })
const adding = ref(false)

function syncDraft(c) {
  drafts[c.id] = { name: c.name, phone: c.phone }
}

async function loadContacts() {
  try {
    contacts.value = await apiGet('/api/quick-contacts')
    contacts.value.forEach(syncDraft)
  } catch (e) {
    toast.error(e.message)
  }
}

async function saveContact(c, field) {
  const value = (drafts[c.id][field] || '').trim()
  if (value === c[field]) return
  if (!value) {
    drafts[c.id][field] = c[field]
    toast.error(field === 'name' ? 'Название не может быть пустым' : 'Номер не может быть пустым')
    return
  }
  try {
    const updated = await apiPut(`/api/quick-contacts/${c.id}`, { [field]: value })
    Object.assign(c, updated)
    syncDraft(c)
  } catch (e) {
    drafts[c.id][field] = c[field]
    toast.error(e.message)
  }
}

async function addContact() {
  adding.value = true
  try {
    const created = await apiPost('/api/quick-contacts', {
      name: newContact.name.trim(),
      phone: newContact.phone.trim(),
    })
    contacts.value.push(created)
    syncDraft(created)
    newContact.name = ''
    newContact.phone = ''
  } catch (e) {
    toast.error(e.message)
  } finally {
    adding.value = false
  }
}

async function removeContact(c) {
  if (!confirm(`Удалить «${c.name}» из частых номеров?`)) return
  try {
    await apiDelete(`/api/quick-contacts/${c.id}`)
    contacts.value = contacts.value.filter((x) => x.id !== c.id)
    delete drafts[c.id]
  } catch (e) {
    toast.error(e.message)
  }
}

/* ---- Utils ---- */
const toTel = (v) => String(v || '').replace(/[^\d+]/g, '')

async function copy(text) {
  try {
    await navigator.clipboard.writeText(text)
    toast.success(`Скопировано: ${text}`)
  } catch {
    toast.error('Не удалось скопировать')
  }
}

onMounted(() => {
  loadContacts()
  searchInput.value?.focus()
})
</script>

<style scoped>
.home {
  max-width: 880px;
  margin: 0 auto;
  padding: 24px 0 48px;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(6px); }
  to   { opacity: 1; transform: none; }
}

/* ---------- Hero / search ---------- */
.hero {
  text-align: center;
  margin-bottom: 40px;
}

.hero-title {
  font-size: 26px;
  font-weight: 600;
  letter-spacing: -0.02em;
  color: var(--text-primary, #1c1917);
  margin: 0 0 20px;
}

.hero-search {
  position: relative;
  max-width: 620px;
  margin: 0 auto;
}

.hero-search-icon {
  position: absolute;
  left: 18px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-tertiary, #a8a29e);
  pointer-events: none;
}

.hero-search input {
  width: 100%;
  padding: 16px 20px 16px 50px;
  font-size: 17px;
  font-family: inherit;
  color: var(--text-primary, #1c1917);
  background: var(--bg-surface, #ffffff);
  border: 1px solid var(--border, #e7e5e4);
  border-radius: 14px;
  outline: none;
  box-shadow: 0 2px 8px rgba(28, 25, 23, 0.04);
  transition: border-color 120ms ease, box-shadow 120ms ease;
}

.hero-search input:hover {
  border-color: var(--border-strong, #d6d3d1);
}

.hero-search input:focus {
  border-color: #93c5fd;
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.12);
}

.hero-search input::placeholder {
  color: var(--text-tertiary, #a8a29e);
}

/* ---------- Blocks ---------- */
.block {
  margin-bottom: 36px;
}

.block-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 12px;
}

.block-head h2 {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-tertiary, #a8a29e);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin: 0;
}

.block-action {
  font-size: 12px;
  font-family: inherit;
  color: var(--text-tertiary, #a8a29e);
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
}

.block-action:hover {
  color: var(--text-primary, #1c1917);
}

/* ---------- Quick contacts ---------- */
.quick-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 10px;
}

.quick-item {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 14px 16px;
  background: var(--bg-surface, #ffffff);
  border: 1px solid var(--border, #e7e5e4);
  border-radius: 12px;
  transition: border-color 120ms ease;
}

.quick-item:hover {
  border-color: var(--border-strong, #d6d3d1);
}

.quick-name {
  font-size: 13px;
  color: var(--text-secondary, #57534e);
}

.quick-phone {
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 20px;
  font-weight: 800;
  letter-spacing: 0.02em;
  font-variant-numeric: tabular-nums;
  color: #1d4ed8;
  text-decoration: none;
  cursor: pointer;
}

a.quick-phone:hover {
  color: #1e3a8a;
}

.quick-name-input,
.quick-phone-input {
  appearance: none;
  border: none;
  background: none;
  outline: none;
  padding: 0;
  margin: 0;
  width: 100%;
  cursor: text;
}

.quick-name-input {
  font-family: inherit;
  font-size: 13px;
  color: var(--text-secondary, #57534e);
}

.quick-phone-input {
  caret-color: #1d4ed8;
}

.quick-name-input::placeholder,
.quick-phone-input::placeholder {
  color: var(--text-tertiary, #a8a29e);
  font-family: inherit;
  font-size: 13px;
  font-weight: 400;
  font-style: italic;
  letter-spacing: 0;
}

.quick-delete {
  position: absolute;
  top: 6px;
  right: 8px;
  width: 22px;
  height: 22px;
  font-size: 16px;
  line-height: 1;
  color: var(--text-tertiary, #a8a29e);
  background: none;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  opacity: 0;
  transition: opacity 120ms ease;
}

.quick-item:hover .quick-delete {
  opacity: 1;
}

.quick-delete:hover {
  color: #c92a2a;
}

.quick-add {
  border-style: dashed;
  background: transparent;
}

.quick-add-btn {
  align-self: flex-start;
  margin-top: 4px;
  padding: 4px 10px;
  font-size: 12px;
  font-family: inherit;
  color: var(--text-secondary, #57534e);
  background: var(--bg-subtle, #f5f5f4);
  border: 1px solid var(--border, #e7e5e4);
  border-radius: 6px;
  cursor: pointer;
}

.quick-add-btn:disabled {
  opacity: 0.5;
  cursor: default;
}

/* ---------- Recent ---------- */
.recent-list {
  background: var(--bg-surface, #ffffff);
  border: 1px solid var(--border, #e7e5e4);
  border-radius: 12px;
  overflow: hidden;
}

.recent-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 16px;
  text-decoration: none;
  color: inherit;
  border-bottom: 1px solid var(--bg-subtle, #f5f5f4);
  transition: background 120ms ease;
}

.recent-item:last-child {
  border-bottom: none;
}

.recent-item:hover {
  background: var(--bg-subtle, #f5f5f4);
  text-decoration: none;
}

.recent-main {
  flex: 1;
  min-width: 0;
}

.recent-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary, #1c1917);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.recent-title {
  font-size: 12px;
  color: var(--text-tertiary, #a8a29e);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.recent-phone {
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 17px;
  font-weight: 800;
  letter-spacing: 0.02em;
  font-variant-numeric: tabular-nums;
  color: #1d4ed8;
  flex-shrink: 0;
}

.recent-no-phone {
  font-size: 12px;
  font-style: italic;
  color: var(--text-tertiary, #a8a29e);
  flex-shrink: 0;
}

.home-hint {
  text-align: center;
  font-size: 13px;
  color: var(--text-tertiary, #a8a29e);
}

@media (max-width: 600px) {
  .hero-search input {
    font-size: 15px;
    padding: 14px 16px 14px 44px;
  }
}
</style>

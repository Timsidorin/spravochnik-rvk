<template>
  <div class="admins">
    <h1 class="admins-title">Администраторы</h1>
    <p class="admins-hint">
      Администраторы могут вносить номера, запускать синхронизацию с AD и вести частые номера.
      Добавлять и удалять администраторов можете только вы.
    </p>

    <form class="add-form" @submit.prevent="addAdmin">
      <input
        v-model="newLogin"
        class="add-input"
        placeholder="Логин сотрудника, например ivanov"
        autocomplete="off"
        :disabled="adding"
      />
      <button type="submit" class="add-btn" :disabled="adding || !newLogin.trim()">
        {{ adding ? 'Добавляю...' : 'Добавить' }}
      </button>
    </form>

    <div v-if="loading" class="admins-empty">Загрузка...</div>

    <div v-else class="admins-list">
      <div v-for="a in admins" :key="a.login" class="admin-row">
        <div class="admin-main">
          <div class="admin-name">{{ a.full_name || a.login }}</div>
          <div class="admin-login">{{ a.login }}</div>
        </div>
        <span v-if="a.from_env" class="admin-badge">из настроек сервера</span>
        <span v-else class="admin-meta">добавил {{ a.added_by }}</span>
        <button
          v-if="!a.from_env"
          class="admin-delete"
          title="Убрать права администратора"
          @click="removeAdmin(a)"
        >
          ×
        </button>
        <span v-else class="admin-delete-spacer"></span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { apiDelete, apiGet, apiPost } from '../api'
import { useToast } from '../composables/useToast'

const toast = useToast()

const admins = ref([])
const loading = ref(true)
const newLogin = ref('')
const adding = ref(false)

async function load() {
  try {
    admins.value = await apiGet('/api/admin/admins')
  } catch (e) {
    toast.error(e.message)
  } finally {
    loading.value = false
  }
}

async function addAdmin() {
  adding.value = true
  try {
    const created = await apiPost('/api/admin/admins', { login: newLogin.value.trim() })
    admins.value.push(created)
    newLogin.value = ''
    toast.success(`${created.full_name || created.login} теперь администратор`)
  } catch (e) {
    toast.error(e.message)
  } finally {
    adding.value = false
  }
}

async function removeAdmin(a) {
  if (!confirm(`Убрать права администратора у ${a.full_name || a.login}?`)) return
  try {
    await apiDelete(`/api/admin/admins/${encodeURIComponent(a.login)}`)
    admins.value = admins.value.filter((x) => x.login !== a.login)
  } catch (e) {
    toast.error(e.message)
  }
}

onMounted(load)
</script>

<style scoped>
.admins {
  max-width: 680px;
  margin: 0 auto;
  padding: 24px 0 48px;
}

.admins-title {
  font-size: 22px;
  font-weight: 600;
  letter-spacing: -0.02em;
  color: var(--text-primary, #1c1917);
  margin: 0 0 8px;
}

.admins-hint {
  font-size: 13px;
  line-height: 1.5;
  color: var(--text-tertiary, #a8a29e);
  margin: 0 0 24px;
}

.add-form {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
}

.add-input {
  flex: 1;
  padding: 10px 14px;
  font-size: 14px;
  font-family: inherit;
  color: var(--text-primary, #1c1917);
  background: var(--bg-surface, #ffffff);
  border: 1px solid var(--border, #e7e5e4);
  border-radius: 10px;
  outline: none;
  transition: border-color 120ms ease, box-shadow 120ms ease;
}

.add-input:focus {
  border-color: #93c5fd;
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.12);
}

.add-btn {
  padding: 10px 18px;
  font-size: 13px;
  font-weight: 500;
  font-family: inherit;
  color: var(--text-on-accent, #ffffff);
  background: var(--accent, #1c1917);
  border: none;
  border-radius: 10px;
  cursor: pointer;
}

.add-btn:disabled {
  opacity: 0.5;
  cursor: default;
}

.admins-empty {
  font-size: 13px;
  color: var(--text-tertiary, #a8a29e);
}

.admins-list {
  background: var(--bg-surface, #ffffff);
  border: 1px solid var(--border, #e7e5e4);
  border-radius: 12px;
  overflow: hidden;
}

.admin-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--bg-subtle, #f5f5f4);
}

.admin-row:last-child {
  border-bottom: none;
}

.admin-main {
  flex: 1;
  min-width: 0;
}

.admin-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary, #1c1917);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.admin-login {
  font-size: 12px;
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  color: var(--text-tertiary, #a8a29e);
}

.admin-badge,
.admin-meta {
  font-size: 12px;
  color: var(--text-tertiary, #a8a29e);
  flex-shrink: 0;
}

.admin-badge {
  padding: 2px 8px;
  border: 1px solid var(--border, #e7e5e4);
  border-radius: 6px;
}

.admin-delete,
.admin-delete-spacer {
  width: 28px;
  height: 28px;
  flex-shrink: 0;
}

.admin-delete {
  font-size: 18px;
  line-height: 1;
  color: var(--text-tertiary, #a8a29e);
  background: none;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}

.admin-delete:hover {
  color: #c92a2a;
  background: var(--bg-subtle, #f5f5f4);
}
</style>

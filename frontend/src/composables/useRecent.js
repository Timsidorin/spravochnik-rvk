import { ref } from 'vue'

const KEY = 'phonebook.recent'
const LIMIT = 8

function read() {
  try {
    const data = JSON.parse(localStorage.getItem(KEY) || '[]')
    return Array.isArray(data) ? data : []
  } catch {
    return []
  }
}

const recent = ref(read())

function save() {
  localStorage.setItem(KEY, JSON.stringify(recent.value))
}

export function useRecent() {
  function remember(emp) {
    if (!emp?.login) return
    const entry = {
      login: emp.login,
      full_name: emp.full_name,
      title: emp.title || '',
      phone: emp.phone || '',
    }
    recent.value = [entry, ...recent.value.filter((e) => e.login !== emp.login)].slice(0, LIMIT)
    save()
  }

  function clear() {
    recent.value = []
    save()
  }

  return { recent, remember, clear }
}

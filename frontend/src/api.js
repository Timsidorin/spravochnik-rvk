import { useAuthStore } from './stores/auth'
import router from './router'

const API_BASE = '' // пусто — Vite проксирует /api на бэкенд

export async function api(path, opts = {}) {
  const auth = useAuthStore()
  const { skipAuth, ...fetchOpts } = opts

  const headers = { 'Content-Type': 'application/json', ...(fetchOpts.headers || {}) }

  const res = await fetch(API_BASE + path, {
    ...fetchOpts,
    headers,
    credentials: 'same-origin',
  })

  if (res.status === 401 && !skipAuth) {
    auth.logout()
    const current = router.currentRoute.value
    if (current.name !== 'login') {
      router.replace({ name: 'login', query: { redirect: current.fullPath } })
    }
    const err = new Error('Сессия истекла, войдите заново')
    err.status = 401
    throw err
  }

  if (!res.ok) {
    let message = `Ошибка ${res.status}`
    try {
      const data = await res.json()
      if (typeof data.detail === 'string') message = data.detail
    } catch {}
    const err = new Error(message)
    err.status = res.status
    throw err
  }

  if (res.status === 204) return null
  return res.json()
}

export const apiGet = (path) => api(path)

export const apiPost = (path, body, opts = {}) =>
  api(path, {
    ...opts,
    method: 'POST',
    body: body ? JSON.stringify(body) : undefined,
  })

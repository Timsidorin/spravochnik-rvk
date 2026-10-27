import { useAuthStore } from './stores/auth'

const API_BASE = '' // пусто — Vite проксирует /api на бэкенд

export async function api(path, opts = {}) {
  const auth = useAuthStore()

  const headers = { 'Content-Type': 'application/json', ...(opts.headers || {}) }
  if (auth.token && !opts.skipAuth) {
    headers['Authorization'] = `Bearer ${auth.token}`
  }

  const res = await fetch(API_BASE + path, { ...opts, headers })

  if (res.status === 401 && !opts.skipAuth) {
    auth.logout()
    const err = new Error('Сессия истекла, войдите заново')
    err.status = 401
    throw err
  }

  if (!res.ok) {
    let message = `Ошибка ${res.status}`
    try {
      const data = await res.json()
      message = data.detail || message
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
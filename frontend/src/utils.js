export const PHONE_FIELDS = [
  { key: 'phone', label: 'Рабочий' },
  { key: 'mobile', label: 'Мобильный' },
  { key: 'ip_phone', label: 'IP-телефон' },
  { key: 'sip_line', label: 'SIP / Teams' },
  { key: 'other_phone', label: 'Другой' },
]

export const toTel = (value) => String(value || '').replace(/[^\d+]/g, '')

// "tel:+78121234567;ext=1003" -> "+78121234567 доб. 1003"
export function formatPhone(raw) {
  if (!raw) return ''
  const s = String(raw).replace(/^tel:/i, '').trim()
  const m = s.match(/^(.*?);ext=(.*)$/i)
  return m ? `${m[1]} доб. ${m[2]}` : s
}

export function initials(name) {
  const parts = (name || '').trim().split(/\s+/).filter(Boolean)
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase()
  return (name || '?').slice(0, 2).toUpperCase()
}

export function pickByName(name, list) {
  let h = 0
  for (const c of name || '') h = (h * 31 + c.charCodeAt(0)) >>> 0
  return list[h % list.length]
}

// v меняют после загрузки нового фото, чтобы сбросить кэш браузера
export function photoUrl(login, v) {
  const url = `/api/employees/${encodeURIComponent(login)}/photo`
  return v ? `${url}?v=${v}` : url
}

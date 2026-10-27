<template>
  <div
    class="employee-card"
    :class="{ 'head-card': head }"
    @click="onClick"
  >
    <div class="employee-card-inner">
      <div class="emp-avatar" :style="avatarStyle">{{ initials }}</div>
      <div class="emp-body">
        <div class="emp-name">
          {{ emp.full_name }}
          <span v-if="head" class="badge-head">Руководитель</span>
        </div>
        <div class="emp-title">{{ emp.title || '—' }}</div>
        <div class="emp-phones">
          <template v-if="phones.length">
            <a
              v-for="p in phones"
              :key="p.label"
              class="emp-phone"
              :href="`tel:${p.tel}`"
              @click.stop
            >{{ p.icon }} {{ p.label }}</a>
          </template>
          <span v-else class="emp-no-phone">телефон не указан</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({
  emp: { type: Object, required: true },
  head: { type: Boolean, default: false },
})

const router = useRouter()

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
  const [c1, c2] = colorFor(props.emp.full_name)
  return { background: `linear-gradient(135deg, ${c1}, ${c2})` }
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
  return m ? `${m[1]} (доб. ${m[2]})` : s
}

const phones = computed(() => {
  const e = props.emp
  const list = []
  if (e.phone) list.push({ icon: '📞', label: e.phone, tel: e.phone.replace(/[^\d+]/g, '') })
  if (e.mobile) list.push({ icon: '📱', label: e.mobile, tel: e.mobile.replace(/[^\d+]/g, '') })
  if (e.ip_phone) list.push({ icon: '☎', label: e.ip_phone, tel: e.ip_phone.replace(/[^\d+]/g, '') })
  if (e.sip_line) {
    const v = formatPhone(e.sip_line)
    list.push({ icon: '🎧', label: v, tel: v.replace(/[^\d+]/g, '') })
  }
  return list
})

function onClick() {
  router.push({ name: 'employee', params: { login: props.emp.login } })
}
</script>
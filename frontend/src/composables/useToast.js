import { reactive } from 'vue'

const state = reactive({
  message: '',
  type: '',
  visible: false,
})

let timer = null

function show(message, type = '') {
  state.message = message
  state.type = type
  state.visible = true
  clearTimeout(timer)
  timer = setTimeout(() => {
    state.visible = false
  }, 3500)
}

export function useToast() {
  return {
    state,
    show,
    success: (m) => show(m, 'success'),
    error: (m) => show(m, 'error'),
  }
}
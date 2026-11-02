import { reactive } from 'vue'

// Перетаскиваемый сейчас узел дерева: { node, siblings }
export const treeDnd = reactive({ dragging: null })

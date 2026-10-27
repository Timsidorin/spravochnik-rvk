<template>
  <nav class="tree-nav">
    <div v-if="loading" class="tree-empty">Загрузка...</div>
    <div v-else-if="!tree.length" class="tree-empty">
      Нет данных. Импортируйте из AD.
    </div>
    <ul v-else class="tree-root">
      <TreeNode v-for="node in tree" :key="node.id" :node="node" :level="0" />
    </ul>
  </nav>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { apiGet } from '../api'
import { useToast } from '../composables/useToast'
import TreeNode from './TreeNode.vue'

const tree = ref([])
const loading = ref(false)
const toast = useToast()

async function loadTree() {
  loading.value = true
  try {
    tree.value = await apiGet('/api/departments/tree')
  } catch (e) {
    toast.error(e.message)
    tree.value = []
  } finally {
    loading.value = false
  }
}

function handleReload() {
  loadTree()
}

onMounted(() => {
  loadTree()
  window.addEventListener('tree:reload', handleReload)
})

onUnmounted(() => {
  window.removeEventListener('tree:reload', handleReload)
})
</script>
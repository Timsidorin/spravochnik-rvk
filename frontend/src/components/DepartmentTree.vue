<template>
  <nav class="tree-nav" aria-label="Подразделения">
    <div v-if="loading" class="tree-skeleton" aria-busy="true" aria-label="Загрузка структуры">
      <div
        v-for="(w, i) in skeletonWidths"
        :key="i"
        class="skeleton-row"
        :style="{ paddingLeft: (i % 3) * 16 + 8 + 'px' }"
      >
        <div class="skeleton-icon shimmer"></div>
        <div class="skeleton-text shimmer" :style="{ width: w + '%' }"></div>
      </div>
    </div>

    <div v-else-if="!tree.length" class="tree-empty">
      <svg
        class="tree-empty-icon"
        width="32"
        height="32"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.5"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
        <line x1="12" y1="11" x2="12" y2="17" />
        <line x1="9" y1="14" x2="15" y2="14" />
      </svg>
      <p class="tree-empty-title">Структура пуста</p>
      <p class="tree-empty-hint">
        Импортируйте данные из Active Directory
      </p>
    </div>

    <Transition name="tree-appear">
      <ul v-if="!loading && tree.length" class="tree-root" role="tree">
        <TreeNode
          v-for="node in tree"
          :key="node.id"
          :node="node"
          :level="0"
        />
      </ul>
    </Transition>
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

const skeletonWidths = [62, 78, 54, 70, 45, 82, 58]

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

onMounted(() => {
  loadTree()
  window.addEventListener('tree:reload', loadTree)
})

onUnmounted(() => window.removeEventListener('tree:reload', loadTree))
</script>

<style scoped>
.tree-skeleton {
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.skeleton-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 8px;
  border-radius: var(--r-xs, 6px);
}

.skeleton-icon {
  width: 14px;
  height: 14px;
  border-radius: 3px;
  background: var(--bg-subtle, #f5f5f4);
  flex-shrink: 0;
}

.skeleton-text {
  height: 12px;
  border-radius: 4px;
  background: var(--bg-subtle, #f5f5f4);
}

.shimmer {
  position: relative;
  overflow: hidden;
}

.shimmer::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(255, 255, 255, 0.6) 50%,
    transparent 100%
  );
  animation: shimmer 1.6s ease-in-out infinite;
}

@keyframes shimmer {
  0%   { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

.tree-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  text-align: center;
  gap: 6px;
}

.tree-empty-icon {
  color: var(--text-tertiary, #a8a29e);
  margin-bottom: 8px;
  opacity: 0.5;
}

.tree-empty-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary, #57534e);
}

.tree-empty-hint {
  font-size: 12px;
  color: var(--text-tertiary, #a8a29e);
  line-height: 1.5;
  max-width: 200px;
}

.tree-appear-enter-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.tree-appear-enter-from {
  opacity: 0;
  transform: translateY(4px);
}
</style>
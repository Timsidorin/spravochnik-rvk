<template>
  <li class="tree-node">
    <div
      class="tree-row"
      :class="{ active: isActive }"
      :style="{ paddingLeft: 8 + level * 14 + 'px' }"
      @click="onClick"
    >
      <span
        class="tree-toggle"
        @click.stop="toggle"
      >{{ hasChildren ? (open ? '▾' : '▸') : '' }}</span>

      <span class="tree-label" :title="node.name">{{ node.name }}</span>

      <span v-if="node.employees_count" class="tree-count">
        {{ node.employees_count }}
      </span>
    </div>

    <ul
      v-if="hasChildren"
      class="tree-children"
      :style="{ display: open ? 'block' : 'none' }"
    >
      <TreeNode
        v-for="child in node.children"
        :key="child.id"
        :node="child"
        :level="level + 1"
      />
    </ul>
  </li>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const props = defineProps({
  node: { type: Object, required: true },
  level: { type: Number, default: 0 },
})

const route = useRoute()
const router = useRouter()
const open = ref(false)

const hasChildren = computed(() => (props.node.children?.length || 0) > 0)

const isActive = computed(
  () => route.name === 'department' && Number(route.params.id) === props.node.id
)

// Автоматически раскрываем ветку, если активный маршрут внутри неё
function containsActive(dept) {
  if (!dept) return false
  if (Number(route.params.id) === dept.id) return true
  return (dept.children || []).some(containsActive)
}

function syncOpen() {
  if (hasChildren.value && containsActive(props.node)) {
    open.value = true
  }
}

onMounted(syncOpen)
watch(() => route.params.id, syncOpen)

function toggle() {
  if (hasChildren.value) open.value = !open.value
}

function onClick() {
  if (hasChildren.value) open.value = true
  router.push({ name: 'department', params: { id: props.node.id } })
}
</script>
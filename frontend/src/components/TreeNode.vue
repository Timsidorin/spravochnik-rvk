<template>
  <li class="tree-node" role="treeitem" :aria-expanded="hasChildren ? isOpen : undefined">
    <div
      class="tree-row"
      :class="{ active: isActive }"
      @click="toggle"
      @keydown.enter.prevent="toggle"
      @keydown.right.prevent="hasChildren && !isOpen && (isOpen = true)"
      @keydown.left.prevent="hasChildren && isOpen ? (isOpen = false) : $emit('focus-parent')"
      tabindex="0"
    >
      <!-- Toggle chevron -->
      <span v-if="hasChildren" class="tree-toggle" :class="{ open: isOpen }">
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
          <path d="M4.5 2.5L8 6L4.5 9.5" stroke="currentColor" stroke-width="1.5"
                stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </span>
      <span v-else class="tree-toggle-spacer"></span>

      <!-- Icon: folder open / folder closed / dot -->
      <svg v-if="hasChildren && isOpen" class="tree-icon" width="16" height="16" viewBox="0 0 24 24"
           fill="none" stroke="currentColor" stroke-width="1.5"
           stroke-linecap="round" stroke-linejoin="round">
        <path d="M5 19a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h4l2 2h6a2 2 0 0 1 2 2v1"/>
        <path d="M20.13 12H7.87a1 1 0 0 0-.97.76L5 19h14.13a1 1 0 0 0 .97-.76L21.97 13a1 1 0 0 0-.97-1.24z"
              fill="currentColor" opacity="0.12"/>
        <path d="M20.13 12H7.87a1 1 0 0 0-.97.76L5 19h14.13a1 1 0 0 0 .97-.76L21.97 13a1 1 0 0 0-.97-1.24z"/>
      </svg>
      <svg v-else-if="hasChildren" class="tree-icon" width="16" height="16" viewBox="0 0 24 24"
           fill="none" stroke="currentColor" stroke-width="1.5"
           stroke-linecap="round" stroke-linejoin="round">
        <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"
              fill="currentColor" opacity="0.08"/>
        <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
      </svg>
      <span v-else class="tree-dot"></span>

      <!-- Label -->
      <span class="tree-label" :title="node.name">{{ node.name }}</span>

      <!-- Count badge -->
      <span v-if="node.employeeCount" class="tree-count">
        {{ node.employeeCount }}
      </span>
    </div>

    <!-- Children -->
    <Transition name="tree-collapse">
      <ul v-if="hasChildren && isOpen" class="tree-children" role="group">
        <TreeNode
          v-for="child in node.children"
          :key="child.id"
          :node="child"
          :level="level + 1"
        />
      </ul>
    </Transition>
  </li>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const props = defineProps({
  node: { type: Object, required: true },
  level: { type: Number, default: 0 },
})

defineEmits(['focus-parent'])

const route = useRoute()
const router = useRouter()
const isOpen = ref(false)

const hasChildren = computed(() => props.node.children?.length > 0)

const isActive = computed(() => {
  return route.params.id === String(props.node.id)
})

function toggle() {
  if (hasChildren.value) {
    isOpen.value = !isOpen.value
  }
  router.push({ name: 'department', params: { id: props.node.id } })
}
</script>

<style scoped>
/* ============================================
   NODE
   ============================================ */
.tree-node {
  list-style: none;
  position: relative;
}

/* ============================================
   ROW
   ============================================ */
.tree-row {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px 4px 4px;
  border-radius: 6px;
  cursor: pointer;
  user-select: none;
  color: var(--text-secondary, #57534e);
  transition: background 100ms ease, color 100ms ease;
  position: relative;
  outline: none;
  min-height: 34px;
}

.tree-row:hover {
  background: var(--bg-hover, #f5f5f4);
  color: var(--text-primary, #1c1917);
}

.tree-row:focus-visible {
  box-shadow: 0 0 0 2px var(--border-focus, #44403c);
}

.tree-row.active {
  background: var(--accent-soft, rgba(28, 25, 23, 0.06));
  color: var(--text-primary, #1c1917);
}

.tree-row.active .tree-label {
  font-weight: 600;
}

/* Active indicator bar */
.tree-row.active::after {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 2px;
  height: 16px;
  background: var(--accent, #1c1917);
  border-radius: 1px;
}

/* ============================================
   CHEVRON
   ============================================ */
.tree-toggle {
  width: 18px;
  height: 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: var(--text-tertiary, #a8a29e);
  transition: transform 150ms ease, color 100ms ease;
  border-radius: 4px;
}

.tree-toggle:hover {
  color: var(--text-primary, #1c1917);
  background: var(--bg-active, #ebebe9);
}

.tree-toggle.open {
  transform: rotate(90deg);
}

.tree-toggle-spacer {
  width: 18px;
  flex-shrink: 0;
}

/* ============================================
   ICONS
   ============================================ */
.tree-icon {
  flex-shrink: 0;
  color: var(--text-tertiary, #a8a29e);
  transition: color 100ms ease;
  margin-right: 2px;
}

.tree-row:hover .tree-icon {
  color: var(--text-secondary, #57534e);
}

.tree-row.active .tree-icon {
  color: var(--text-primary, #1c1917);
}

/* Leaf dot */
.tree-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--border-strong, #d6d3d1);
  flex-shrink: 0;
  margin: 0 7px 0 6px;
  transition: background 100ms ease;
}

.tree-row:hover .tree-dot {
  background: var(--text-tertiary, #a8a29e);
}

.tree-row.active .tree-dot {
  background: var(--accent, #1c1917);
}

/* ============================================
   LABEL & COUNT
   ============================================ */
.tree-label {
  flex: 1;
  font-size: 16px;
  line-height: 1.3;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  padding: 2px 0;
}

.tree-count {
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  color: var(--text-tertiary, #a8a29e);
  padding: 1px 6px;
  border-radius: 10px;
  flex-shrink: 0;
  font-weight: 500;
  background: var(--bg-subtle, #f5f5f4);
  transition: color 100ms ease, background 100ms ease;
  line-height: 1.4;
}

.tree-row:hover .tree-count {
  color: var(--text-secondary, #57534e);
  background: var(--bg-active, #ebebe9);
}

.tree-row.active .tree-count {
  color: var(--text-primary, #1c1917);
  background: var(--accent-soft-strong, rgba(28, 25, 23, 0.1));
}

/* ============================================
   CHILDREN & TREE LINES
   ============================================ */
.tree-children {
  list-style: none;
  padding: 0;
  margin: 0;
  position: relative;
  padding-left: 14px;
  margin-left: 12px;
}

/* Vertical line */
.tree-children::before {
  content: '';
  position: absolute;
  left: 0;
  top: 2px;
  bottom: 10px;
  width: 1px;
  background: var(--border, #e7e5e4);
}

/* Horizontal branch to each child row */
.tree-children > :deep(.tree-node) > .tree-row::before {
  content: '';
  position: absolute;
  left: -14px;
  top: 50%;
  width: 10px;
  height: 1px;
  background: var(--border, #e7e5e4);
}

/* Last child — vertical line stops at its center */
.tree-children > :deep(.tree-node):last-child::after {
  content: '';
  position: absolute;
  left: -14px;
  top: 50%;
  bottom: 0;
  width: 1px;
  background: var(--bg-surface, #ffffff);
}

/* ============================================
   COLLAPSE ANIMATION
   ============================================ */
.tree-collapse-enter-active {
  transition: opacity 180ms ease, max-height 200ms ease;
  overflow: hidden;
}

.tree-collapse-leave-active {
  transition: opacity 120ms ease, max-height 150ms ease;
  overflow: hidden;
}

.tree-collapse-enter-from,
.tree-collapse-leave-to {
  opacity: 0;
  max-height: 0;
}

.tree-collapse-enter-to,
.tree-collapse-leave-from {
  opacity: 1;
  max-height: 2000px;
}
</style>
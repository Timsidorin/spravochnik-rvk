<template>
  <Transition name="toast">
    <div
      v-if="toast.state.visible"
      class="toast"
      :class="toast.state.type"
    >
      {{ toast.state.message }}
    </div>
  </Transition>
</template>

<script setup>
import { useToast } from '../composables/useToast'

const toast = useToast()
</script>
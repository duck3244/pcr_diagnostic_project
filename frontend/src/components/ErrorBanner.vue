<script setup>
defineProps({ message: { type: String, default: null } })
</script>

<template>
  <div v-if="message" class="rounded-md bg-rose-50 border border-rose-200 p-3 text-sm text-rose-800">
    {{ message }}
  </div>
</template>

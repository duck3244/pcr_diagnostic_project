<script setup>
defineProps({ label: { type: String, default: 'Loading...' } })
</script>

<template>
  <div class="inline-flex items-center gap-2 text-sm text-slate-500">
    <svg class="animate-spin h-4 w-4 text-slate-400" viewBox="0 0 24 24" fill="none">
      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
      <path class="opacity-75" fill="currentColor"
        d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
    </svg>
    <span>{{ label }}</span>
  </div>
</template>

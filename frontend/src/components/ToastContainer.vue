<script setup>
import { useToastsStore } from '@/stores/toasts'

const toasts = useToastsStore()

const styles = {
  success: 'bg-emerald-50 border-emerald-300 text-emerald-900',
  error: 'bg-rose-50 border-rose-300 text-rose-900',
  info: 'bg-slate-50 border-slate-300 text-slate-900',
}
</script>

<template>
  <div class="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none">
    <transition-group name="toast" tag="div" class="flex flex-col gap-2">
      <div v-for="t in toasts.items" :key="t.id"
           :class="['rounded-md border shadow-sm px-4 py-3 text-sm pointer-events-auto', styles[t.type]]">
        <div class="flex items-start gap-2">
          <span class="flex-1 whitespace-pre-wrap">{{ t.message }}</span>
          <button class="text-current opacity-60 hover:opacity-100" @click="toasts.dismiss(t.id)">✕</button>
        </div>
      </div>
    </transition-group>
  </div>
</template>

<style scoped>
.toast-enter-active, .toast-leave-active { transition: all 0.18s ease; }
.toast-enter-from { opacity: 0; transform: translateY(8px); }
.toast-leave-to { opacity: 0; transform: translateX(20px); }
</style>

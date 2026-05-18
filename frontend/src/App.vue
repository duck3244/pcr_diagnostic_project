<script setup>
import { RouterLink, RouterView } from 'vue-router'
import ToastContainer from '@/components/ToastContainer.vue'
</script>

<template>
  <div class="min-h-screen flex flex-col">
    <header class="bg-white border-b border-slate-200">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex h-14 items-center justify-between">
        <div class="flex items-center gap-2">
          <span class="text-xl">🧬</span>
          <span class="font-semibold text-slate-900">PCR Diagnostic</span>
        </div>
        <nav class="flex gap-1">
          <RouterLink v-for="link in [
              { to: '/upload', label: 'Upload' },
              { to: '/qc', label: 'QC' },
              { to: '/quantification', label: 'ΔΔCt' },
              { to: '/ml', label: 'ML' },
            ]"
            :key="link.to"
            :to="link.to"
            class="px-3 py-1.5 rounded text-sm font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-100"
            active-class="bg-blue-50 text-blue-700"
          >
            {{ link.label }}
          </RouterLink>
        </nav>
      </div>
    </header>
    <main class="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <RouterView />
    </main>
    <ToastContainer />
  </div>
</template>

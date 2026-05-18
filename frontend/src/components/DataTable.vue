<script setup>
defineProps({
  columns: { type: Array, required: true },
  rows: { type: Array, required: true },
})
</script>

<template>
  <div class="overflow-x-auto rounded-md border border-slate-200">
    <table class="min-w-full text-sm">
      <thead class="bg-slate-50">
        <tr>
          <th v-for="c in columns" :key="c" class="px-3 py-2 text-left font-medium text-slate-600 whitespace-nowrap">
            {{ c }}
          </th>
        </tr>
      </thead>
      <tbody class="divide-y divide-slate-200">
        <tr v-for="(r, i) in rows" :key="i" class="hover:bg-slate-50">
          <td v-for="c in columns" :key="c" class="px-3 py-1.5 whitespace-nowrap text-slate-700">
            {{ r[c] === null || r[c] === undefined ? '—' : r[c] }}
          </td>
        </tr>
        <tr v-if="rows.length === 0">
          <td :colspan="columns.length" class="px-3 py-8 text-center text-slate-400">데이터 없음</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

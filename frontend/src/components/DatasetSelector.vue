<script setup>
import { onMounted, computed } from 'vue'
import { useDatasetsStore } from '@/stores/datasets'

const datasets = useDatasetsStore()
onMounted(() => {
  if (datasets.items.length === 0) datasets.fetchAll()
})

const selectedId = computed({
  get: () => datasets.selectedId,
  set: (v) => (datasets.selectedId = v),
})
</script>

<template>
  <div>
    <label class="label">데이터셋</label>
    <select v-model="selectedId" class="input">
      <option :value="null" disabled>데이터셋을 선택하세요</option>
      <option v-for="d in datasets.items" :key="d.id" :value="d.id">
        {{ d.filename }} ({{ d.n_samples }} samples)
      </option>
    </select>
    <p v-if="!datasets.loading && datasets.items.length === 0" class="mt-1 text-xs text-rose-600">
      먼저 Upload 페이지에서 데이터셋을 추가하세요.
    </p>
  </div>
</template>

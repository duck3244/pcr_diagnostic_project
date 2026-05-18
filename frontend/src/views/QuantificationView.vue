<script setup>
import { ref, computed, watch } from 'vue'
import { useDatasetsStore } from '@/stores/datasets'
import { useToastsStore } from '@/stores/toasts'
import { ddctApi } from '@/api/client'
import DatasetSelector from '@/components/DatasetSelector.vue'
import PlotlyChart from '@/components/PlotlyChart.vue'
import Spinner from '@/components/Spinner.vue'
import ErrorBanner from '@/components/ErrorBanner.vue'

const datasets = useDatasetsStore()
const toasts = useToastsStore()
const selected = computed(() => datasets.items.find((d) => d.id === datasets.selectedId) || null)

const targetGene = ref('')
const referenceGene = ref('')
const controlGroup = ref('')
const treatmentGroups = ref([])

const loading = ref(false)
const error = ref(null)
const result = ref(null)

watch(selected, (v) => {
  result.value = null
  if (v) {
    if (!targetGene.value || !v.genes.includes(targetGene.value)) {
      targetGene.value = v.genes[0] || ''
    }
    if (!referenceGene.value || referenceGene.value === targetGene.value || !v.genes.includes(referenceGene.value)) {
      referenceGene.value = v.genes.find((g) => g !== targetGene.value) || ''
    }
    if (!controlGroup.value || !v.groups.includes(controlGroup.value)) {
      controlGroup.value = v.groups[0] || ''
    }
    treatmentGroups.value = []
  }
}, { immediate: true })

async function run() {
  if (!datasets.selectedId) { error.value = '데이터셋을 선택하세요.'; return }
  if (targetGene.value === referenceGene.value) {
    error.value = 'target과 reference는 서로 달라야 합니다.'; return
  }
  loading.value = true
  error.value = null
  result.value = null
  try {
    result.value = await ddctApi.run(datasets.selectedId, {
      target_gene: targetGene.value,
      reference_gene: referenceGene.value,
      control_group: controlGroup.value,
      treatment_groups: treatmentGroups.value.length ? treatmentGroups.value : null,
    })
    toasts.success(`ΔΔCt 분석 완료 (${Object.keys(result.value.comparisons).length}개 비교)`)
  } catch (e) {
    error.value = e.message
    toasts.error(`ΔΔCt 실패: ${e.message}`)
  } finally {
    loading.value = false
  }
}

const validComparisons = computed(() => {
  if (!result.value) return []
  return Object.entries(result.value.comparisons)
    .filter(([, v]) => v.fold_change !== null && v.fold_change !== undefined && !Number.isNaN(v.fold_change))
    .map(([group, v]) => ({ group, ...v }))
})

const foldChangeChart = computed(() => {
  if (validComparisons.value.length === 0) return []
  return [{
    type: 'bar',
    x: validComparisons.value.map((c) => c.group),
    y: validComparisons.value.map((c) => c.fold_change),
    marker: {
      color: validComparisons.value.map((c) => (c.p_value < 0.05 ? '#dc2626' : '#94a3b8')),
    },
    text: validComparisons.value.map((c) => {
      if (c.p_value < 0.001) return '***'
      if (c.p_value < 0.01) return '**'
      if (c.p_value < 0.05) return '*'
      return 'ns'
    }),
    textposition: 'outside',
  }]
})

const foldChangeLayout = computed(() => ({
  title: result.value
    ? `${result.value.target_gene} expression (vs ${result.value.control_group})`
    : 'Fold Change',
  yaxis: { title: 'Fold Change', type: 'log' },
  margin: { t: 50, l: 60, r: 20, b: 60 },
  shapes: [{
    type: 'line', x0: -0.5, x1: validComparisons.value.length - 0.5,
    y0: 1, y1: 1, line: { color: '#0f172a', dash: 'dash', width: 1 },
  }],
}))

function downloadCsv() {
  if (!result.value) return
  const cols = ['group', 'delta_delta_ct', 'fold_change', 'log2_fold_change', 'p_value', 'significant', 'ci_95_lower', 'ci_95_upper', 'n_control', 'n_treatment']
  const rows = Object.entries(result.value.comparisons).map(([g, v]) => ({ group: g, ...v }))
  const csv = [cols.join(',')]
    .concat(rows.map((r) => cols.map((c) => r[c] ?? '').join(',')))
    .join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `ddct_${result.value.target_gene}.csv`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
</script>

<template>
  <section class="space-y-6">
    <h1 class="text-xl font-semibold">ΔΔCt Quantification</h1>

    <div class="card grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 items-end">
      <DatasetSelector />
      <div>
        <label class="label">Target gene</label>
        <select v-model="targetGene" class="input">
          <option v-for="g in selected?.genes || []" :key="g" :value="g">{{ g }}</option>
        </select>
      </div>
      <div>
        <label class="label">Reference gene</label>
        <select v-model="referenceGene" class="input">
          <option v-for="g in selected?.genes || []" :key="g" :value="g">{{ g }}</option>
        </select>
      </div>
      <div>
        <label class="label">Control group</label>
        <select v-model="controlGroup" class="input">
          <option v-for="g in selected?.groups || []" :key="g" :value="g">{{ g }}</option>
        </select>
      </div>
      <div>
        <label class="label">Treatment groups (비우면 전체)</label>
        <select v-model="treatmentGroups" multiple class="input min-h-[2.5rem]">
          <option v-for="g in (selected?.groups || []).filter((x) => x !== controlGroup)" :key="g" :value="g">
            {{ g }}
          </option>
        </select>
      </div>
      <div class="md:col-span-2 lg:col-span-5">
        <button class="btn-primary" :disabled="loading || !datasets.selectedId" @click="run">
          {{ loading ? 'Running…' : 'Run ΔΔCt' }}
        </button>
        <Spinner v-if="loading" class="ml-2" :label="''" />
      </div>
    </div>

    <ErrorBanner :message="error" />

    <template v-if="result">
      <div class="card">
        <div class="flex items-center justify-between mb-3">
          <h2 class="font-medium text-slate-800">Fold Change</h2>
          <button class="btn-secondary text-xs" @click="downloadCsv">CSV 다운로드</button>
        </div>
        <PlotlyChart :data="foldChangeChart" :layout="foldChangeLayout" />
        <p class="text-xs text-slate-500 mt-2">
          * p &lt; 0.05, ** p &lt; 0.01, *** p &lt; 0.001 / 빨강: 유의 / 회색: ns
        </p>
      </div>

      <div class="card">
        <h2 class="font-medium text-slate-800 mb-3">상세 결과</h2>
        <div class="overflow-x-auto">
          <table class="min-w-full text-sm">
            <thead class="bg-slate-50">
              <tr>
                <th class="px-3 py-2 text-left font-medium text-slate-600">Group</th>
                <th class="px-3 py-2 text-left font-medium text-slate-600">ΔΔCt</th>
                <th class="px-3 py-2 text-left font-medium text-slate-600">Fold Change</th>
                <th class="px-3 py-2 text-left font-medium text-slate-600">log2 FC</th>
                <th class="px-3 py-2 text-left font-medium text-slate-600">95% CI</th>
                <th class="px-3 py-2 text-left font-medium text-slate-600">p-value</th>
                <th class="px-3 py-2 text-left font-medium text-slate-600">N (ctrl/treat)</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-200">
              <tr v-for="(c, group) in result.comparisons" :key="group">
                <td class="px-3 py-1.5 font-medium">{{ group }}</td>
                <td class="px-3 py-1.5">{{ c.delta_delta_ct?.toFixed(3) ?? '—' }}</td>
                <td class="px-3 py-1.5" :class="c.significant ? 'text-rose-600 font-medium' : ''">
                  {{ c.fold_change?.toFixed(3) ?? '—' }}
                </td>
                <td class="px-3 py-1.5">{{ c.log2_fold_change?.toFixed(3) ?? '—' }}</td>
                <td class="px-3 py-1.5 text-xs">
                  {{ c.ci_95_lower !== null && c.ci_95_upper !== null
                      ? `[${c.ci_95_lower.toFixed(2)}, ${c.ci_95_upper.toFixed(2)}]`
                      : '—' }}
                </td>
                <td class="px-3 py-1.5">{{ c.p_value?.toFixed(4) ?? '—' }}</td>
                <td class="px-3 py-1.5 text-xs">{{ c.n_control }}/{{ c.n_treatment }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </section>
</template>

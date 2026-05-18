<script setup>
import { ref, computed } from 'vue'
import { useDatasetsStore } from '@/stores/datasets'
import { useToastsStore } from '@/stores/toasts'
import { qcApi } from '@/api/client'
import DatasetSelector from '@/components/DatasetSelector.vue'
import PlotlyChart from '@/components/PlotlyChart.vue'
import Spinner from '@/components/Spinner.vue'
import ErrorBanner from '@/components/ErrorBanner.vue'

const datasets = useDatasetsStore()
const toasts = useToastsStore()
const ctThreshold = ref(35)
const cvThreshold = ref(5)
const outlierMethod = ref('modified_zscore')
const referenceGenes = ref([])
const result = ref(null)
const loading = ref(false)
const error = ref(null)

const selected = computed(() => datasets.items.find((d) => d.id === datasets.selectedId) || null)

async function run() {
  if (!datasets.selectedId) {
    error.value = '데이터셋을 먼저 선택하세요.'
    return
  }
  loading.value = true
  error.value = null
  result.value = null
  try {
    result.value = await qcApi.run(datasets.selectedId, {
      ct_threshold: Number(ctThreshold.value),
      cv_threshold: Number(cvThreshold.value),
      outlier_method: outlierMethod.value,
      reference_genes: referenceGenes.value,
    })
    toasts.success('QC 분석 완료')
  } catch (e) {
    error.value = e.message
    toasts.error(`QC 실패: ${e.message}`)
  } finally {
    loading.value = false
  }
}

const boxplotData = computed(() => {
  if (!result.value) return []
  return result.value.boxplot.map((g) => ({
    type: 'box',
    name: g.gene,
    y: g.ct_values,
    boxpoints: 'outliers',
  }))
})

const boxplotLayout = {
  title: 'Ct Value Distribution by Gene',
  yaxis: { title: 'Ct value' },
  margin: { t: 40, l: 50, r: 20, b: 60 },
}

const cvHistData = computed(() => {
  if (!result.value) return []
  const cvs = result.value.reproducibility.details.map((d) => d.cv_percent)
  return [{
    type: 'histogram',
    x: cvs,
    nbinsx: 20,
    marker: { color: '#3b82f6' },
  }]
})

const cvHistLayout = {
  title: 'Reproducibility (CV%)',
  xaxis: { title: 'CV%' },
  yaxis: { title: 'Count' },
  shapes: [{
    type: 'line',
    x0: 5, x1: 5, y0: 0, y1: 1, yref: 'paper',
    line: { color: '#ef4444', dash: 'dash' },
  }],
  margin: { t: 40, l: 50, r: 20, b: 50 },
}
</script>

<template>
  <section class="space-y-6">
    <h1 class="text-xl font-semibold">Quality Control</h1>

    <div class="card grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 items-end">
      <DatasetSelector />
      <div>
        <label class="label">Ct 임계값</label>
        <input v-model.number="ctThreshold" type="number" step="0.1" class="input" />
      </div>
      <div>
        <label class="label">CV% 임계값</label>
        <input v-model.number="cvThreshold" type="number" step="0.1" class="input" />
      </div>
      <div>
        <label class="label">이상치 방법</label>
        <select v-model="outlierMethod" class="input">
          <option value="modified_zscore">modified z-score</option>
          <option value="zscore">z-score</option>
          <option value="grubbs">grubbs</option>
        </select>
      </div>
      <div>
        <label class="label">Reference 유전자 (효율 계산 제외)</label>
        <select v-model="referenceGenes" multiple class="input min-h-[2.5rem]">
          <option v-for="g in selected?.genes || []" :key="g" :value="g">{{ g }}</option>
        </select>
      </div>
      <div class="md:col-span-2 lg:col-span-5">
        <button class="btn-primary" :disabled="loading || !datasets.selectedId" @click="run">
          {{ loading ? 'Running…' : 'Run QC' }}
        </button>
        <Spinner v-if="loading" class="ml-2" :label="''" />
      </div>
    </div>

    <ErrorBanner :message="error" />

    <template v-if="result">
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div class="card">
          <p class="text-xs text-slate-500">Ct 범위 검사</p>
          <p class="text-2xl font-semibold" :class="result.ct_check.pass ? 'text-emerald-600' : 'text-rose-600'">
            {{ result.ct_check.pass ? 'PASS' : 'FAIL' }}
          </p>
          <p class="text-xs text-slate-500 mt-1">
            임계값 초과: {{ result.ct_check.above_threshold }} / {{ result.ct_check.total_measurements }}
          </p>
        </div>
        <div class="card">
          <p class="text-xs text-slate-500">NTC 검사</p>
          <p class="text-2xl font-semibold"
             :class="result.ntc_check.pass === null ? 'text-slate-400' : (result.ntc_check.pass ? 'text-emerald-600' : 'text-rose-600')">
            {{ result.ntc_check.pass === null ? 'N/A' : (result.ntc_check.pass ? 'PASS' : 'FAIL') }}
          </p>
          <p class="text-xs text-slate-500 mt-1">
            NTC {{ result.ntc_check.ntc_count }}, 증폭 {{ result.ntc_check.amplified_count }}
          </p>
        </div>
        <div class="card">
          <p class="text-xs text-slate-500">평균 CV%</p>
          <p class="text-2xl font-semibold">{{ result.reproducibility.mean_cv?.toFixed(2) ?? '—' }}%</p>
          <p class="text-xs text-slate-500 mt-1">
            CV {{ '>' }} {{ result.reproducibility.cv_threshold }}%: {{ result.reproducibility.high_cv_count }}
          </p>
        </div>
        <div class="card">
          <p class="text-xs text-slate-500">이상치</p>
          <p class="text-2xl font-semibold">{{ result.outliers.length }}</p>
          <p class="text-xs text-slate-500 mt-1">방법: {{ result.request.outlier_method }}</p>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div class="card">
          <PlotlyChart :data="boxplotData" :layout="boxplotLayout" />
        </div>
        <div class="card">
          <PlotlyChart :data="cvHistData" :layout="cvHistLayout" />
        </div>
      </div>

      <div class="card">
        <h2 class="font-medium text-slate-800 mb-3">증폭 효율</h2>
        <table class="min-w-full text-sm">
          <thead class="bg-slate-50">
            <tr>
              <th class="px-3 py-2 text-left font-medium text-slate-600">유전자</th>
              <th class="px-3 py-2 text-left font-medium text-slate-600">효율</th>
              <th class="px-3 py-2 text-left font-medium text-slate-600">R²</th>
              <th class="px-3 py-2 text-left font-medium text-slate-600">Slope</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-200">
            <tr v-for="(eff, gene) in result.efficiency" :key="gene">
              <td class="px-3 py-1.5 font-medium">{{ gene }}</td>
              <td class="px-3 py-1.5">{{ eff ? eff.efficiency.toFixed(1) + '%' : '— (표준 곡선 아님)' }}</td>
              <td class="px-3 py-1.5">{{ eff?.r_squared?.toFixed(3) ?? '—' }}</td>
              <td class="px-3 py-1.5">{{ eff?.slope?.toFixed(3) ?? '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </section>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useDatasetsStore } from '@/stores/datasets'
import { useToastsStore } from '@/stores/toasts'
import { mlApi } from '@/api/client'
import DatasetSelector from '@/components/DatasetSelector.vue'
import PlotlyChart from '@/components/PlotlyChart.vue'
import Spinner from '@/components/Spinner.vue'
import ErrorBanner from '@/components/ErrorBanner.vue'

const datasets = useDatasetsStore()
const toasts = useToastsStore()
const selected = computed(() => datasets.items.find((d) => d.id === datasets.selectedId) || null)

const modelType = ref('random_forest')
const targetCol = ref('group')
const testSize = ref(0.3)
const loading = ref(false)
const error = ref(null)
const result = ref(null)

async function run() {
  if (!datasets.selectedId) { error.value = '데이터셋을 선택하세요.'; return }
  loading.value = true
  error.value = null
  result.value = null
  try {
    result.value = await mlApi.train(datasets.selectedId, {
      model_type: modelType.value,
      target_col: targetCol.value,
      test_size: Number(testSize.value),
    })
    toasts.success(`${modelType.value} 학습 완료 — accuracy ${(result.value.accuracy * 100).toFixed(1)}%`)
  } catch (e) {
    error.value = e.message
    toasts.error(`학습 실패: ${e.message}`)
  } finally {
    loading.value = false
  }
}

const cmChart = computed(() => {
  if (!result.value) return []
  return [{
    type: 'heatmap',
    z: result.value.confusion_matrix,
    x: result.value.labels,
    y: result.value.labels,
    colorscale: 'Blues',
    showscale: true,
    text: result.value.confusion_matrix,
    texttemplate: '%{text}',
    textfont: { size: 16 },
  }]
})

const cmLayout = {
  title: 'Confusion Matrix',
  xaxis: { title: 'Predicted' },
  yaxis: { title: 'True', autorange: 'reversed' },
  margin: { t: 50, l: 100, r: 20, b: 80 },
}

const fiChart = computed(() => {
  if (!result.value || result.value.feature_importance.length === 0) return []
  const sorted = [...result.value.feature_importance].sort((a, b) => a.importance - b.importance)
  return [{
    type: 'bar',
    orientation: 'h',
    x: sorted.map((f) => f.importance),
    y: sorted.map((f) => f.feature),
    marker: { color: '#3b82f6' },
  }]
})

const fiLayout = {
  title: 'Feature Importance (top 15)',
  margin: { t: 50, l: 180, r: 20, b: 50 },
  yaxis: { automargin: true },
}
</script>

<template>
  <section class="space-y-6">
    <h1 class="text-xl font-semibold">ML Classification</h1>

    <div class="card grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 items-end">
      <DatasetSelector />
      <div>
        <label class="label">Model</label>
        <select v-model="modelType" class="input">
          <option value="random_forest">Random Forest</option>
          <option value="gradient_boosting">Gradient Boosting</option>
          <option value="svm">SVM</option>
          <option value="xgboost">XGBoost</option>
          <option value="ensemble">Voting Ensemble</option>
        </select>
      </div>
      <div>
        <label class="label">Target column</label>
        <input v-model="targetCol" class="input" />
      </div>
      <div>
        <label class="label">Test size</label>
        <input v-model.number="testSize" type="number" min="0.1" max="0.5" step="0.05" class="input" />
      </div>
      <div>
        <button class="btn-primary w-full" :disabled="loading || !datasets.selectedId" @click="run">
          {{ loading ? 'Training…' : 'Train' }}
        </button>
      </div>
      <div v-if="loading" class="md:col-span-2 lg:col-span-5">
        <Spinner label="모델 학습 중 (수 초~수십 초)…" />
      </div>
    </div>

    <ErrorBanner :message="error" />

    <template v-if="result">
      <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
        <div class="card">
          <p class="text-xs text-slate-500">정확도</p>
          <p class="text-2xl font-semibold">{{ (result.accuracy * 100).toFixed(1) }}%</p>
        </div>
        <div class="card">
          <p class="text-xs text-slate-500">F1</p>
          <p class="text-2xl font-semibold">{{ result.f1_score.toFixed(3) }}</p>
        </div>
        <div class="card">
          <p class="text-xs text-slate-500">Precision</p>
          <p class="text-2xl font-semibold">{{ result.precision.toFixed(3) }}</p>
        </div>
        <div class="card">
          <p class="text-xs text-slate-500">Recall</p>
          <p class="text-2xl font-semibold">{{ result.recall.toFixed(3) }}</p>
        </div>
        <div class="card">
          <p class="text-xs text-slate-500">CV mean ± std</p>
          <p class="text-2xl font-semibold">{{ result.cv_mean.toFixed(2) }}</p>
          <p class="text-xs text-slate-500">± {{ result.cv_std.toFixed(2) }}</p>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div class="card">
          <PlotlyChart :data="cmChart" :layout="cmLayout" />
        </div>
        <div class="card">
          <PlotlyChart v-if="fiChart.length" :data="fiChart" :layout="fiLayout" />
          <p v-else class="text-sm text-slate-400 text-center py-12">
            이 모델은 feature importance를 제공하지 않습니다.
          </p>
        </div>
      </div>

      <div class="card">
        <h2 class="font-medium text-slate-800 mb-3">클래스 분포</h2>
        <table class="text-sm">
          <thead class="bg-slate-50">
            <tr>
              <th class="px-3 py-2 text-left font-medium text-slate-600">클래스</th>
              <th class="px-3 py-2 text-left font-medium text-slate-600">샘플 수</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-200">
            <tr v-for="(n, cls) in result.class_counts" :key="cls">
              <td class="px-3 py-1.5">{{ cls }}</td>
              <td class="px-3 py-1.5">{{ n }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </section>
</template>

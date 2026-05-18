<script setup>
import { onMounted, ref, computed } from 'vue'
import { useDatasetsStore } from '@/stores/datasets'
import { useToastsStore } from '@/stores/toasts'
import { datasetsApi } from '@/api/client'
import UploadDropzone from '@/components/UploadDropzone.vue'
import DataTable from '@/components/DataTable.vue'
import Spinner from '@/components/Spinner.vue'
import ErrorBanner from '@/components/ErrorBanner.vue'

const datasets = useDatasetsStore()
const toasts = useToastsStore()
const uploading = ref(false)
const uploadProgress = ref(0)
const uploadError = ref(null)
const preview = ref(null)
const previewLoading = ref(false)

const selected = computed(() => datasets.items.find((d) => d.id === datasets.selectedId) || null)

onMounted(() => datasets.fetchAll())

async function handleFile(file) {
  uploading.value = true
  uploadError.value = null
  uploadProgress.value = 0
  try {
    const created = await datasets.upload(file, (e) => {
      if (e.total) uploadProgress.value = Math.round((e.loaded / e.total) * 100)
    })
    await loadPreview()
    toasts.success(`${created.filename} 업로드 완료 (${created.n_samples}개 샘플)`)
  } catch (e) {
    uploadError.value = e.message
    toasts.error(`업로드 실패: ${e.message}`)
  } finally {
    uploading.value = false
  }
}

async function selectDataset(id) {
  datasets.selectedId = id
  await loadPreview()
}

async function loadPreview() {
  if (!datasets.selectedId) {
    preview.value = null
    return
  }
  previewLoading.value = true
  try {
    preview.value = await datasetsApi.preview(datasets.selectedId, 20)
  } catch (e) {
    preview.value = null
  } finally {
    previewLoading.value = false
  }
}

async function remove(id) {
  if (!confirm('이 데이터셋을 삭제할까요?')) return
  try {
    await datasets.remove(id)
    if (datasets.selectedId === null) preview.value = null
    toasts.info('삭제되었습니다.')
  } catch (e) {
    toasts.error(`삭제 실패: ${e.message}`)
  }
}

function fmtDate(iso) {
  return new Date(iso).toLocaleString()
}
</script>

<template>
  <section class="space-y-6">
    <h1 class="text-xl font-semibold">Upload &amp; Datasets</h1>

    <UploadDropzone @file-selected="handleFile" />
    <div v-if="uploading" class="space-y-2">
      <Spinner :label="`업로드 중 ${uploadProgress}%`" />
      <div class="h-1.5 bg-slate-200 rounded">
        <div class="h-full bg-blue-500 rounded transition-all" :style="{ width: `${uploadProgress}%` }" />
      </div>
    </div>
    <ErrorBanner :message="uploadError" />

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div class="card lg:col-span-1">
        <div class="flex items-center justify-between mb-3">
          <h2 class="font-medium text-slate-800">데이터셋</h2>
          <Spinner v-if="datasets.loading" label="" />
        </div>
        <ErrorBanner :message="datasets.error" />
        <ul class="space-y-2">
          <li v-for="d in datasets.items" :key="d.id"
              :class="['rounded-md border p-3 cursor-pointer transition-colors',
                       d.id === datasets.selectedId ? 'border-blue-500 bg-blue-50' : 'border-slate-200 hover:bg-slate-50']"
              @click="selectDataset(d.id)">
            <div class="flex items-start justify-between gap-2">
              <div class="min-w-0 flex-1">
                <p class="text-sm font-medium truncate" :title="d.filename">{{ d.filename }}</p>
                <p class="text-xs text-slate-500 mt-0.5">{{ fmtDate(d.uploaded_at) }}</p>
                <p class="text-xs text-slate-500 mt-0.5">
                  샘플 {{ d.n_samples }} · 유전자 {{ d.n_genes }} · 행 {{ d.n_rows }}
                </p>
              </div>
              <button class="text-xs text-rose-600 hover:text-rose-800" @click.stop="remove(d.id)">삭제</button>
            </div>
          </li>
          <li v-if="!datasets.loading && datasets.items.length === 0"
              class="text-sm text-slate-400 text-center py-6">
            업로드된 데이터셋이 없습니다.
          </li>
        </ul>
      </div>

      <div class="card lg:col-span-2">
        <div class="flex items-center justify-between mb-3">
          <h2 class="font-medium text-slate-800">미리보기</h2>
          <Spinner v-if="previewLoading" label="" />
        </div>
        <template v-if="selected">
          <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            <div class="rounded-md bg-slate-50 p-3">
              <p class="text-xs text-slate-500">샘플 수</p>
              <p class="text-lg font-semibold">{{ selected.n_samples }}</p>
            </div>
            <div class="rounded-md bg-slate-50 p-3">
              <p class="text-xs text-slate-500">유전자 수</p>
              <p class="text-lg font-semibold">{{ selected.n_genes }}</p>
            </div>
            <div class="rounded-md bg-slate-50 p-3">
              <p class="text-xs text-slate-500">그룹</p>
              <p class="text-sm font-medium">{{ selected.groups.join(', ') || '—' }}</p>
            </div>
            <div class="rounded-md bg-slate-50 p-3">
              <p class="text-xs text-slate-500">전체 행</p>
              <p class="text-lg font-semibold">{{ selected.n_rows }}</p>
            </div>
          </div>
          <DataTable v-if="preview" :columns="preview.columns" :rows="preview.rows" />
        </template>
        <p v-else class="text-sm text-slate-400 text-center py-12">왼쪽에서 데이터셋을 선택하세요.</p>
      </div>
    </div>
  </section>
</template>

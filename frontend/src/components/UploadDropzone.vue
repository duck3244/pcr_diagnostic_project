<script setup>
import { ref } from 'vue'

const emit = defineEmits(['file-selected'])

const dragOver = ref(false)
const fileInput = ref(null)

function onPick() {
  fileInput.value?.click()
}

function onFiles(files) {
  if (!files || files.length === 0) return
  emit('file-selected', files[0])
}

function onDrop(e) {
  dragOver.value = false
  onFiles(e.dataTransfer.files)
}
</script>

<template>
  <div
    @dragenter.prevent="dragOver = true"
    @dragover.prevent="dragOver = true"
    @dragleave.prevent="dragOver = false"
    @drop.prevent="onDrop"
    @click="onPick"
    :class="[
      'cursor-pointer rounded-lg border-2 border-dashed p-8 text-center transition-colors',
      dragOver ? 'border-blue-500 bg-blue-50' : 'border-slate-300 bg-white hover:border-slate-400',
    ]"
  >
    <input
      ref="fileInput"
      type="file"
      accept=".csv"
      class="hidden"
      @change="onFiles($event.target.files)"
    />
    <div class="text-3xl">📄</div>
    <p class="mt-2 text-sm font-medium text-slate-700">CSV 파일을 드래그하거나 클릭해서 업로드</p>
    <p class="mt-1 text-xs text-slate-500">필수 컬럼: sample_id, gene, ct_value (최대 10MB)</p>
  </div>
</template>

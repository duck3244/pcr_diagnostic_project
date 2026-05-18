import { defineStore } from 'pinia'
import { ref } from 'vue'
import { datasetsApi } from '@/api/client'

export const useDatasetsStore = defineStore('datasets', () => {
  const items = ref([])
  const selectedId = ref(null)
  const loading = ref(false)
  const error = ref(null)

  async function fetchAll() {
    loading.value = true
    error.value = null
    try {
      items.value = await datasetsApi.list()
    } catch (e) {
      error.value = e?.response?.data?.detail || e.message
    } finally {
      loading.value = false
    }
  }

  async function upload(file, onProgress) {
    error.value = null
    const created = await datasetsApi.upload(file, onProgress)
    await fetchAll()
    selectedId.value = created.id
    return created
  }

  async function remove(id) {
    await datasetsApi.remove(id)
    if (selectedId.value === id) selectedId.value = null
    await fetchAll()
  }

  function selected() {
    return items.value.find((d) => d.id === selectedId.value) || null
  }

  return { items, selectedId, loading, error, fetchAll, upload, remove, selected }
})

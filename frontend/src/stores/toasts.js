import { defineStore } from 'pinia'
import { ref } from 'vue'

let counter = 0

export const useToastsStore = defineStore('toasts', () => {
  const items = ref([])

  function push(message, { type = 'info', timeout = 4000 } = {}) {
    const id = ++counter
    items.value.push({ id, message, type })
    if (timeout > 0) setTimeout(() => dismiss(id), timeout)
    return id
  }
  function success(msg, opts) { return push(msg, { ...opts, type: 'success' }) }
  function error(msg, opts) { return push(msg, { ...opts, type: 'error', timeout: 6000 }) }
  function info(msg, opts) { return push(msg, { ...opts, type: 'info' }) }
  function dismiss(id) {
    items.value = items.value.filter((t) => t.id !== id)
  }

  return { items, push, success, error, info, dismiss }
})

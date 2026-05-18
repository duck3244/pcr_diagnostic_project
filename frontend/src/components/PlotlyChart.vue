<script setup>
import { onMounted, onBeforeUnmount, watch, ref } from 'vue'
import Plotly from 'plotly.js-dist-min'

const props = defineProps({
  data: { type: Array, required: true },
  layout: { type: Object, default: () => ({}) },
  config: { type: Object, default: () => ({ displaylogo: false, responsive: true }) },
})

const el = ref(null)

function render() {
  if (!el.value) return
  Plotly.react(el.value, props.data, props.layout, props.config)
}

onMounted(render)
onBeforeUnmount(() => {
  if (el.value) Plotly.purge(el.value)
})
watch(() => [props.data, props.layout], render, { deep: true })
</script>

<template>
  <div ref="el" class="w-full" style="min-height: 320px"></div>
</template>

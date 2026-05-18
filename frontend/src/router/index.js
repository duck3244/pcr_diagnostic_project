import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', redirect: '/upload' },
  { path: '/upload', name: 'upload', component: () => import('@/views/UploadView.vue'), meta: { title: 'Upload' } },
  { path: '/qc', name: 'qc', component: () => import('@/views/QCView.vue'), meta: { title: 'Quality Control' } },
  { path: '/quantification', name: 'quantification', component: () => import('@/views/QuantificationView.vue'), meta: { title: 'ΔΔCt' } },
  { path: '/ml', name: 'ml', component: () => import('@/views/MLView.vue'), meta: { title: 'ML' } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router

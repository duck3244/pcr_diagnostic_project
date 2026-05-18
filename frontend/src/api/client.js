import axios from 'axios'

const client = axios.create({
  baseURL: '/api',
  timeout: 120000,
})

// Normalize FastAPI error responses ({detail: "..."}) into Error.message
client.interceptors.response.use(
  (r) => r,
  (e) => {
    const detail = e?.response?.data?.detail
    if (detail) e.message = typeof detail === 'string' ? detail : JSON.stringify(detail)
    return Promise.reject(e)
  },
)

export default client

export const datasetsApi = {
  list: () => client.get('/datasets').then((r) => r.data),
  get: (id) => client.get(`/datasets/${id}`).then((r) => r.data),
  preview: (id, n = 20) => client.get(`/datasets/${id}/preview`, { params: { n } }).then((r) => r.data),
  upload: (file, onProgress) => {
    const form = new FormData()
    form.append('file', file)
    return client.post('/datasets', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: onProgress,
    }).then((r) => r.data)
  },
  remove: (id) => client.delete(`/datasets/${id}`),
}

export const qcApi = {
  run: (datasetId, body) => client.post(`/qc/${datasetId}`, body).then((r) => r.data),
}

export const ddctApi = {
  run: (datasetId, body) => client.post(`/quantification/ddct/${datasetId}`, body).then((r) => r.data),
}

export const mlApi = {
  train: (datasetId, body) => client.post(`/ml/train/${datasetId}`, body).then((r) => r.data),
}

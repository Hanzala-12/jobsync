import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export function getApiErrorMessage(error) {
  const payload = error?.response?.data
  if (payload && typeof payload === 'object') {
    if (typeof payload.message === 'string' && payload.message.trim()) {
      return payload.message.trim()
    }
    if (typeof payload.detail === 'string' && payload.detail.trim()) {
      return payload.detail.trim()
    }
    if (Array.isArray(payload.detail)) {
      return payload.detail.map(d => d.msg || JSON.stringify(d)).join('; ')
    }
    if (typeof payload.error === 'string' && payload.error.trim()) {
      return payload.error.trim()
    }
  }

  if (typeof error?.message === 'string' && error.message.trim()) {
    return error.message.trim()
  }

  return 'Something went wrong. Please try again.'
}

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status || 0
    const message = getApiErrorMessage(error)
    const normalized = {
      error: true,
      message,
      code: status,
    }

    if (error.response) {
      error.response.data = normalized
    }

    error.message = message
    error.userMessage = message
    error.apiError = normalized
    return Promise.reject(error)
  },
)

export const resumeAPI = {
  analyze: (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return apiClient.post('/resume/analyze', formData)
  },
  reanalyze: (jobDescription) => apiClient.post('/resume/reanalyze', { job_description: jobDescription }),
  rewrite: (payload) => apiClient.post('/resume/rewrite', payload),
  saveVersion: (payload) => apiClient.post('/resume/versions', payload),
  listVersions: () => apiClient.get('/resume/versions'),
  getVersion: (id) => apiClient.get(`/resume/versions/${id}`),
  deleteVersion: (id) => apiClient.delete(`/resume/versions/${id}`),
  updateVersionUsedFor: (id, usedFor) => apiClient.patch(`/resume/versions/${id}`, { used_for: usedFor }),
}

export const jobsAPI = {
  search: (params = {}) =>
    apiClient.get('/jobs/search', {
      params: {
        query: 'software engineer',
        location: 'Pakistan',
        remote_only: false,
        country_code: 'pk',
        ...params,
      },
    }),
  match: (jobId) => apiClient.get(`/jobs/${jobId}/match`),
  upsert: (job) => apiClient.post('/jobs/upsert', job),
  explainMatch: (payload) => apiClient.post('/jobs/explain-match', payload),
  salaryEstimate: (payload) => apiClient.post('/jobs/salary-estimate', payload),
  autocomplete: (query) => apiClient.get('/jobs/autocomplete', { params: { query } }),
}

export const profileAPI = {
  create: (formData) =>
    apiClient.post('/profile', formData),
  exists: () => apiClient.get('/profile'),
  select: (id) => apiClient.post(`/profile/select/${id}`),
  selected: () => apiClient.get('/profile/selected'),
  get: (id) => apiClient.get(`/profile/${id}`),
  update: (id, formData) => apiClient.patch(`/profile/${id}`, formData),
  list: (page = 1, per_page = 10) => apiClient.get('/profile', { params: { page, per_page } }),
  delete: (id) => apiClient.delete(`/profile/${id}`),
}

export const apiActions = {
  match: (jobId) => apiClient.post(`/match/${jobId}`),
  buildResume: (jobId) => apiClient.post(`/build_resume/${jobId}`),
  coverLetter: (jobId) => apiClient.post(`/cover_letter/${jobId}`),
}

export const applicationsAPI = {
  create: (data) => apiClient.post('/applications/', data),
  list: (status = null) => apiClient.get('/applications/', { params: status ? { status } : {} }),
  get: (appId) => apiClient.get(`/applications/${appId}`),
  updateStatus: (appId, status) => apiClient.patch(`/applications/${appId}/status`, { status }),
  update: (appId, data) => apiClient.patch(`/applications/${appId}`, data),
  delete: (appId) => apiClient.delete(`/applications/${appId}`),
  healthScore: () => apiClient.get('/applications/health-score'),
}

export const dailyScoutAPI = {
  run: (data) => apiClient.post('/scout/run', data),
  status: () => apiClient.get('/scout/status'),
}

export const coverLetterAPI = {
  generate: (data) => apiClient.post('/cover-letter/generate', data),
}

export const intelligenceAPI = {
  skillGap: (jobDescriptions) => apiClient.post('/intelligence/skill-gap', { job_descriptions: jobDescriptions }),
}

export const interviewAPI = {
  predict: (payload) => apiClient.post('/interview/predict', payload),
  evaluate: (payload) => apiClient.post('/interview/evaluate', payload),
  generateQuestions: (payload) => apiClient.post('/interview/generate-questions', payload),
}

export default apiClient

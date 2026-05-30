import axios from 'axios'

const AUTH_TOKEN_KEY = 'jobsync_access_token'
let authToken = typeof window !== 'undefined' ? localStorage.getItem(AUTH_TOKEN_KEY) : ''

function resolveApiBaseUrl() {
  const configured = String(import.meta.env.VITE_API_URL || '').trim()
  if (!configured) {
    return ''
  }

  if (!import.meta.env.PROD) {
    const localBackendUrls = ['http://localhost:8000', 'http://127.0.0.1:8000']
    if (localBackendUrls.includes(configured.replace(/\/$/, ''))) {
      return ''
    }
  }

  return configured.replace(/\/$/, '')
}

export const API_BASE_URL = resolveApiBaseUrl()

function resolveBackendRootUrl() {
  if (!API_BASE_URL) return ''
  return API_BASE_URL.replace(/\/api$/, '')
}

const apiClient = axios.create({
  baseURL: API_BASE_URL,
})

export function setAuthToken(token) {
  authToken = token || ''
  if (typeof window === 'undefined') return
  if (authToken) {
    localStorage.setItem(AUTH_TOKEN_KEY, authToken)
  } else {
    localStorage.removeItem(AUTH_TOKEN_KEY)
  }
}

export function getStoredAuthToken() {
  if (authToken) return authToken
  if (typeof window === 'undefined') return ''
  return localStorage.getItem(AUTH_TOKEN_KEY) || ''
}


export function clearAuthToken() {
  setAuthToken('')
}

apiClient.interceptors.request.use((config) => {
  if (!API_BASE_URL && typeof config.url === 'string' && config.url.startsWith('/') && !config.url.startsWith('/api/')) {
    config.url = `/api${config.url}`
  }
  const token = getStoredAuthToken()
  if (token) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${token}`
  }
  // Ensure cookies (HttpOnly refresh token) are sent for cross-site requests when needed
  config.withCredentials = true
  return config
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
  async (error) => {
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

    // Attempt a single refresh on 401 before invalidating auth
    const originalRequest = error.config
    if (status === 401 && !originalRequest?._retry) {
      originalRequest._retry = true
      try {
        // Call refresh endpoint which uses HttpOnly cookie
        const refreshResp = await axios.post(`${API_BASE_URL || ''}/auth/refresh`, {}, { withCredentials: true })
        const newAccess = refreshResp?.data?.access_token
        if (newAccess) {
          setAuthToken(newAccess)
          originalRequest.headers = originalRequest.headers || {}
          originalRequest.headers.Authorization = `Bearer ${newAccess}`
          return apiClient(originalRequest)
        }
      } catch (refreshErr) {
        // Fall through to invalidation
      }

      clearAuthToken()
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new Event('jobsync-auth-invalidated'))
      }
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

export const authAPI = {
  login: (payload) => apiClient.post('/auth/login', payload),
  signup: (payload) => apiClient.post('/auth/signup', payload),
  me: () => apiClient.get('/auth/me'),
  refresh: () => apiClient.post('/auth/refresh', {}, { withCredentials: true }),
  logout: () => apiClient.post('/auth/logout', {}, { withCredentials: true }),
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
  create: (payload) => apiClient.post('/profile', payload),
  exists: () => apiClient.get('/profile'),
  select: (id) => apiClient.post(`/profile/select/${id}`),
  selected: () => apiClient.get('/profile/selected'),
  get: (id) => apiClient.get(`/profile/${id}`),
  update: (id, payload) => apiClient.patch(`/profile/${id}`, payload),
  list: (page = 1, per_page = 10) => apiClient.get('/profile', { params: { page, per_page } }),
  delete: (id) => apiClient.delete(`/profile/${id}`),
}

export const apiActions = {
  match: (jobId) => apiClient.post(`/match/${jobId}`),
  buildResume: (jobId) => apiClient.post(`/build_resume/${jobId}`),
  downloadResumePdf: (jobId) => apiClient.get(`/build_resume/${jobId}/pdf`, { responseType: 'blob' }),
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

export const coverLetterAPI = {
  generate: (data) => apiClient.post('/cover-letter/generate', data),
  download: (data) => apiClient.post('/cover-letter/download', data, { responseType: 'blob' }),
}

export const settingsAPI = {
  listKeys: () => apiClient.get('/settings/keys'),
  saveKey: (payload) => apiClient.post('/settings/keys', payload),
  deleteKey: (provider) => apiClient.delete(`/settings/keys/${provider}`),
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

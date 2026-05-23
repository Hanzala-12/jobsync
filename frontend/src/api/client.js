import axios from 'axios'

const AUTH_TOKEN_KEY = 'jobsync_access_token'
const REFRESH_TOKEN_KEY = 'jobsync_refresh_token'
let authToken = typeof window !== 'undefined' ? localStorage.getItem(AUTH_TOKEN_KEY) : ''
let refreshToken = typeof window !== 'undefined' ? localStorage.getItem(REFRESH_TOKEN_KEY) : ''

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

export function setRefreshToken(token) {
  refreshToken = token || ''
  if (typeof window === 'undefined') return
  if (refreshToken) {
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken)
  } else {
    localStorage.removeItem(REFRESH_TOKEN_KEY)
  }
}

export function getStoredAuthToken() {
  if (authToken) return authToken
  if (typeof window === 'undefined') return ''
  return localStorage.getItem(AUTH_TOKEN_KEY) || ''
}

export function getStoredRefreshToken() {
  if (refreshToken) return refreshToken
  if (typeof window === 'undefined') return ''
  return localStorage.getItem(REFRESH_TOKEN_KEY) || ''
}

export function clearAuthToken() {
  setAuthToken('')
  setRefreshToken('')
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

    if (status === 401 && (getStoredAuthToken() || getStoredRefreshToken())) {
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
  refresh: (refresh_token) => apiClient.post('/auth/refresh', { refresh_token }),
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

export const studentAPI = {
  createProfile: (data) => apiClient.post('/api/student/profile', data),
  getCurrentProfile: () => apiClient.get('/api/student/profile'),
  listProfiles: () => apiClient.get('/api/student/profiles'),
  selectProfile: (profileId) => apiClient.post(`/api/student/profile/select/${profileId}`),
  getProfile: (id) => apiClient.get(`/api/student/profile/${id}`),
  updateProfile: (id, data) => apiClient.patch(`/api/student/profile/${id}`, data),
  deleteProfile: (id) => apiClient.delete(`/api/student/profile/${id}`),
  getRecommendations: (profileId, limit = 20, filters = {}) =>
    apiClient.post('/api/student/match/recommend', { student_profile_id: profileId, limit, ...filters }),
  getProgramMatch: (profileId, programId) =>
    apiClient.get(`/api/student/match/program/${programId}`, { params: { student_profile_id: profileId } }),
  getUniversitiesFilter: (params) => apiClient.get('/api/student/universities/filter', { params }),
  getUniversityDetail: (universityId) => apiClient.get(`/api/student/university/${universityId}/detail`),
  saveUniversity: (studentId, programId) => apiClient.post('/api/student/save', { student_id: studentId, program_id: programId }),
  getSavedUniversities: (studentId) => apiClient.get(`/api/student/saved/${studentId}`),
  applyProgram: (studentId, programId, notes = '') => apiClient.post('/api/student/apply', { student_id: studentId, program_id: programId, notes }),
  updateApplication: (applicationId, payload) => apiClient.put(`/api/student/applications/${applicationId}`, payload),
  getApplications: (studentId) => apiClient.get(`/api/student/applications/${studentId}`),
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

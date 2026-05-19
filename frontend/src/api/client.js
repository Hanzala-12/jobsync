import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export const resumeAPI = {
  analyze: (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return apiClient.post('/resume/analyze', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  reanalyze: (jobDescription) =>
    apiClient.post('/resume/reanalyze', { job_description: jobDescription }),
}

export const jobsAPI = {
  search: (query = 'software developer') => 
    apiClient.get('/jobs/search', { params: { query } }),
  
  match: (jobId) => 
    apiClient.get(`/jobs/${jobId}/match`),
}

export const applicationsAPI = {
  create: (data) => 
    apiClient.post('/applications/', data),
  
  list: (status = null) => 
    apiClient.get('/applications/', { params: status ? { status } : {} }),
  
  get: (appId) => 
    apiClient.get(`/applications/${appId}`),
  
  updateStatus: (appId, status) => 
    apiClient.patch(`/applications/${appId}/status`, { status }),
}

export const dailyScoutAPI = {
  run: (data) => apiClient.post('/scout/run', data),
  status: () => apiClient.get('/scout/status'),
}

export const coverLetterAPI = {
  generate: (data) => 
    apiClient.post('/cover-letter/generate', data),
}

export const intelligenceAPI = {
  skillGap: (jobDescriptions) => 
    apiClient.post('/intelligence/skill-gap', { job_descriptions: jobDescriptions }),
  
  interviewPrep: (role, jobDescription = null) => 
    apiClient.post('/intelligence/interview-prep', { 
      role, 
      job_description: jobDescription 
    }),
}

export default apiClient

// frontend/src/api/client.js
import { getStoredKey } from '../hooks/useAuth.js'

const BASE = import.meta.env.VITE_API_BASE || '/api'

function getApiKey() {
  return getStoredKey()
}

function getHeaders() {
  const h = { 'Content-Type': 'application/json' }
  const key = getApiKey()
  if (key) h['X-API-Key'] = key
  return h
}

async function request(method, path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: getHeaders(),
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`${res.status}: ${text}`)
  }
  if (res.status === 204) return null
  return res.json()
}

export const listJobs      = ()     => request('GET',  '/evidence/jobs/')
export const createJob     = (data) => request('POST', '/evidence/jobs/', data)
export const getJob        = (id)   => request('GET',  `/evidence/jobs/${id}/`)
export const dispatchJob   = (id)   => request('POST', `/evidence/jobs/${id}/dispatch/`)
export const listPapers    = (id)   => request('GET',  `/evidence/jobs/${id}/papers/`)
export const listClaims    = (id)   => request('GET',  `/evidence/jobs/${id}/claims/`)
export const listConflicts = (id)   => request('GET',  `/evidence/jobs/${id}/conflicts/`)
export const getReport     = (id)   => request('GET',  `/evidence/jobs/${id}/report/`)
export const getHealth     = ()     => request('GET',  '/health/')

export async function uploadPaper(jobId, file, title = '') {
  const form = new FormData()
  form.append('pdf_file', file)
  if (title) form.append('title', title)
  const h = {}
  const key = getApiKey()
  if (key) h['X-API-Key'] = key
  const res = await fetch(`${BASE}/evidence/jobs/${jobId}/papers/`, {
    method: 'POST',
    headers: h,
    body: form,
  })
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`)
  return res.json()
}

export async function deletePaper(paperId) {
  const h = {}
  const key = getApiKey()
  if (key) h['X-API-Key'] = key
  const res = await fetch(`${BASE}/evidence/papers/${paperId}/`, {
    method: 'DELETE',
    headers: h,
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`${res.status}: ${text}`)
  }
  return true
}

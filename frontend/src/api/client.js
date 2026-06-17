// frontend/src/api/client.js
const BASE    = import.meta.env.VITE_API_BASE || '/api'
const API_KEY = import.meta.env.VITE_API_KEY  || ''

function getHeaders(requiresAuth = false) {
  const h = { 'Content-Type': 'application/json' }
  if (requiresAuth && API_KEY) h['X-API-Key'] = API_KEY
  return h
}

async function request(method, path, body, requiresAuth = false) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: getHeaders(requiresAuth),
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`${res.status}: ${text}`)
  }
  if (res.status === 204) return null
  return res.json()
}

// ── Read-only (public, no auth) ───────────────────────────────────────────────
export const listJobs      = ()   => request('GET',  '/evidence/jobs/')
export const getJob        = (id) => request('GET',  `/evidence/jobs/${id}/`)
export const listPapers    = (id) => request('GET',  `/evidence/jobs/${id}/papers/`)
export const listClaims    = (id) => request('GET',  `/evidence/jobs/${id}/claims/`)
export const listConflicts = (id) => request('GET',  `/evidence/jobs/${id}/conflicts/`)
export const getReport     = (id) => request('GET',  `/evidence/jobs/${id}/report/`)
export const getHealth     = ()   => request('GET',  '/health/')

// ── Write (requires API key) ──────────────────────────────────────────────────
export const createJob   = (data) => request('POST', '/evidence/jobs/',              data, true)
export const dispatchJob     = (id) => request('POST', `/evidence/jobs/${id}/dispatch/`,      {}, true)
export const dispatchJobSync = (id) => request('POST', `/evidence/jobs/${id}/dispatch-sync/`, {}, true)

export async function uploadPaper(jobId, file, title = '') {
  const form = new FormData()
  form.append('pdf_file', file)
  if (title) form.append('title', title)
  const h = {}
  if (API_KEY) h['X-API-Key'] = API_KEY
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
  if (API_KEY) h['X-API-Key'] = API_KEY
  const res = await fetch(`${BASE}/evidence/papers/${paperId}/`, {
    method: 'DELETE',
    headers: h,
  })
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`)
  return true
}

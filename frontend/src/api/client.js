// frontend/src/api/client.js
const BASE = import.meta.env.VITE_API_BASE || '/api'

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!res.ok) {
    let msg = `HTTP ${res.status}`
    try {
      const body = await res.json()
      msg = body.detail || body.message || JSON.stringify(body)
    } catch (_) {}
    throw new Error(msg)
  }
  if (res.status === 204) return null
  return res.json()
}

export const listSuites = () => request('/evals/suites/')
export const getSuite = (id) => request(`/evals/suites/${id}/`)
export const createSuite = (data) => request('/evals/suites/', { method: 'POST', body: JSON.stringify(data) })
export const patchSuite = (id, data) => request(`/evals/suites/${id}/`, { method: 'PATCH', body: JSON.stringify(data) })

export const listCases = (suiteId) => request(`/evals/suites/${suiteId}/cases/`)
export const createCase = (suiteId, data) => request(`/evals/suites/${suiteId}/cases/`, { method: 'POST', body: JSON.stringify(data) })
export const deleteCase = (caseId) => request(`/evals/cases/${caseId}/`, { method: 'DELETE' })

export const createRun = (data) => request('/evals/runs/', { method: 'POST', body: JSON.stringify(data) })
export const getRun = (id) => request(`/evals/runs/${id}/`)
export const getRunResults = (id) => request(`/evals/runs/${id}/results/`)
export const getRegression = (id) => request(`/evals/runs/${id}/regression/`)
export const pinBaseline = (id) => request(`/evals/runs/${id}/pin-baseline/`, { method: 'POST' })

export const listModels = () => request('/evals/models/')
export const getHealth = () => request('/health/')

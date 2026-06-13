// frontend/src/pages/Suites.jsx
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useApi } from '../hooks/useApi.js'
import { listSuites, createSuite } from '../api/client.js'
import { MOCK_SUITES } from '../data/mockData.js'
import { MockBanner } from '../components/MockBanner.jsx'
import { LoadingState } from '../components/LoadingState.jsx'
import { ErrorState } from '../components/ErrorState.jsx'

function criteriaCount(rubric) {
  if (!rubric) return 0
  if (Array.isArray(rubric)) return rubric.length
  return Object.keys(rubric).length
}

function formatDate(iso) {
  if (!iso) return '--'
  return new Date(iso).toLocaleDateString()
}

export default function Suites() {
  const { data: suites, loading, error, isMock, refetch } = useApi(listSuites, MOCK_SUITES)

  const [showForm, setShowForm] = useState(false)
  const [name, setName] = useState('')
  const [rubricRaw, setRubricRaw] = useState([{ criterion: '', weight: '' }])
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState(null)

  function addRow() {
    setRubricRaw(r => [...r, { criterion: '', weight: '' }])
  }

  function updateRow(idx, field, val) {
    setRubricRaw(r => r.map((row, i) => i === idx ? { ...row, [field]: val } : row))
  }

  async function handleCreate(e) {
    e.preventDefault()
    setFormError(null)
    if (!name.trim()) { setFormError('Suite name is required.'); return }
    const rubric = {}
    for (const row of rubricRaw) {
      if (!row.criterion.trim()) continue
      const w = parseFloat(row.weight)
      if (isNaN(w) || w <= 0) { setFormError('All weights must be positive numbers.'); return }
      rubric[row.criterion.trim()] = w
    }
    if (Object.keys(rubric).length === 0) { setFormError('At least one rubric criterion is required.'); return }
    setSubmitting(true)
    try {
      await createSuite({ name: name.trim(), rubric })
      setName('')
      setRubricRaw([{ criterion: '', weight: '' }])
      setShowForm(false)
      refetch()
    } catch (err) {
      setFormError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-gauntlet-bg">
      {isMock && <MockBanner />}
      <div className="px-8 py-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-semibold text-gauntlet-text">Suites</h1>
            <p className="text-gauntlet-muted text-sm mt-1">Manage evaluation suites and rubrics</p>
          </div>
          <button
            onClick={() => setShowForm(v => !v)}
            className="bg-gauntlet-accent hover:bg-gauntlet-accent/80 text-white text-sm font-medium px-4 py-2 transition-colors"
          >
            + New Suite
          </button>
        </div>

        {showForm && (
          <div className="bg-gauntlet-surface border border-gauntlet-border p-6 mb-8">
            <h2 className="text-gauntlet-text font-medium text-sm mb-4">Create Suite</h2>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-gauntlet-muted text-xs font-mono mb-1">Suite Name</label>
                <input
                  type="text"
                  value={name}
                  onChange={e => setName(e.target.value)}
                  className="w-full bg-gauntlet-bg border border-gauntlet-border text-gauntlet-text text-sm px-3 py-2 focus:outline-none focus:border-gauntlet-accent"
                  placeholder="My Evaluation Suite"
                />
              </div>
              <div>
                <label className="block text-gauntlet-muted text-xs font-mono mb-1">Rubric Criteria</label>
                {rubricRaw.map((row, idx) => (
                  <div key={idx} className="flex gap-2 mb-2">
                    <input
                      type="text"
                      value={row.criterion}
                      onChange={e => updateRow(idx, 'criterion', e.target.value)}
                      className="flex-1 bg-gauntlet-bg border border-gauntlet-border text-gauntlet-text text-sm px-3 py-2 focus:outline-none focus:border-gauntlet-accent"
                      placeholder="criterion (e.g. accuracy)"
                    />
                    <input
                      type="number"
                      step="0.01"
                      value={row.weight}
                      onChange={e => updateRow(idx, 'weight', e.target.value)}
                      className="w-24 bg-gauntlet-bg border border-gauntlet-border text-gauntlet-text text-sm px-3 py-2 focus:outline-none focus:border-gauntlet-accent"
                      placeholder="weight"
                    />
                  </div>
                ))}
                <button type="button" onClick={addRow} className="text-gauntlet-accent text-xs font-mono hover:text-gauntlet-accent/80">
                  + add criterion
                </button>
              </div>
              {formError && <p className="text-gauntlet-danger text-xs font-mono">{formError}</p>}
              <div className="flex gap-3">
                <button
                  type="submit"
                  disabled={submitting}
                  className="bg-gauntlet-accent hover:bg-gauntlet-accent/80 disabled:opacity-50 text-white text-sm font-medium px-4 py-2 transition-colors"
                >
                  {submitting ? 'Creating...' : 'Create'}
                </button>
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  className="bg-gauntlet-border hover:bg-gauntlet-border/80 text-gauntlet-text text-sm font-medium px-4 py-2 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        {loading && <LoadingState rows={5} />}
        {error && <ErrorState message={error} onRetry={refetch} />}
        {!loading && !error && suites && (
          <div className="border border-gauntlet-border">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gauntlet-surface text-gauntlet-muted text-xs uppercase tracking-wider">
                  <th className="text-left px-6 py-3 border-b border-gauntlet-border">Name</th>
                  <th className="text-left px-6 py-3 border-b border-gauntlet-border">Version</th>
                  <th className="text-left px-6 py-3 border-b border-gauntlet-border">Criteria</th>
                  <th className="text-left px-6 py-3 border-b border-gauntlet-border">Created</th>
                  <th className="text-left px-6 py-3 border-b border-gauntlet-border">Actions</th>
                </tr>
              </thead>
              <tbody>
                {suites.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-6 py-8 text-center text-gauntlet-muted text-sm">
                      No suites yet. Create one above.
                    </td>
                  </tr>
                )}
                {suites.map(s => (
                  <tr key={s.id} className="border-b border-gauntlet-border hover:bg-gauntlet-surface/50">
                    <td className="px-6 py-4 text-gauntlet-text font-medium">{s.name}</td>
                    <td className="px-6 py-4 text-gauntlet-muted font-mono text-xs">v{s.version}</td>
                    <td className="px-6 py-4 text-gauntlet-muted font-mono text-xs">{criteriaCount(s.rubric)}</td>
                    <td className="px-6 py-4 text-gauntlet-muted text-xs">{formatDate(s.created_at)}</td>
                    <td className="px-6 py-4">
                      <Link
                        to={`/suites/${s.id}`}
                        className="text-gauntlet-accent hover:text-gauntlet-accent/80 text-xs font-mono"
                      >
                        Cases →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

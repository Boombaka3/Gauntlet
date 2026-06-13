// frontend/src/pages/Cases.jsx
import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useApi } from '../hooks/useApi.js'
import { listCases, getSuite, createCase, deleteCase } from '../api/client.js'
import { MOCK_CASES } from '../data/mockData.js'
import { MockBanner } from '../components/MockBanner.jsx'
import { LoadingState } from '../components/LoadingState.jsx'
import { ErrorState } from '../components/ErrorState.jsx'

function trunc(str, n) {
  if (!str) return '--'
  return str.length > n ? str.slice(0, n) + '…' : str
}

export default function Cases() {
  const { id } = useParams()
  const suiteId = parseInt(id, 10)

  const { data: suite } = useApi(() => getSuite(suiteId), null, [suiteId])
  const { data: cases, loading, error, isMock, refetch } = useApi(
    () => listCases(suiteId),
    MOCK_CASES,
    [suiteId]
  )

  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ name: '', system_prompt: '', user_prompt: '', expected_output: '' })
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState(null)
  const [deleting, setDeleting] = useState(null)

  function updateForm(field, val) {
    setForm(f => ({ ...f, [field]: val }))
  }

  async function handleCreate(e) {
    e.preventDefault()
    setFormError(null)
    if (!form.name.trim()) { setFormError('Name is required.'); return }
    if (!form.user_prompt.trim()) { setFormError('User prompt is required.'); return }
    setSubmitting(true)
    try {
      await createCase(suiteId, {
        name: form.name.trim(),
        system_prompt: form.system_prompt.trim(),
        user_prompt: form.user_prompt.trim(),
        expected_output: form.expected_output.trim() || null,
        tags: [],
      })
      setForm({ name: '', system_prompt: '', user_prompt: '', expected_output: '' })
      setShowForm(false)
      refetch()
    } catch (err) {
      setFormError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  async function handleDelete(caseId) {
    setDeleting(caseId)
    try {
      await deleteCase(caseId)
      refetch()
    } catch (err) {
      alert(`Delete failed: ${err.message}`)
    } finally {
      setDeleting(null)
    }
  }

  return (
    <div className="min-h-screen bg-gauntlet-bg">
      {isMock && <MockBanner />}
      <div className="px-8 py-8">
        <div className="flex items-center justify-between mb-2">
          <div>
            <div className="flex items-center gap-2 text-gauntlet-muted text-xs font-mono mb-1">
              <Link to="/suites" className="hover:text-gauntlet-accent">Suites</Link>
              <span>/</span>
              <span>{suite?.name || `Suite ${suiteId}`}</span>
            </div>
            <h1 className="text-2xl font-semibold text-gauntlet-text">Cases</h1>
          </div>
          <div className="flex gap-3">
            <Link
              to={`/runs/new?suite_id=${suiteId}`}
              className="bg-gauntlet-success hover:bg-gauntlet-success/80 text-white text-sm font-medium px-4 py-2 transition-colors"
            >
              Run this suite →
            </Link>
            <button
              onClick={() => setShowForm(v => !v)}
              className="bg-gauntlet-accent hover:bg-gauntlet-accent/80 text-white text-sm font-medium px-4 py-2 transition-colors"
            >
              + Add Case
            </button>
          </div>
        </div>

        {showForm && (
          <div className="bg-gauntlet-surface border border-gauntlet-border p-6 mb-8 mt-6">
            <h2 className="text-gauntlet-text font-medium text-sm mb-4">Add Case</h2>
            <form onSubmit={handleCreate} className="space-y-4">
              {[
                { field: 'name', label: 'Name', placeholder: 'Short description', multiline: false },
                { field: 'system_prompt', label: 'System Prompt', placeholder: 'You are a helpful assistant.', multiline: true },
                { field: 'user_prompt', label: 'User Prompt *', placeholder: 'What is 2+2?', multiline: true },
                { field: 'expected_output', label: 'Expected Output', placeholder: 'Leave blank for LLM judge scoring', multiline: true },
              ].map(({ field, label, placeholder, multiline }) => (
                <div key={field}>
                  <label className="block text-gauntlet-muted text-xs font-mono mb-1">{label}</label>
                  {multiline ? (
                    <textarea
                      rows={3}
                      value={form[field]}
                      onChange={e => updateForm(field, e.target.value)}
                      className="w-full bg-gauntlet-bg border border-gauntlet-border text-gauntlet-text text-sm px-3 py-2 focus:outline-none focus:border-gauntlet-accent resize-y font-mono"
                      placeholder={placeholder}
                    />
                  ) : (
                    <input
                      type="text"
                      value={form[field]}
                      onChange={e => updateForm(field, e.target.value)}
                      className="w-full bg-gauntlet-bg border border-gauntlet-border text-gauntlet-text text-sm px-3 py-2 focus:outline-none focus:border-gauntlet-accent"
                      placeholder={placeholder}
                    />
                  )}
                </div>
              ))}
              {formError && <p className="text-gauntlet-danger text-xs font-mono">{formError}</p>}
              <div className="flex gap-3">
                <button
                  type="submit"
                  disabled={submitting}
                  className="bg-gauntlet-accent hover:bg-gauntlet-accent/80 disabled:opacity-50 text-white text-sm font-medium px-4 py-2 transition-colors"
                >
                  {submitting ? 'Saving...' : 'Save Case'}
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

        <div className="mt-6">
          {loading && <LoadingState rows={5} />}
          {error && <ErrorState message={error} onRetry={refetch} />}
          {!loading && !error && cases && (
            <div className="border border-gauntlet-border">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gauntlet-surface text-gauntlet-muted text-xs uppercase tracking-wider">
                    <th className="text-left px-6 py-3 border-b border-gauntlet-border">Name</th>
                    <th className="text-left px-6 py-3 border-b border-gauntlet-border">System Prompt</th>
                    <th className="text-left px-6 py-3 border-b border-gauntlet-border">User Prompt</th>
                    <th className="text-left px-6 py-3 border-b border-gauntlet-border">Expected</th>
                    <th className="text-left px-6 py-3 border-b border-gauntlet-border">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {cases.length === 0 && (
                    <tr>
                      <td colSpan={5} className="px-6 py-8 text-center text-gauntlet-muted text-sm">
                        No cases yet. Add one above.
                      </td>
                    </tr>
                  )}
                  {cases.map(c => (
                    <tr key={c.id} className="border-b border-gauntlet-border hover:bg-gauntlet-surface/50">
                      <td className="px-6 py-4 text-gauntlet-text font-medium">{c.name}</td>
                      <td className="px-6 py-4 text-gauntlet-muted font-mono text-xs">{trunc(c.system_prompt, 50)}</td>
                      <td className="px-6 py-4 text-gauntlet-muted font-mono text-xs">{trunc(c.user_prompt, 50)}</td>
                      <td className="px-6 py-4 text-gauntlet-muted font-mono text-xs">{trunc(c.expected_output, 30)}</td>
                      <td className="px-6 py-4">
                        <button
                          onClick={() => handleDelete(c.id)}
                          disabled={deleting === c.id}
                          className="text-gauntlet-danger hover:text-gauntlet-danger/80 text-xs font-mono disabled:opacity-50"
                        >
                          {deleting === c.id ? 'Deleting…' : 'Delete'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

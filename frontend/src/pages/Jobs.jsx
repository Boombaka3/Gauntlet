// frontend/src/pages/Jobs.jsx
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useApi } from '../hooks/useApi.js'
import { listJobs, createJob } from '../api/client.js'
import { MOCK_JOBS } from '../data/mockData.js'
import { MockBanner } from '../components/MockBanner.jsx'
import { LoadingState } from '../components/LoadingState.jsx'
import { ErrorState } from '../components/ErrorState.jsx'
import StatusBadge from '../components/StatusBadge.jsx'

function fmtDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

export default function Jobs() {
  const { data: jobs, loading, error, isMock, refetch } = useApi(listJobs, MOCK_JOBS)
  const [showCreate, setShowCreate] = useState(false)
  const [nSamples, setNSamples] = useState(3)
  const [creating, setCreating] = useState(false)
  const navigate = useNavigate()

  async function handleCreate(e) {
    e.preventDefault()
    setCreating(true)
    try {
      const job = await createJob({ n_samples: nSamples })
      navigate(`/jobs/${job.id}`)
    } catch {
      refetch()
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#010102]">
      {isMock && <MockBanner />}

      <div className="px-8 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-xl font-semibold text-[#f7f8f8] tracking-tight">
            Analysis Jobs
          </h1>
          <button
            onClick={() => setShowCreate(v => !v)}
            className="px-3 py-2 bg-[#5e6ad2] hover:bg-[#828fff] text-white
                       text-sm rounded-[8px] transition-colors"
          >
            + New Analysis
          </button>
        </div>

        {/* Inline create form */}
        {showCreate && (
          <form onSubmit={handleCreate}
            className="bg-[#0f1011] border border-[#23252a] rounded-[12px] p-4 mb-6">
            <div className="mb-3">
              <label className="block text-[#8a8f98] text-xs uppercase tracking-wider mb-1">
                Consistency samples
              </label>
              <input
                type="number"
                min={1} max={10}
                value={nSamples}
                onChange={e => setNSamples(parseInt(e.target.value) || 1)}
                className="bg-[#141516] border border-[#23252a] rounded-[8px] px-3 py-2
                           text-[#f7f8f8] text-sm focus:outline-none focus:border-[#5e6ad2] w-24"
              />
            </div>
            <div className="flex gap-2">
              <button type="submit" disabled={creating}
                className="px-3 py-1.5 bg-[#5e6ad2] hover:bg-[#828fff] text-white
                           text-xs rounded-[8px] transition-colors disabled:opacity-50">
                {creating ? 'Creating…' : 'Create'}
              </button>
              <button type="button" onClick={() => setShowCreate(false)}
                className="px-3 py-1.5 text-[#f7f8f8] text-xs rounded-[8px]
                           hover:bg-[#141516] transition-colors">
                Cancel
              </button>
            </div>
          </form>
        )}

        {/* Stats row */}
        {jobs && jobs.length > 0 && !isMock && (() => {
          const totalJobs      = jobs.length
          const doneJobs       = jobs.filter(j => j.status === 'DONE').length
          const totalAnswers = jobs.reduce((s, j) => s + (j.answer_count || j.conflicts_count || 0), 0)
          const totalClaims = jobs.reduce((s, j) => s + (j.claim_count  || j.claims_count    || 0), 0)
          return (
            <div className="grid grid-cols-4 gap-3 mb-6">
              {[
                { label: 'Analyses',         value: totalJobs    },
                { label: 'Completed',        value: doneJobs     },
                { label: 'Claims extracted', value: totalClaims  },
                { label: 'Answers scored',   value: totalAnswers },
              ].map(s => (
                <div key={s.label}
                  className="bg-[#0f1011] border border-[#23252a] rounded-[8px] p-4">
                  <div className="text-[#f7f8f8] text-2xl font-semibold font-mono">{s.value}</div>
                  <div className="text-[#8a8f98] text-xs uppercase tracking-wider mt-1">{s.label}</div>
                </div>
              ))}
            </div>
          )
        })()}

        {loading && <LoadingState rows={4} />}
        {error && !isMock && <ErrorState message={error} onRetry={refetch} />}

        {jobs && jobs.length === 0 && !loading && (
          <div className="flex flex-col items-center justify-center py-32 gap-4">
            <div className="w-12 h-12 rounded-[12px] bg-[#0f1011] border border-[#23252a]
                            flex items-center justify-center">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
                   stroke="#5e6ad2" strokeWidth="1.5">
                <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586
                         a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19
                         a2 2 0 01-2 2z" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <p className="text-[#f7f8f8] text-sm font-medium">No analyses yet</p>
            <p className="text-[#8a8f98] text-xs text-center max-w-xs">
              Upload research papers to automatically detect
              contradictions across clinical trial publications.
            </p>
            <button onClick={() => navigate('/jobs/new')}
              className="mt-2 bg-[#5e6ad2] hover:bg-[#828fff] text-white
                         text-sm font-medium px-4 py-2 rounded-[8px] transition-colors">
              Start first analysis
            </button>
          </div>
        )}

        {jobs && jobs.length > 0 && (
          <table className="w-full">
            <thead>
              <tr className="bg-[#0f1011] border-y border-[#23252a]">
                {['#', 'Status', 'Papers', 'Claims', 'Answers', 'Created', 'Actions'].map(h => (
                  <th key={h}
                    className="text-[#8a8f98] text-[11px] font-medium uppercase tracking-wider
                               px-4 py-3 text-left">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {jobs.map(job => (
                <tr key={job.id}
                  className="border-b border-[#23252a] hover:bg-[#0f1011] transition-colors">
                  <td className="px-4 py-3 text-[#62666d] font-mono text-xs">{job.id}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={job.status} size="sm" />
                  </td>
                  <td className="px-4 py-3 text-[#d0d6e0] font-mono text-xs">
                    {job.paper_count ?? job.papers_count ?? 0}
                  </td>
                  <td className="px-4 py-3 text-[#d0d6e0] font-mono text-xs">
                    {job.claim_count ?? job.claims_count ?? 0}
                  </td>
                  <td className="px-4 py-3 text-[#d0d6e0] font-mono text-xs">
                    {job.answer_count ?? job.conflicts_count ?? 0}
                  </td>
                  <td className="px-4 py-3 text-[#8a8f98] text-xs">
                    {fmtDate(job.created_at)}
                  </td>
                  <td className="px-4 py-3 flex items-center gap-3">
                    <Link
                      to={`/jobs/${job.id}`}
                      className="text-[#5e6ad2] hover:text-[#828fff] text-xs transition-colors"
                    >
                      Papers →
                    </Link>
                    {job.status === 'DONE' && (
                      <Link
                        to={`/jobs/${job.id}/chat`}
                        className="text-[#8a8f98] hover:text-[#5e6ad2] text-xs font-mono transition-colors"
                      >
                        Chat →
                      </Link>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

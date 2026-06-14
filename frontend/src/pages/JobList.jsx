// frontend/src/pages/JobList.jsx
import { Link } from 'react-router-dom'
import { useApi } from '../hooks/useApi.js'
import { listJobs } from '../api/client.js'
import { MOCK_JOBS } from '../data/mockData.js'
import { MockBanner } from '../components/MockBanner.jsx'
import { LoadingState } from '../components/LoadingState.jsx'
import { ErrorState } from '../components/ErrorState.jsx'
import StatusBadge from '../components/StatusBadge.jsx'

function fmtDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

export default function JobList() {
  const { data: jobs, loading, error, isMock, refetch } = useApi(listJobs, MOCK_JOBS)

  return (
    <div className="min-h-screen bg-[#010102]">
      {isMock && <MockBanner />}

      <div className="px-8 py-8">
        <h1 className="text-xl font-semibold text-[#f7f8f8] tracking-tight mb-6">
          History
        </h1>

        {loading && <LoadingState rows={4} />}
        {error && !isMock && <ErrorState message={error} onRetry={refetch} />}

        {jobs && jobs.length === 0 && !loading && (
          <div className="text-center py-24">
            <p className="text-[#8a8f98] text-sm">No jobs in history yet.</p>
            <Link to="/jobs/new"
              className="inline-block mt-4 px-4 py-2 bg-[#5e6ad2] hover:bg-[#828fff]
                         text-white text-sm rounded-[8px] transition-colors">
              + New Analysis
            </Link>
          </div>
        )}

        {jobs && jobs.length > 0 && (
          <table className="w-full">
            <thead>
              <tr className="bg-[#0f1011] border-y border-[#23252a]">
                {['#', 'Status', 'Papers', 'Claims', 'Conflicts', 'Samples', 'Created', ''].map(h => (
                  <th key={h} className="text-[#8a8f98] text-[11px] font-medium uppercase
                                         tracking-wider px-4 py-3 text-left">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[...jobs].sort((a, b) => b.id - a.id).map(job => (
                <tr key={job.id}
                  className="border-b border-[#23252a] hover:bg-[#0f1011] transition-colors">
                  <td className="px-4 py-3 text-[#62666d] font-mono text-xs">{job.id}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={job.status} size="sm" />
                  </td>
                  <td className="px-4 py-3 text-[#d0d6e0] font-mono text-xs">{job.papers_count ?? 0}</td>
                  <td className="px-4 py-3 text-[#d0d6e0] font-mono text-xs">{job.claims_count ?? 0}</td>
                  <td className="px-4 py-3 text-[#d0d6e0] font-mono text-xs">{job.conflicts_count ?? 0}</td>
                  <td className="px-4 py-3 text-[#d0d6e0] font-mono text-xs">{job.n_samples}</td>
                  <td className="px-4 py-3 text-[#8a8f98] text-xs">{fmtDate(job.created_at)}</td>
                  <td className="px-4 py-3">
                    <Link to={`/jobs/${job.id}/conflicts`}
                      className="text-[#5e6ad2] hover:text-[#828fff] text-xs transition-colors">
                      Conflicts →
                    </Link>
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

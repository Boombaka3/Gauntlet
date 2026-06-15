// frontend/src/pages/Conflicts.jsx
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useApi } from '../hooks/useApi.js'
import { listConflicts, getJob } from '../api/client.js'
import { MOCK_CONFLICTS } from '../data/mockData.js'
import { MockBanner } from '../components/MockBanner.jsx'
import { LoadingState } from '../components/LoadingState.jsx'
import { ErrorState } from '../components/ErrorState.jsx'
import { ConflictBadge } from '../components/ConflictBadge.jsx'
import { ConfidenceBar } from '../components/ConfidenceBar.jsx'

function SeverityDots({ severity, verdict }) {
  const color =
    verdict === 'CONTRADICTS' ? '#EF4444' :
    verdict === 'SUPPORTS'    ? '#27a644' :
    verdict === 'PARTIAL'     ? '#F59E0B' : '#8a8f98'
  return (
    <div className="flex gap-0.5">
      {[1, 2, 3, 4, 5].map(i => (
        <span
          key={i}
          className="w-1.5 h-1.5 rounded-full"
          style={{ backgroundColor: i <= (severity || 0) ? color : '#23252a' }}
        />
      ))}
    </div>
  )
}

export default function Conflicts() {
  const { id } = useParams()
  const { data: conflicts, loading, error, isMock, refetch } = useApi(
    () => listConflicts(id), MOCK_CONFLICTS, [id]
  )
  const { data: job } = useApi(() => getJob(id), null, [id])
  const [expandedId, setExpandedId] = useState(null)

  const nSamples = job?.n_samples ?? '?'
  const contradictions = conflicts?.filter(c => c.verdict === 'CONTRADICTS').length ?? 0
  const supports = conflicts?.filter(c => c.verdict === 'SUPPORTS').length ?? 0
  const avgConf = conflicts?.length
    ? (conflicts.reduce((s, c) => s + (c.final_confidence ?? 0), 0) / conflicts.length).toFixed(2)
    : '—'
  const allErrors = conflicts?.flatMap(c => c.error_types || []) ?? []
  const uniqueErrors = [...new Set(allErrors)].length

  return (
    <div className="min-h-screen bg-[#010102]">
      {isMock && <MockBanner />}

      <div className="px-8 py-8">
        <Link to={`/jobs/${id}/status`}
          className="text-[#8a8f98] text-xs hover:text-[#5e6ad2] transition-colors mb-4 block">
          ← Job #{id}
        </Link>

        <h1 className="text-xl font-semibold text-[#f7f8f8] mb-3 tracking-tight">
          Conflict Report
        </h1>

        <p className="text-[#8a8f98] text-sm mb-6 max-w-2xl">
          Each row shows a conflict detected between claims from different papers.
          Confidence combines consistency across {nSamples} independent judgments
          and faithfulness of each claim to its source sentence.
        </p>

        {/* Summary stat row */}
        {conflicts && conflicts.length > 0 && (
          <p className="text-[#d0d6e0] text-sm font-mono border-b border-[#23252a] pb-3 mb-4">
            {conflicts.length} pair{conflicts.length !== 1 ? 's' : ''} analyzed —{' '}
            {contradictions} contradiction{contradictions !== 1 ? 's' : ''},{' '}
            {supports} agreement{supports !== 1 ? 's' : ''}
          </p>
        )}

        {/* Summary cards */}
        {conflicts && (
          <div className="grid grid-cols-4 gap-3 mb-6">
            {[
              { label: 'Total pairs',     value: conflicts.length },
              { label: 'Contradictions',  value: contradictions },
              { label: 'Avg confidence',  value: avgConf },
              { label: 'Error types',     value: uniqueErrors },
            ].map(s => (
              <div key={s.label}
                className="bg-[#0f1011] border border-[#23252a] rounded-[8px] p-4">
                <div className="text-[#f7f8f8] text-xl font-semibold font-mono">{s.value}</div>
                <div className="text-[#8a8f98] text-xs mt-1">{s.label}</div>
              </div>
            ))}
          </div>
        )}

        {loading && <LoadingState rows={5} />}
        {error && !isMock && <ErrorState message={error} onRetry={refetch} />}

        {conflicts && conflicts.length === 0 && !loading && (
          <p className="text-[#8a8f98] text-sm py-8 text-center">
            No conflicts detected yet.
          </p>
        )}

        {conflicts && conflicts.length > 0 && (
          <table className="w-full">
            <thead>
              <tr className="bg-[#0f1011] border-y border-[#23252a]">
                {['Verdict', 'Type', 'Severity', 'Confidence', 'Reasoning', 'Error Types'].map(h => (
                  <th key={h} className="text-[#8a8f98] text-[11px] font-medium uppercase
                                         tracking-wider px-4 py-3 text-left">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {conflicts.map(c => (
                <>
                  <tr key={c.id}
                    className="border-b border-[#23252a] hover:bg-[#0f1011] transition-colors cursor-pointer"
                    onClick={() => setExpandedId(expandedId === c.id ? null : c.id)}>
                    <td className="px-4 py-3">
                      <ConflictBadge verdict={c.verdict} />
                    </td>
                    <td className="px-4 py-3 text-[#8a8f98] text-xs font-mono">
                      {c.conflict_type || '—'}
                    </td>
                    <td className="px-4 py-3">
                      <SeverityDots severity={c.severity} verdict={c.verdict} />
                    </td>
                    <td className="px-4 py-3">
                      <ConfidenceBar score={c.final_confidence} />
                    </td>
                    <td className="px-4 py-3 text-[#d0d6e0] text-xs max-w-xs truncate">
                      {c.reasoning || '—'}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {(c.error_types || []).map(et => (
                          <span key={et}
                            className="rounded-[4px] bg-[#141516] border border-[#23252a]
                                       text-[#8a8f98] text-[10px] font-mono px-1.5 py-0.5">
                            {et}
                          </span>
                        ))}
                        {!c.error_types?.length && (
                          <span className="text-[#62666d] text-[10px] font-mono">—</span>
                        )}
                      </div>
                    </td>
                  </tr>
                  {expandedId === c.id && (
                    <tr key={`${c.id}-expanded`} className="border-b border-[#23252a] bg-[#0f1011]">
                      <td colSpan={6} className="px-4 py-3 text-[#d0d6e0] text-xs font-mono">
                        {c.reasoning}
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

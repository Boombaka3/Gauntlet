// frontend/src/pages/Results.jsx
import { useParams, Link } from 'react-router-dom'
import { useApi } from '../hooks/useApi.js'
import { getRunResults } from '../api/client.js'
import { MOCK_RESULTS } from '../data/mockData.js'
import { MockBanner } from '../components/MockBanner.jsx'
import { LoadingState } from '../components/LoadingState.jsx'
import { ErrorState } from '../components/ErrorState.jsx'
import ScoreBar from '../components/ScoreBar.jsx'
import ModelCompare from '../components/ModelCompare.jsx'
import DeltaBadge from '../components/DeltaBadge.jsx'

function StatCard({ label, value }) {
  return (
    <div className="bg-gauntlet-surface border border-gauntlet-border px-5 py-4">
      <div className="text-2xl font-bold text-gauntlet-text font-mono">{value}</div>
      <div className="text-gauntlet-muted text-xs mt-1">{label}</div>
    </div>
  )
}

export default function Results() {
  const { id } = useParams()
  const { data: results, loading, error, isMock, refetch } = useApi(
    () => getRunResults(id),
    MOCK_RESULTS,
    [id]
  )

  const passed = results ? results.filter(r => r.passed === true).length : 0
  const total = results ? results.length : 0
  const passRate = total > 0 ? Math.round((passed / total) * 100) + '%' : '--'
  const overallVals = results ? results.map(r => r.overall).filter(v => v != null) : []
  const avgScore = overallVals.length > 0
    ? (overallVals.reduce((a, b) => a + b, 0) / overallVals.length).toFixed(2)
    : '--'
  const modelCount = results
    ? [...new Set(results.map(r => r.model_id || r.model_run_id))].length
    : '--'

  const hasRegression = results && results.some(r => r.regression_delta != null)

  const byCaseId = {}
  if (results) {
    for (const r of results) {
      const key = r.prompt_case_id
      if (!byCaseId[key]) byCaseId[key] = []
      byCaseId[key].push(r)
    }
  }

  return (
    <div className="min-h-screen bg-gauntlet-bg">
      {isMock && <MockBanner />}
      <div className="px-8 py-8">
        <div className="mb-8">
          <Link to={`/runs/${id}`} className="text-gauntlet-muted hover:text-gauntlet-text text-sm font-mono">
            ← Run #{id}
          </Link>
          <h1 className="text-2xl font-semibold text-gauntlet-text mt-3">Results</h1>
        </div>

        {loading && <LoadingState rows={6} />}
        {error && <ErrorState message={error} onRetry={refetch} />}

        {!loading && !error && results && (
          <div className="space-y-10">
            {/* Stats grid */}
            <div className="grid grid-cols-4 gap-4">
              <StatCard label="Total results" value={total} />
              <StatCard label="Models tested" value={modelCount} />
              <StatCard label="Avg score" value={avgScore} />
              <StatCard label="Pass rate" value={passRate} />
            </div>

            {/* Model comparison */}
            {results.length > 0 && (
              <div className="bg-gauntlet-surface border border-gauntlet-border p-6">
                <ModelCompare results={results} />
              </div>
            )}

            {/* Results by case */}
            {Object.entries(byCaseId).map(([caseId, rows]) => (
              <div key={caseId}>
                <div className="text-gauntlet-muted text-xs font-mono uppercase tracking-wider mb-3">
                  Case #{caseId}
                </div>
                <div className="border border-gauntlet-border">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="bg-gauntlet-surface text-gauntlet-muted text-xs uppercase tracking-wider">
                        <th className="text-left px-6 py-3 border-b border-gauntlet-border">Model</th>
                        <th className="text-left px-6 py-3 border-b border-gauntlet-border">Score</th>
                        <th className="text-left px-6 py-3 border-b border-gauntlet-border">Passed</th>
                        <th className="text-left px-6 py-3 border-b border-gauntlet-border">Latency</th>
                        <th className="text-left px-6 py-3 border-b border-gauntlet-border">Delta</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map(r => (
                        <tr key={r.id} className="border-b border-gauntlet-border hover:bg-gauntlet-surface/50">
                          <td className="px-6 py-3 font-mono text-sm text-gauntlet-text">
                            {r.model_id || `run #${r.model_run_id}`}
                          </td>
                          <td className="px-6 py-3">
                            <ScoreBar value={r.overall} />
                          </td>
                          <td className="px-6 py-3 font-bold text-base">
                            {r.passed === null || r.passed === undefined ? (
                              <span className="text-gauntlet-muted text-xs">--</span>
                            ) : r.passed ? (
                              <span className="text-gauntlet-success">✓</span>
                            ) : (
                              <span className="text-gauntlet-danger">✗</span>
                            )}
                          </td>
                          <td className="px-6 py-3 font-mono text-xs text-gauntlet-muted">
                            {r.latency_ms != null ? `${r.latency_ms}ms` : '--'}
                          </td>
                          <td className="px-6 py-3">
                            <DeltaBadge delta={r.regression_delta} />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ))}

            {/* Regression section */}
            {hasRegression && (
              <div className="bg-gauntlet-surface border border-gauntlet-border p-6">
                <div className="text-gauntlet-text font-medium text-sm mb-4">Regression Summary</div>
                <div className="grid grid-cols-3 gap-4 text-xs font-mono">
                  <div className="bg-gauntlet-bg border border-gauntlet-border p-3">
                    <div className="text-gauntlet-success text-lg font-bold">
                      {results.filter(r => r.regression_delta > 0).length}
                    </div>
                    <div className="text-gauntlet-muted mt-1">Improved</div>
                  </div>
                  <div className="bg-gauntlet-bg border border-gauntlet-border p-3">
                    <div className="text-gauntlet-danger text-lg font-bold">
                      {results.filter(r => r.regression_delta < 0).length}
                    </div>
                    <div className="text-gauntlet-muted mt-1">Regressed</div>
                  </div>
                  <div className="bg-gauntlet-bg border border-gauntlet-border p-3">
                    <div className="text-gauntlet-muted text-lg font-bold">
                      {results.filter(r => r.regression_delta === 0 || r.regression_delta == null).length}
                    </div>
                    <div className="text-gauntlet-muted mt-1">Unchanged / N/A</div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

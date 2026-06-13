// frontend/src/components/ModelCompare.jsx
import ScoreBar from './ScoreBar.jsx'
import DeltaBadge from './DeltaBadge.jsx'

export default function ModelCompare({ results }) {
  const sorted = [...results].sort((a, b) => {
    const av = a.overall ?? -1
    const bv = b.overall ?? -1
    return bv - av
  })

  return (
    <div>
      <div className="text-gauntlet-text font-medium text-sm mb-3">Model Comparison</div>
      <table className="w-full text-sm border border-gauntlet-border">
        <thead>
          <tr className="bg-gauntlet-surface text-gauntlet-muted text-xs uppercase tracking-wider">
            <th className="text-left px-4 py-3 border-b border-gauntlet-border">Rank</th>
            <th className="text-left px-4 py-3 border-b border-gauntlet-border">Model</th>
            <th className="text-left px-4 py-3 border-b border-gauntlet-border">Score</th>
            <th className="text-left px-4 py-3 border-b border-gauntlet-border">Passed</th>
            <th className="text-left px-4 py-3 border-b border-gauntlet-border">Latency</th>
            <th className="text-left px-4 py-3 border-b border-gauntlet-border">Delta</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((r, idx) => (
            <tr key={r.id} className="hover:bg-gauntlet-surface/50 border-b border-gauntlet-border">
              <td className="px-4 py-3 text-gauntlet-muted font-mono text-xs">#{idx + 1}</td>
              <td className="px-4 py-3 font-mono text-sm text-gauntlet-text">
                {r.model_id || `run #${r.model_run_id}`}
              </td>
              <td className="px-4 py-3">
                <ScoreBar value={r.overall} />
              </td>
              <td className="px-4 py-3 text-base font-bold">
                {r.passed === null || r.passed === undefined ? (
                  <span className="text-gauntlet-muted text-xs">--</span>
                ) : r.passed ? (
                  <span className="text-gauntlet-success">✓</span>
                ) : (
                  <span className="text-gauntlet-danger">✗</span>
                )}
              </td>
              <td className="px-4 py-3 font-mono text-xs text-gauntlet-muted">
                {r.latency_ms != null ? `${r.latency_ms}ms` : '--'}
              </td>
              <td className="px-4 py-3">
                <DeltaBadge delta={r.regression_delta} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// frontend/src/components/ConfidenceBar.jsx
export function ConfidenceBar({ score, n_samples = null }) {
  if (score === null || score === undefined) {
    return <span className="text-[#62666d] font-mono text-xs">—</span>
  }

  const pct = Math.round(score * 100)
  const fillColor =
    score >= 0.8 ? 'bg-[#27a644]' :
    score >= 0.5 ? 'bg-[#F59E0B]' :
    'bg-[#EF4444]'

  return (
    <div className="min-w-[72px]">
      <div className="w-full h-1.5 bg-[#23252a]">
        <div
          className={`h-1.5 transition-all duration-300 ${fillColor}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="flex items-center gap-2 mt-1">
        <span className="text-xs font-mono text-[#8a8f98]">{pct}%</span>
        {n_samples != null && (
          <span className="text-[10px] font-mono text-[#62666d]">n={n_samples}</span>
        )}
      </div>
    </div>
  )
}

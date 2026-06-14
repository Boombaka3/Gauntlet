// frontend/src/components/ScoreBar.jsx
export default function ScoreBar({ value, showLabel = true }) {
  if (value === null || value === undefined) {
    return <span className="text-[#62666d] font-mono text-xs">—</span>
  }

  const pct = Math.min(100, Math.round(value * 100))
  const fillColor =
    value >= 0.8 ? 'bg-[#27a644]' :
    value >= 0.5 ? 'bg-[#F59E0B]' :
    'bg-[#EF4444]'

  return (
    <div className="min-w-[80px]">
      <div className="w-full h-1.5 bg-[#23252a]">
        <div
          className={`h-1.5 transition-all duration-300 ${fillColor}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      {showLabel && (
        <div className="text-xs font-mono mt-1 text-[#8a8f98]">
          {value.toFixed(2)}
        </div>
      )}
    </div>
  )
}

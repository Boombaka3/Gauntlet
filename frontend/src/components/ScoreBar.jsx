// frontend/src/components/ScoreBar.jsx
export default function ScoreBar({ value, showLabel = true }) {
  if (value === null || value === undefined) {
    return <span className="text-gauntlet-muted font-mono text-xs">N/A</span>
  }

  const pct = Math.min(100, Math.round(value * 100))
  const fillColor =
    value >= 0.8 ? 'bg-gauntlet-success' :
    value >= 0.5 ? 'bg-gauntlet-warning' :
    'bg-gauntlet-danger'
  const labelColor =
    value >= 0.8 ? 'text-gauntlet-success' :
    value >= 0.5 ? 'text-gauntlet-warning' :
    'text-gauntlet-danger'

  return (
    <div className="min-w-[80px]">
      <div className="w-full h-1.5 bg-gauntlet-border">
        <div className={`h-1.5 ${fillColor}`} style={{ width: `${pct}%` }} />
      </div>
      {showLabel && (
        <div className={`text-xs font-mono mt-0.5 ${labelColor}`}>
          {value.toFixed(2)}
        </div>
      )}
    </div>
  )
}

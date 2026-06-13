// frontend/src/components/ProgressBar.jsx
export default function ProgressBar({ current, total, animated = true }) {
  const pct = total > 0 ? Math.min(100, Math.round((current / total) * 100)) : 0
  return (
    <div>
      <div className="text-gauntlet-muted text-xs font-mono mb-1">
        {current} / {total} complete
      </div>
      <div className="w-full h-1.5 bg-gauntlet-border">
        <div
          className={`h-1.5 bg-gauntlet-accent ${animated ? 'transition-all duration-500' : ''}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}

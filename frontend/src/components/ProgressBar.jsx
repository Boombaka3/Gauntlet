// frontend/src/components/ProgressBar.jsx
export default function ProgressBar({ current, total, animated = true }) {
  const pct = total > 0 ? Math.min(100, (current / total) * 100) : 0
  return (
    <div>
      <div className="text-[#8a8f98] text-xs font-mono mb-1">
        {current} / {total}
      </div>
      <div className="w-full h-1 bg-[#23252a]">
        <div
          className={`h-1 bg-[#5e6ad2] ${animated ? 'transition-all duration-500' : ''}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}

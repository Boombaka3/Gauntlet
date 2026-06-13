// frontend/src/components/MockBanner.jsx
export function MockBanner() {
  return (
    <div className="w-full bg-gauntlet-warning/10 border-b border-gauntlet-warning/30
                    px-6 py-2 flex items-center gap-2">
      <span className="w-2 h-2 rounded-full bg-gauntlet-warning animate-pulse" />
      <span className="text-gauntlet-warning text-xs font-mono">
        DEMO MODE — API unavailable. Showing sample data.
      </span>
    </div>
  )
}

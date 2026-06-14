// frontend/src/components/MockBanner.jsx
export function MockBanner() {
  return (
    <div className="w-full bg-[#141516] border-b border-[#34343a] px-6 py-2 flex items-center gap-2">
      <span className="w-1.5 h-1.5 rounded-full bg-[#F59E0B] animate-pulse flex-shrink-0" />
      <span className="text-[#d0d6e0] text-xs font-mono">
        DEMO MODE — API unavailable. Showing sample data.
      </span>
    </div>
  )
}

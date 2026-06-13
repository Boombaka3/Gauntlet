// frontend/src/components/LoadingState.jsx
export function LoadingState({ rows = 5 }) {
  return (
    <div className="space-y-2 animate-pulse">
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="h-10 bg-gauntlet-surface border border-gauntlet-border"
        />
      ))}
    </div>
  )
}

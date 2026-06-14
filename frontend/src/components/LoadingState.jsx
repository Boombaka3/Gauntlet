// frontend/src/components/LoadingState.jsx
export function LoadingState({ rows = 5 }) {
  return (
    <div className="space-y-px animate-pulse">
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="h-10 bg-[#0f1011] border-b border-[#23252a]"
          style={{ opacity: 1 - i * 0.15 }}
        />
      ))}
    </div>
  )
}

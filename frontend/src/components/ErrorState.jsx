// frontend/src/components/ErrorState.jsx
export function ErrorState({ message, onRetry }) {
  return (
    <div className="flex flex-col items-center justify-center py-24 gap-3">
      <div className="w-8 h-8 rounded-[8px] bg-[#141516] border border-[#34343a]
                      flex items-center justify-center text-[#EF4444] text-sm font-mono">
        !
      </div>
      <p className="text-[#f7f8f8] text-sm font-medium">Something went wrong</p>
      <p className="text-[#8a8f98] text-xs font-mono max-w-xs text-center">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-2 px-3 py-1.5 bg-[#0f1011] border border-[#23252a]
                     hover:border-[#5e6ad2] text-[#d0d6e0] hover:text-[#f7f8f8]
                     text-xs rounded-[8px] transition-colors font-mono"
        >
          Try again
        </button>
      )}
    </div>
  )
}

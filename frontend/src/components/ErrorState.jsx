// frontend/src/components/ErrorState.jsx
export function ErrorState({ message, onRetry }) {
  return (
    <div className="flex flex-col items-center justify-center py-24 gap-4">
      <div className="text-gauntlet-danger text-4xl font-mono font-bold">!</div>
      <p className="text-gauntlet-text font-medium">Something went wrong</p>
      <p className="text-gauntlet-muted text-sm font-mono max-w-md text-center break-all">
        {message}
      </p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-2 px-4 py-2 border border-gauntlet-border
                     text-gauntlet-muted hover:text-gauntlet-text
                     hover:border-gauntlet-accent text-sm transition-colors"
        >
          Try again
        </button>
      )}
    </div>
  )
}

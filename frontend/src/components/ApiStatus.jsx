// frontend/src/components/ApiStatus.jsx
import { useState, useEffect } from 'react'

export function ApiStatus() {
  const [online, setOnline] = useState(null)

  useEffect(() => {
    const check = () =>
      fetch('/api/health/')
        .then(r => setOnline(r.ok))
        .catch(() => setOnline(false))

    check()
    const id = setInterval(check, 30000)
    return () => clearInterval(id)
  }, [])

  if (online === null) return null

  return (
    <div className="fixed bottom-0 left-0 right-0 h-6
                    bg-gauntlet-surface border-t border-gauntlet-border
                    flex items-center px-4 gap-2 z-50">
      <span className={`w-1.5 h-1.5 rounded-full ${
        online ? 'bg-gauntlet-success' : 'bg-gauntlet-danger animate-pulse'
      }`} />
      <span className="text-gauntlet-muted text-xs font-mono">
        {online ? 'API connected' : 'API offline — showing cached data'}
      </span>
    </div>
  )
}

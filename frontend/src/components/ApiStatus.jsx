// frontend/src/components/ApiStatus.jsx
import { useState, useEffect } from 'react'

const MODEL = import.meta.env.VITE_NAVIGATOR_MODEL || 'llama-3.3-70b-instruct'

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
                    bg-[#010102] border-t border-[#23252a]
                    flex items-center px-4 gap-2 z-50">
      <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
        online ? 'bg-[#27a644]' : 'bg-[#EF4444] animate-pulse'
      }`} />
      <span className="text-[#62666d] text-xs font-mono">
        {online ? 'NaviGator API connected' : 'API offline — showing cached data'}
      </span>
      {online && (
        <span className="text-[#62666d] text-xs font-mono ml-auto">
          {MODEL} · HiPerGator
        </span>
      )}
    </div>
  )
}

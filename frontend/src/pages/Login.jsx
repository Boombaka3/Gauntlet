// frontend/src/pages/Login.jsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

export default function Login() {
  const [token, setToken]     = useState('')
  const [error, setError]     = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  async function handleSubmit() {
    if (!token.trim()) {
      setError('Enter your access token')
      return
    }
    setLoading(true)
    setError('')
    try {
      const res = await fetch('/api/evidence/jobs/', {
        headers: { 'Host': 'demo.localhost', 'X-API-Key': token.trim() }
      })
      if (res.status === 401) {
        setError('Invalid token')
        setLoading(false)
        return
      }
      sessionStorage.setItem('et_api_key', token.trim())
      navigate('/jobs')
    } catch {
      setError('Cannot reach API — check backend is running')
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#010102] flex items-center justify-center">
      <div className="w-full max-w-sm">

        <div className="mb-8 text-center">
          <p className="text-[#f7f8f8] font-mono font-bold text-lg tracking-widest">
            EVIDENCE
          </p>
          <p className="text-[#8a8f98] text-xs mt-1">
            Claim Conflict Detection
          </p>
        </div>

        <div className="bg-[#0f1011] border border-[#23252a] rounded-[12px] p-6">
          <p className="text-[#d0d6e0] text-sm font-medium mb-4">
            Access Token
          </p>

          <input
            type="password"
            value={token}
            onChange={e => setToken(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSubmit()}
            placeholder="Paste your API key"
            className="w-full bg-[#141516] border border-[#23252a] rounded-[8px]
                       px-3 py-2.5 text-[#f7f8f8] text-sm font-mono
                       placeholder-[#62666d]
                       focus:outline-none focus:border-[#5e6ad2]
                       transition-colors mb-3"
          />

          {error && (
            <p className="text-[#EF4444] text-xs font-mono mb-3">{error}</p>
          )}

          <button
            onClick={handleSubmit}
            disabled={loading}
            className="w-full bg-[#5e6ad2] hover:bg-[#828fff] disabled:opacity-50
                       text-white text-sm font-medium py-2.5 rounded-[8px]
                       transition-colors"
          >
            {loading ? 'Verifying...' : 'Access Dashboard'}
          </button>
        </div>

        <p className="text-[#62666d] text-xs text-center mt-4 font-mono">
          EvidenceTrace v1.0.0
        </p>
      </div>
    </div>
  )
}

// frontend/src/pages/NewJob.jsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createJob } from '../api/client.js'

const SAMPLE_OPTIONS = [
  { value: 1, label: '1 sample',   desc: 'Fast, single run' },
  { value: 3, label: '3 samples',  desc: 'Balanced (recommended)' },
  { value: 5, label: '5 samples',  desc: 'High confidence, slower' },
]

export default function NewJob() {
  const [nSamples, setNSamples] = useState(3)
  const [creating, setCreating] = useState(false)
  const [err, setErr] = useState(null)
  const navigate = useNavigate()

  async function handleSubmit(e) {
    e.preventDefault()
    setCreating(true)
    setErr(null)
    try {
      const job = await createJob({ n_samples: nSamples })
      navigate(`/jobs/${job.id}`)
    } catch (e) {
      setErr(e.message)
      setCreating(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#010102] flex items-start justify-center pt-20 px-4">
      <div className="w-full max-w-md">
        <h1 className="text-xl font-semibold text-[#f7f8f8] mb-6 tracking-tight">
          New Analysis
        </h1>

        <form onSubmit={handleSubmit}
          className="bg-[#0f1011] border border-[#23252a] rounded-[12px] p-6">

          <label className="block text-[#8a8f98] text-xs uppercase tracking-wider mb-3">
            Consistency samples
          </label>

          <div className="space-y-2 mb-6">
            {SAMPLE_OPTIONS.map(opt => (
              <button
                key={opt.value}
                type="button"
                onClick={() => setNSamples(opt.value)}
                className={`w-full text-left p-3 rounded-[8px] border transition-colors ${
                  nSamples === opt.value
                    ? 'border-[#5e6ad2] bg-[#141516]'
                    : 'border-[#23252a] hover:border-[#34343a]'
                }`}
              >
                <div className="text-[#f7f8f8] text-sm font-medium">{opt.label}</div>
                <div className="text-[#8a8f98] text-xs mt-0.5">{opt.desc}</div>
              </button>
            ))}
          </div>

          {err && (
            <p className="text-[#EF4444] text-xs font-mono mb-4">{err}</p>
          )}

          <button
            type="submit"
            disabled={creating}
            className="w-full py-2 bg-[#5e6ad2] hover:bg-[#828fff] text-white
                       text-sm rounded-[8px] transition-colors disabled:opacity-50"
          >
            {creating ? 'Creating…' : 'Create Job'}
          </button>
        </form>
      </div>
    </div>
  )
}

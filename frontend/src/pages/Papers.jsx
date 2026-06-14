// frontend/src/pages/Papers.jsx
import { useState, useRef } from 'react'
import { Link, useParams, useNavigate } from 'react-router-dom'
import { useApi } from '../hooks/useApi.js'
import { listPapers, uploadPaper, dispatchJob } from '../api/client.js'
import { MOCK_PAPERS } from '../data/mockData.js'
import { MockBanner } from '../components/MockBanner.jsx'
import { LoadingState } from '../components/LoadingState.jsx'
import { ErrorState } from '../components/ErrorState.jsx'

function fmtDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

export default function Papers() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { data: papers, loading, error, isMock, refetch } = useApi(
    () => listPapers(id), MOCK_PAPERS, [id]
  )
  const [title, setTitle] = useState('')
  const [uploading, setUploading] = useState(false)
  const [dispatching, setDispatching] = useState(false)
  const fileRef = useRef(null)

  async function handleUpload(e) {
    e.preventDefault()
    const file = fileRef.current?.files?.[0]
    if (!file) return
    setUploading(true)
    try {
      await uploadPaper(id, file, title)
      setTitle('')
      if (fileRef.current) fileRef.current.value = ''
      refetch()
    } catch (err) {
      alert(`Upload failed: ${err.message}`)
    } finally {
      setUploading(false)
    }
  }

  async function handleDispatch() {
    setDispatching(true)
    try {
      await dispatchJob(id)
      navigate(`/jobs/${id}/status`)
    } catch (err) {
      alert(`Dispatch failed: ${err.message}`)
      setDispatching(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#010102]">
      {isMock && <MockBanner />}

      <div className="px-8 py-8">
        {/* Breadcrumb */}
        <Link to="/jobs" className="text-[#8a8f98] text-xs hover:text-[#5e6ad2] transition-colors mb-4 block">
          ← Jobs
        </Link>

        <h1 className="text-lg font-semibold text-[#f7f8f8] mb-6">
          Job #{id} — Papers
        </h1>

        {/* Upload form */}
        <form onSubmit={handleUpload}
          className="bg-[#0f1011] border border-[#23252a] rounded-[12px] p-4 mb-6 flex flex-wrap gap-3 items-end">
          <div className="flex-1 min-w-48">
            <label className="block text-[#8a8f98] text-xs uppercase tracking-wider mb-1">
              PDF file
            </label>
            <input
              type="file"
              accept=".pdf"
              ref={fileRef}
              required
              className="bg-[#141516] border border-[#23252a] rounded-[8px] px-3 py-2
                         text-[#f7f8f8] text-sm focus:outline-none focus:border-[#5e6ad2]
                         w-full file:mr-3 file:py-1 file:px-2 file:rounded file:border-0
                         file:bg-[#23252a] file:text-[#d0d6e0] file:text-xs"
            />
          </div>
          <div className="flex-1 min-w-48">
            <label className="block text-[#8a8f98] text-xs uppercase tracking-wider mb-1">
              Title (optional)
            </label>
            <input
              type="text"
              value={title}
              onChange={e => setTitle(e.target.value)}
              placeholder="Paper title"
              className="bg-[#141516] border border-[#23252a] rounded-[8px] px-3 py-2
                         text-[#f7f8f8] text-sm focus:outline-none focus:border-[#5e6ad2]
                         placeholder-[#62666d] w-full"
            />
          </div>
          <button
            type="submit"
            disabled={uploading}
            className="px-4 py-2 bg-[#5e6ad2] hover:bg-[#828fff] text-white
                       text-sm rounded-[8px] transition-colors disabled:opacity-50 self-end"
          >
            {uploading ? 'Uploading…' : 'Upload Paper'}
          </button>
        </form>

        {loading && <LoadingState rows={3} />}
        {error && !isMock && <ErrorState message={error} onRetry={refetch} />}

        {papers && papers.length > 0 && (
          <table className="w-full mb-6">
            <thead>
              <tr className="bg-[#0f1011] border-y border-[#23252a]">
                {['Title', 'Claims', 'Uploaded'].map(h => (
                  <th key={h} className="text-[#8a8f98] text-[11px] font-medium uppercase
                                         tracking-wider px-4 py-3 text-left">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {papers.map(p => (
                <tr key={p.id} className="border-b border-[#23252a] hover:bg-[#0f1011] transition-colors">
                  <td className="px-4 py-3 text-[#f7f8f8] text-sm">
                    {p.title || `Paper ${p.id}`}
                  </td>
                  <td className="px-4 py-3 text-[#d0d6e0] font-mono text-xs">
                    {p.claims_count ?? 0}
                  </td>
                  <td className="px-4 py-3 text-[#8a8f98] text-xs">
                    {fmtDate(p.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {papers && papers.length === 0 && !loading && (
          <p className="text-[#8a8f98] text-sm py-8 text-center">
            No papers uploaded yet. Upload at least two to detect conflicts.
          </p>
        )}

        {/* Run action */}
        <div className="mt-4">
          <button
            onClick={handleDispatch}
            disabled={dispatching || !papers || papers.length < 2}
            className="px-4 py-2 bg-[#27a644] hover:bg-[#27a644]/80 text-white
                       text-sm rounded-[8px] transition-colors
                       disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {dispatching ? 'Dispatching…' : 'Run Analysis →'}
          </button>
          {papers && papers.length < 2 && (
            <span className="text-[#62666d] text-xs ml-3">
              Upload at least 2 papers to run analysis
            </span>
          )}
        </div>
      </div>
    </div>
  )
}

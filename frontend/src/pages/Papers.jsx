// frontend/src/pages/Papers.jsx
import { useState, useRef, Fragment } from 'react'
import { Link, useParams, useNavigate } from 'react-router-dom'
import { useApi } from '../hooks/useApi.js'
import { listPapers, uploadPaper, dispatchJob, dispatchJobSync, deletePaper, getJob } from '../api/client.js'
import { MOCK_PAPERS } from '../data/mockData.js'
import { MockBanner } from '../components/MockBanner.jsx'
import { LoadingState } from '../components/LoadingState.jsx'
import { ErrorState } from '../components/ErrorState.jsx'
import ProgressBar from '../components/ProgressBar.jsx'

function fmtDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function UploadIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none"
         stroke="#8a8f98" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"/>
    </svg>
  )
}

function XIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none"
         stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
      <line x1="1" y1="1" x2="11" y2="11" />
      <line x1="11" y1="1" x2="1" y2="11" />
    </svg>
  )
}

function ItemStatus({ status, error }) {
  if (status === 'uploading') {
    return (
      <span className="flex items-center gap-1.5 text-[#5e6ad2] font-mono text-xs">
        <span className="w-1.5 h-1.5 rounded-full bg-[#5e6ad2] animate-pulse" />
        uploading...
      </span>
    )
  }
  if (status === 'done')  return <span className="text-[#27a644] font-mono text-xs">done</span>
  if (status === 'error') return <span className="text-[#EF4444] font-mono text-xs">failed — {error}</span>
  return <span className="text-[#62666d] font-mono text-xs">waiting...</span>
}

export default function Papers() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { data: papers, loading, error, isMock, refetch } = useApi(
    () => listPapers(id), MOCK_PAPERS, [id]
  )
  const { data: job } = useApi(() => getJob(id), null, [id])

  const [dragOver,    setDragOver]    = useState(false)
  const [queue,       setQueue]       = useState([])
  const [uploading,   setUploading]   = useState(false)
  const [nonPdfWarn,  setNonPdfWarn]  = useState(false)
  const [dispatching, setDispatching] = useState(false)
  const fileInputRef = useRef(null)

  const doneCount = queue.filter(q => q.status === 'done').length

  function addFilesToQueue(files) {
    const all = Array.from(files)
    const pdfs = all.filter(f => f.name.toLowerCase().endsWith('.pdf'))
    setNonPdfWarn(pdfs.length < all.length)
    if (!pdfs.length) return
    setQueue(prev => [
      ...prev,
      ...pdfs.map(f => ({
        id: crypto.randomUUID(),
        file: f,
        title: f.name.replace(/\.pdf$/i, ''),
        status: 'queued',
        error: null,
      })),
    ])
  }

  async function uploadAll() {
    const snapshot = queue
    setUploading(true)
    let allDone = true
    for (const item of snapshot) {
      setQueue(prev => prev.map(q => q.id === item.id ? { ...q, status: 'uploading' } : q))
      try {
        await uploadPaper(id, item.file, item.title)
        setQueue(prev => prev.map(q => q.id === item.id ? { ...q, status: 'done' } : q))
      } catch (err) {
        setQueue(prev => prev.map(q => q.id === item.id ? { ...q, status: 'error', error: err.message } : q))
        allDone = false
      }
    }
    setUploading(false)
    refetch()
    if (allDone) setTimeout(() => setQueue([]), 2000)
  }

  async function handleDelete(paperId) {
    try {
      await deletePaper(paperId)
      refetch()
    } catch (err) {
      alert(`Delete failed: ${err.message}`)
    }
  }

  async function handleDispatch() {
    setDispatching(true)
    try {
      // Try sync dispatch first (works on free tier, no Celery needed)
      await dispatchJobSync(id)
      navigate(`/jobs/${id}/status`)
    } catch (err) {
      if (err.message.includes('400')) {
        // Too many papers for sync -- use async
        await dispatchJob(id)
        navigate(`/jobs/${id}/status`)
      } else {
        alert(`Dispatch failed: ${err.message}`)
        setDispatching(false)
      }
    }
  }

  const isPending = job?.status === 'PENDING' || job === null

  return (
    <div className="min-h-screen bg-[#010102]">
      {isMock && <MockBanner />}

      <div className="px-8 py-8">
        <Link to="/jobs" className="text-[#8a8f98] text-xs hover:text-[#5e6ad2] transition-colors mb-4 block">
          ← Jobs
        </Link>

        <h1 className="text-lg font-semibold text-[#f7f8f8] mb-6">
          Job #{id} — Papers
        </h1>

        {/* ── Upload section ──────────────────────────────────────────────── */}
        <div className="bg-[#0f1011] border border-[#23252a] rounded-[12px] p-5 mb-6">
          <p className="text-[#8a8f98] text-xs uppercase tracking-wider mb-4">Upload Papers</p>

          {/* Drag zone */}
          {!uploading && (
            <div
              onClick={() => fileInputRef.current?.click()}
              onDragOver={e => { e.preventDefault(); setDragOver(true) }}
              onDragLeave={() => setDragOver(false)}
              onDrop={e => {
                e.preventDefault()
                setDragOver(false)
                addFilesToQueue(e.dataTransfer.files)
              }}
              className={`border-2 border-dashed rounded-[12px] p-12
                         flex flex-col items-center justify-center gap-3
                         cursor-pointer transition-colors
                         ${dragOver
                           ? 'border-[#5e6ad2] bg-[#5e6ad2]/5'
                           : 'border-[#23252a] hover:border-[#5e6ad2]'}`}
            >
              <UploadIcon />
              <p className="text-[#8a8f98] text-sm">Drag PDF files here</p>
              <p className="text-[#62666d] text-xs">or</p>
              <button
                type="button"
                onClick={e => { e.stopPropagation(); fileInputRef.current?.click() }}
                className="bg-[#0f1011] border border-[#23252a] hover:border-[#5e6ad2]
                           text-[#d0d6e0] text-xs px-3 py-1.5 rounded-[8px] transition-colors"
              >
                Browse files
              </button>
              <p className="text-[#62666d] text-[10px] font-mono mt-1">Accepts multiple PDFs</p>
            </div>
          )}

          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            multiple
            className="hidden"
            onChange={e => { addFilesToQueue(e.target.files); e.target.value = '' }}
          />

          {nonPdfWarn && (
            <p className="text-[#F59E0B] text-xs font-mono mt-3">
              Only PDF files are accepted — non-PDF files were skipped.
            </p>
          )}

          {/* Queue list */}
          {queue.length > 0 && !uploading && (
            <div className="mt-4 space-y-2">
              {queue.map(item => (
                <div key={item.id}
                  className="flex items-center gap-2 bg-[#141516] border border-[#23252a]
                             rounded-[8px] px-3 py-2">
                  <span className="text-[#8a8f98] text-xs font-mono flex-shrink-0 w-40 truncate"
                        title={item.file.name}>
                    {item.file.name.length > 30 ? item.file.name.slice(0, 30) + '…' : item.file.name}
                  </span>
                  <input
                    type="text"
                    value={item.title}
                    onChange={e => {
                      const v = e.target.value
                      setQueue(prev => prev.map(q => q.id === item.id ? { ...q, title: v } : q))
                    }}
                    className="flex-1 bg-[#141516] border border-[#23252a] rounded-[8px]
                               px-2 py-1 text-[#f7f8f8] text-sm
                               focus:outline-none focus:border-[#5e6ad2] transition-colors"
                  />
                  <button
                    type="button"
                    onClick={() => setQueue(prev => prev.filter(q => q.id !== item.id))}
                    className="text-[#62666d] hover:text-[#EF4444] transition-colors flex-shrink-0"
                    aria-label="Remove"
                  >
                    <XIcon />
                  </button>
                </div>
              ))}

              <button
                type="button"
                onClick={uploadAll}
                disabled={uploading}
                className="w-full mt-3 py-2.5 bg-[#5e6ad2] hover:bg-[#828fff]
                           text-white text-sm rounded-[8px] transition-colors
                           disabled:opacity-50"
              >
                Upload {queue.length} paper{queue.length !== 1 ? 's' : ''}
              </button>
            </div>
          )}

          {/* Upload progress */}
          {uploading && (
            <div className="mt-4 space-y-2">
              {queue.map(item => (
                <div key={item.id}
                  className="flex items-center gap-3 bg-[#141516] border border-[#23252a]
                             rounded-[8px] px-3 py-2">
                  <span className="text-[#8a8f98] text-xs font-mono flex-shrink-0 w-40 truncate">
                    {item.file.name.length > 30 ? item.file.name.slice(0, 30) + '…' : item.file.name}
                  </span>
                  <ItemStatus status={item.status} error={item.error} />
                </div>
              ))}
              <div className="mt-3">
                <ProgressBar current={doneCount} total={queue.length} />
                <p className="text-[#62666d] text-xs font-mono mt-1">
                  {doneCount} / {queue.length} uploaded
                </p>
              </div>
            </div>
          )}
        </div>

        {/* ── Papers table ────────────────────────────────────────────────── */}
        {loading && <LoadingState rows={3} />}
        {error && !isMock && <ErrorState message={error} onRetry={refetch} />}

        {papers && papers.length > 0 && (
          <table className="w-full mb-6">
            <thead>
              <tr className="bg-[#0f1011] border-y border-[#23252a]">
                {['Title', 'Claims', 'Uploaded', ''].map(h => (
                  <th key={h} className="text-[#8a8f98] text-[11px] font-medium uppercase
                                         tracking-wider px-4 py-3 text-left">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {papers.map(p => {
                const claimCount = p.claims_count ?? 0
                return (
                  <tr key={p.id} className="border-b border-[#23252a] hover:bg-[#0f1011] transition-colors">
                    <td className="px-4 py-3 text-[#f7f8f8] text-sm max-w-xs">
                      <span title={p.title}>
                        {(p.title || `Paper ${p.id}`).length > 40
                          ? (p.title || `Paper ${p.id}`).slice(0, 40) + '…'
                          : (p.title || `Paper ${p.id}`)}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-mono text-xs">
                      {claimCount > 0
                        ? <span className="text-[#5e6ad2]">{claimCount}</span>
                        : <span className="text-[#62666d]">{job?.status === 'DONE' ? '0' : '—'}</span>
                      }
                    </td>
                    <td className="px-4 py-3 text-[#8a8f98] text-xs">
                      {fmtDate(p.created_at)}
                    </td>
                    <td className="px-4 py-3">
                      {isPending && (
                        <button
                          onClick={() => handleDelete(p.id)}
                          className="text-[#62666d] hover:text-[#EF4444] text-xs transition-colors"
                        >
                          Remove
                        </button>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}

        {papers && papers.length === 0 && !loading && (
          <p className="text-[#8a8f98] text-sm py-8 text-center">
            No papers uploaded yet. Upload at least two to detect conflicts.
          </p>
        )}

        {/* ── Dispatch ────────────────────────────────────────────────────── */}
        <div className="mt-4 flex items-center gap-3">
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
            <span className="text-[#62666d] text-xs">
              Upload at least 2 papers to run analysis
            </span>
          )}
        </div>
      </div>
    </div>
  )
}

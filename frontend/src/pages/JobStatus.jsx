// frontend/src/pages/JobStatus.jsx
import { useState, useEffect } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getJob } from '../api/client.js'
import { MOCK_JOBS } from '../data/mockData.js'
import StatusBadge from '../components/StatusBadge.jsx'
import ProgressBar from '../components/ProgressBar.jsx'

const TERMINAL = ['DONE', 'FAILED']

const STATUS_MSG = {
  PENDING:  { text: 'Waiting for worker…',                      color: 'text-[#8a8f98]' },
  RUNNING:  { text: 'Extracting claims and building conflict graph…', color: 'text-[#d0d6e0]' },
  DONE:     { text: 'Analysis complete.',                        color: 'text-[#27a644]' },
  FAILED:   { text: 'Analysis failed. Check Celery worker.',     color: 'text-[#EF4444]' },
}

export default function JobStatus() {
  const { id } = useParams()
  const [job, setJob] = useState(MOCK_JOBS[0])
  const [isMock, setIsMock] = useState(false)
  const [polling, setPolling] = useState(true)

  useEffect(() => {
    let cancelled = false

    function poll() {
      getJob(id)
        .then(data => {
          if (!cancelled) {
            setJob(data)
            setIsMock(false)
            if (TERMINAL.includes(data.status)) setPolling(false)
          }
        })
        .catch(() => {
          if (!cancelled) setIsMock(true)
        })
    }

    poll()
    const iv = setInterval(() => {
      if (!cancelled && polling) poll()
    }, 5000)

    return () => { cancelled = true; clearInterval(iv) }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  useEffect(() => {
    if (TERMINAL.includes(job?.status)) setPolling(false)
  }, [job?.status])

  const msg = STATUS_MSG[job?.status] || STATUS_MSG.PENDING
  const claimsEst = (job?.papers_count ?? 0) * 6

  return (
    <div className="min-h-screen bg-[#010102]">
      <div className="px-8 py-8 max-w-2xl mx-auto">
        <Link to={`/jobs/${id}`}
          className="text-[#8a8f98] text-xs hover:text-[#5e6ad2] transition-colors mb-4 block">
          ← Papers
        </Link>

        <div className="flex items-center gap-3 mb-6">
          <h1 className="text-xl font-semibold text-[#f7f8f8] tracking-tight">
            Job #{id}
          </h1>
          {isMock && (
            <span className="text-[#F59E0B] text-xs font-mono">DEMO</span>
          )}
        </div>

        <div className="bg-[#0f1011] border border-[#23252a] rounded-[12px] p-6 space-y-5">
          {/* Status row */}
          <div className="flex items-center gap-3">
            <StatusBadge status={job?.status || 'PENDING'} size="lg" />
            {polling && (
              <span className="w-1.5 h-1.5 bg-[#5e6ad2] rounded-full animate-pulse" />
            )}
          </div>

          {/* Progress */}
          {job?.status === 'RUNNING' && (
            <div>
              <ProgressBar
                current={job.claims_count ?? 0}
                total={claimsEst || 1}
              />
            </div>
          )}

          {/* Details grid */}
          <div className="grid grid-cols-2 gap-2 font-mono text-xs text-[#62666d]">
            <span>Papers: <span className="text-[#d0d6e0]">{job?.papers_count ?? 0}</span></span>
            <span>Samples: <span className="text-[#d0d6e0]">{job?.n_samples ?? 1}</span></span>
            <span>Claims: <span className="text-[#d0d6e0]">{job?.claims_count ?? 0}</span></span>
            <span>Conflicts: <span className="text-[#d0d6e0]">{job?.conflicts_count ?? 0}</span></span>
          </div>

          {/* Status message */}
          <p className={`text-sm ${msg.color}`}>{msg.text}</p>
        </div>

        {/* Actions */}
        <div className="mt-4 flex gap-3">
          {job?.status === 'DONE' && (
            <Link
              to={`/jobs/${id}/conflicts`}
              className="px-4 py-2 bg-[#5e6ad2] hover:bg-[#828fff] text-white
                         text-sm rounded-[8px] transition-colors"
            >
              View Conflicts →
            </Link>
          )}
          {job?.status === 'FAILED' && (
            <Link
              to={`/jobs/${id}`}
              className="px-4 py-2 bg-[#0f1011] border border-[#23252a]
                         hover:border-[#34343a] text-[#d0d6e0] text-sm rounded-[8px] transition-colors"
            >
              Back to Papers
            </Link>
          )}
        </div>
      </div>
    </div>
  )
}

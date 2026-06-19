// frontend/src/pages/JobStatus.jsx
import { useState, useEffect } from 'react'
import { Link, useParams, useNavigate } from 'react-router-dom'
import { getJob } from '../api/client.js'
import { MOCK_JOBS } from '../data/mockData.js'
import StatusBadge from '../components/StatusBadge.jsx'
import ProgressBar from '../components/ProgressBar.jsx'

const TERMINAL = ['DONE', 'FAILED']

const STATUS_MSG = {
  PENDING: { text: 'Waiting for worker…',                           color: 'text-[#8a8f98]' },
  RUNNING: { text: 'Extracting claims and building conflict graph…', color: 'text-[#d0d6e0]' },
  DONE:    { text: 'Analysis complete.',                             color: 'text-[#27a644]' },
  FAILED:  { text: 'Analysis failed. Check Celery worker.',          color: 'text-[#EF4444]' },
}

function StageDot({ state }) {
  if (state === 'done')    return <span className="w-2 h-2 rounded-full bg-[#27a644] flex-shrink-0" />
  if (state === 'current') return <span className="w-2 h-2 rounded-full bg-[#5e6ad2] flex-shrink-0 animate-pulse" />
  return <span className="w-2 h-2 rounded-full bg-[#23252a] flex-shrink-0" />
}

export default function JobStatus() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [job,     setJob]     = useState(MOCK_JOBS[0])
  const [isMock,  setIsMock]  = useState(false)
  const [polling, setPolling] = useState(true)
  const [elapsed, setElapsed] = useState(0)
  const [redirecting, setRedirecting] = useState(false)

  // Polling
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
        .catch(() => { if (!cancelled) setIsMock(true) })
    }
    poll()
    const iv = setInterval(() => { if (!cancelled && polling) poll() }, 5000)
    return () => { cancelled = true; clearInterval(iv) }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  useEffect(() => {
    if (TERMINAL.includes(job?.status)) setPolling(false)
  }, [job?.status])

  // Elapsed timer while RUNNING
  useEffect(() => {
    if (job?.status !== 'RUNNING') return
    const iv = setInterval(() => setElapsed(e => e + 1), 1000)
    return () => clearInterval(iv)
  }, [job?.status])

  // Auto-redirect to conflicts when DONE
  useEffect(() => {
    if (job?.status === 'DONE') {
      setRedirecting(true)
      const t = setTimeout(() => navigate(`/jobs/${id}/conflicts`), 2000)
      return () => clearTimeout(t)
    }
  }, [job?.status, id, navigate])

  const msg         = STATUS_MSG[job?.status] || STATUS_MSG.PENDING
  const isRunning   = job?.status === 'RUNNING'
  const paperCount  = job?.paper_count ?? job?.papers_count ?? 0
  const claimCount  = job?.claim_count ?? job?.claims_count ?? 0
  const answerCount = job?.answer_count ?? job?.conflicts_count ?? 0
  const claimsEst   = paperCount * 6

  const stages = [
    { label: 'PDF Upload',        done: paperCount  > 0 },
    { label: 'Claim Extraction',  done: claimCount  > 0 },
    { label: 'QA Answering',      done: answerCount > 0 },
    { label: 'RL Scoring',        done: job?.status === 'DONE' },
  ]

  const currentStageIdx = isRunning
    ? stages.findIndex(s => !s.done)
    : -1

  const estMinRemaining = isRunning && claimCount > 0
    ? Math.max(1, paperCount * 2 - Math.floor(elapsed / 30))
    : null

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

        {/* Status card */}
        <div className="bg-[#0f1011] border border-[#23252a] rounded-[12px] p-6 space-y-5">
          <div className="flex items-center gap-3">
            <StatusBadge status={job?.status || 'PENDING'} size="lg" />
            {polling && (
              <span className="w-1.5 h-1.5 bg-[#5e6ad2] rounded-full animate-pulse" />
            )}
          </div>

          {isRunning && (
            <div>
              <ProgressBar current={claimCount} total={claimsEst || 1} />
              {claimCount > 0 && (
                <p className="text-[#d0d6e0] text-xs font-mono mt-1">
                  Claims extracted: {claimCount} across {paperCount} paper{paperCount !== 1 ? 's' : ''}
                </p>
              )}
              {estMinRemaining && (
                <p className="text-[#62666d] text-xs font-mono mt-0.5">
                  Approximately {estMinRemaining} min remaining
                </p>
              )}
            </div>
          )}

          <div className="grid grid-cols-2 gap-2 font-mono text-xs text-[#62666d]">
            <span>Papers:  <span className="text-[#d0d6e0]">{paperCount}</span></span>
            <span>Samples: <span className="text-[#d0d6e0]">{job?.n_samples ?? 1}</span></span>
            <span>Claims:  <span className="text-[#d0d6e0]">{claimCount}</span></span>
            <span>Answers: <span className="text-[#d0d6e0]">{answerCount}</span></span>
          </div>

          <p className={`text-sm ${msg.color}`}>{msg.text}</p>

          {redirecting && (
            <p className="text-[#5e6ad2] text-xs animate-pulse font-mono">
              Redirecting to results...
            </p>
          )}
        </div>

        {/* Pipeline stages */}
        <div className="mt-4 bg-[#0f1011] border border-[#23252a] rounded-[12px] p-5">
          <p className="text-[#8a8f98] text-xs uppercase tracking-wider mb-4">Pipeline</p>
          <div className="space-y-3">
            {stages.map((stage, i) => {
              const state = stage.done
                ? 'done'
                : i === currentStageIdx
                  ? 'current'
                  : 'pending'
              return (
                <div key={stage.label} className="flex items-center gap-3">
                  <StageDot state={state} />
                  <span className={`text-xs font-mono ${
                    state === 'done'    ? 'text-[#27a644]' :
                    state === 'current' ? 'text-[#5e6ad2]' :
                    'text-[#62666d]'
                  }`}>
                    {stage.label}
                  </span>
                </div>
              )
            })}
          </div>
        </div>

        {/* Actions */}
        <div className="mt-4 flex gap-3 flex-wrap">
          {job?.status === 'DONE' && (
            <>
              <Link
                to={`/jobs/${id}/conflicts`}
                className="px-4 py-2 bg-[#5e6ad2] hover:bg-[#828fff] text-white
                           text-sm rounded-[8px] transition-colors"
              >
                View Results →
              </Link>
              <Link
                to={`/jobs/${id}/chat`}
                className="px-4 py-2 bg-[#0f1011] border border-[#23252a]
                           hover:border-[#5e6ad2] text-[#d0d6e0] hover:text-[#f7f8f8]
                           text-sm rounded-[8px] transition-colors font-mono"
              >
                Chat with Evidence →
              </Link>
            </>
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

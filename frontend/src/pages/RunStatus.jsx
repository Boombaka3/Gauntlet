// frontend/src/pages/RunStatus.jsx
import { useState, useEffect, useRef } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { getRun } from '../api/client.js'
import { MOCK_RUNS } from '../data/mockData.js'
import { MockBanner } from '../components/MockBanner.jsx'
import StatusBadge from '../components/StatusBadge.jsx'
import ProgressBar from '../components/ProgressBar.jsx'

const TERMINAL = ['DONE', 'FAILED']

function statusMessage(run) {
  if (!run) return ''
  const msgs = {
    PENDING: 'Waiting for Celery worker to pick up the job…',
    DISPATCHED: `Dispatching ${run.total} model tasks…`,
    RUNNING: `${run.progress} of ${run.total} model runs complete`,
    DONE: 'All runs complete. View results below.',
    FAILED: 'Run failed. Check Celery worker logs.',
  }
  return msgs[run.status] || run.status
}

function duration(run) {
  if (!run?.started_at) return null
  const end = run.finished_at ? new Date(run.finished_at) : new Date()
  const secs = Math.round((end - new Date(run.started_at)) / 1000)
  if (secs < 60) return `${secs}s`
  return `${Math.floor(secs / 60)}m ${secs % 60}s`
}

function fmt(dt) {
  return dt ? new Date(dt).toLocaleString() : '--'
}

export default function RunStatus() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [run, setRun] = useState(null)
  const [loading, setLoading] = useState(true)
  const [isMock, setIsMock] = useState(false)
  const intervalRef = useRef(null)

  async function fetchRun() {
    try {
      const data = await getRun(id)
      setRun(data)
      setIsMock(false)
      if (TERMINAL.includes(data.status)) {
        clearInterval(intervalRef.current)
      }
    } catch {
      if (!run) {
        const mock = MOCK_RUNS.find(r => r.id === parseInt(id, 10)) || MOCK_RUNS[0]
        setRun(mock)
        setIsMock(true)
      }
      clearInterval(intervalRef.current)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchRun().then(() => {
      setRun(prev => {
        if (prev && !TERMINAL.includes(prev.status)) {
          intervalRef.current = setInterval(fetchRun, 3000)
        }
        return prev
      })
    })
    return () => clearInterval(intervalRef.current)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  if (loading) {
    return (
      <div className="min-h-screen bg-gauntlet-bg px-8 py-8">
        <div className="animate-pulse space-y-4 max-w-2xl">
          <div className="h-8 bg-gauntlet-surface border border-gauntlet-border" />
          <div className="h-32 bg-gauntlet-surface border border-gauntlet-border" />
        </div>
      </div>
    )
  }

  if (!run) return null

  const dur = duration(run)

  return (
    <div className="min-h-screen bg-gauntlet-bg">
      {isMock && <MockBanner />}
      <div className="px-8 py-8">
        <div className="flex items-center gap-3 mb-8">
          <h1 className="text-2xl font-semibold text-gauntlet-text">Run #{run.id}</h1>
          <StatusBadge status={run.status} size="lg" />
          {!TERMINAL.includes(run.status) && (
            <span className="w-2 h-2 rounded-full bg-gauntlet-accent animate-pulse" title="Polling…" />
          )}
        </div>

        <div className="bg-gauntlet-surface border border-gauntlet-border p-6 max-w-2xl space-y-5">
          <ProgressBar current={run.progress} total={run.total} />

          <p className="text-sm text-gauntlet-text">{statusMessage(run)}</p>

          <div className="grid grid-cols-2 gap-x-8 gap-y-3 text-xs border-t border-gauntlet-border pt-4">
            <div>
              <span className="text-gauntlet-muted font-mono">Suite ID</span>
              <span className="ml-3 text-gauntlet-text font-mono">{run.suite_id}</span>
            </div>
            <div>
              <span className="text-gauntlet-muted font-mono">Score mode</span>
              <span className="ml-3 text-gauntlet-text font-mono">{run.score_mode}</span>
            </div>
            <div>
              <span className="text-gauntlet-muted font-mono">Started</span>
              <span className="ml-3 text-gauntlet-text">{fmt(run.started_at)}</span>
            </div>
            <div>
              <span className="text-gauntlet-muted font-mono">Finished</span>
              <span className="ml-3 text-gauntlet-text">{fmt(run.finished_at)}</span>
            </div>
            {dur && (
              <div>
                <span className="text-gauntlet-muted font-mono">Duration</span>
                <span className="ml-3 text-gauntlet-text font-mono">{dur}</span>
              </div>
            )}
          </div>
        </div>

        <div className="mt-6 flex gap-4">
          {run.status === 'DONE' && (
            <button
              onClick={() => navigate(`/runs/${id}/results`)}
              className="bg-gauntlet-success hover:bg-gauntlet-success/80 text-white text-sm font-medium px-5 py-2 transition-colors"
            >
              View Results →
            </button>
          )}
          <Link
            to="/suites"
            className="text-gauntlet-muted hover:text-gauntlet-text text-sm"
          >
            ← Back to Suites
          </Link>
        </div>
      </div>
    </div>
  )
}

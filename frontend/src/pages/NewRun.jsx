// frontend/src/pages/NewRun.jsx
import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useApi } from '../hooks/useApi.js'
import { listSuites, listModels, createRun } from '../api/client.js'
import { MOCK_SUITES, MOCK_MODELS } from '../data/mockData.js'
import { MockBanner } from '../components/MockBanner.jsx'
import { LoadingState } from '../components/LoadingState.jsx'
import { ErrorState } from '../components/ErrorState.jsx'

const SCORE_MODES = [
  { value: 'exact_match', label: 'Exact Match', desc: 'Compare output to expected string' },
  { value: 'rubric', label: 'Rubric', desc: 'Score against suite criteria weights' },
  { value: 'llm_judge', label: 'LLM Judge', desc: 'Claude evaluates quality holistically' },
  { value: 'regression', label: 'Regression', desc: 'Compare delta against a baseline run' },
]

export default function NewRun() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const preselectedSuiteId = searchParams.get('suite_id') || ''

  const { data: suites, loading: loadingSuites, error: errorSuites, isMock: mockSuites } =
    useApi(listSuites, MOCK_SUITES)
  const { data: models, loading: loadingModels, error: errorModels, isMock: mockModels } =
    useApi(listModels, MOCK_MODELS)

  const [suiteId, setSuiteId] = useState(preselectedSuiteId)
  const [selectedModels, setSelectedModels] = useState([])
  const [scoreMode, setScoreMode] = useState('rubric')
  const [baselineRunId, setBaselineRunId] = useState('')
  const [submitError, setSubmitError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  const isMock = mockSuites || mockModels
  const loading = loadingSuites || loadingModels
  const error = errorSuites || errorModels

  function toggleModel(m) {
    setSelectedModels(prev =>
      prev.includes(m) ? prev.filter(x => x !== m) : [...prev, m]
    )
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setSubmitError(null)
    if (!suiteId) { setSubmitError('Select a suite.'); return }
    if (selectedModels.length === 0) { setSubmitError('Select at least one model.'); return }
    setSubmitting(true)
    try {
      const run = await createRun({
        suite_id: parseInt(suiteId, 10),
        model_ids: selectedModels,
        score_mode: scoreMode,
        baseline_run_id: scoreMode === 'regression' && baselineRunId
          ? parseInt(baselineRunId, 10)
          : null,
      })
      navigate(`/runs/${run.id}`)
    } catch (err) {
      setSubmitError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-gauntlet-bg">
      {isMock && <MockBanner />}
      <div className="px-8 py-8">
        <div className="mb-8">
          <h1 className="text-2xl font-semibold text-gauntlet-text">New Run</h1>
          <p className="text-gauntlet-muted text-sm mt-1">Configure and dispatch an evaluation run</p>
        </div>

        {loading && <LoadingState rows={6} />}
        {error && <ErrorState message={error} />}

        {!loading && !error && suites && models && (
          <form onSubmit={handleSubmit} className="max-w-2xl space-y-8">
            {/* Suite */}
            <div>
              <label className="block text-gauntlet-muted text-xs font-mono uppercase tracking-wider mb-2">
                Suite
              </label>
              <select
                value={suiteId}
                onChange={e => setSuiteId(e.target.value)}
                className="w-full bg-gauntlet-surface border border-gauntlet-border text-gauntlet-text text-sm px-3 py-2 focus:outline-none focus:border-gauntlet-accent"
              >
                <option value="">-- Select a suite --</option>
                {suites.map(s => (
                  <option key={s.id} value={s.id}>{s.name} (v{s.version})</option>
                ))}
              </select>
            </div>

            {/* Models */}
            <div>
              <label className="block text-gauntlet-muted text-xs font-mono uppercase tracking-wider mb-2">
                Models <span className="normal-case">— select one or more</span>
              </label>
              <div className="border border-gauntlet-border divide-y divide-gauntlet-border max-h-64 overflow-y-auto">
                {models.map(m => (
                  <label
                    key={m}
                    className="flex items-center gap-3 px-4 py-3 hover:bg-gauntlet-surface cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={selectedModels.includes(m)}
                      onChange={() => toggleModel(m)}
                      className="accent-gauntlet-accent"
                    />
                    <span className="font-mono text-sm text-gauntlet-text">{m}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Score mode radio cards */}
            <div>
              <label className="block text-gauntlet-muted text-xs font-mono uppercase tracking-wider mb-2">
                Score Mode
              </label>
              <div className="grid grid-cols-2 gap-3">
                {SCORE_MODES.map(({ value, label, desc }) => (
                  <div
                    key={value}
                    onClick={() => setScoreMode(value)}
                    className={`cursor-pointer border p-4 transition-colors ${
                      scoreMode === value
                        ? 'border-gauntlet-accent bg-gauntlet-accent/5'
                        : 'border-gauntlet-border bg-gauntlet-surface hover:border-gauntlet-muted'
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`w-3 h-3 rounded-full border-2 flex-shrink-0 ${
                        scoreMode === value
                          ? 'border-gauntlet-accent bg-gauntlet-accent'
                          : 'border-gauntlet-muted'
                      }`} />
                      <span className="text-gauntlet-text text-sm font-medium">{label}</span>
                    </div>
                    <p className="text-gauntlet-muted text-xs ml-5">{desc}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Baseline run ID (regression only) */}
            {scoreMode === 'regression' && (
              <div>
                <label className="block text-gauntlet-muted text-xs font-mono uppercase tracking-wider mb-2">
                  Baseline Run ID
                </label>
                <input
                  type="number"
                  value={baselineRunId}
                  onChange={e => setBaselineRunId(e.target.value)}
                  placeholder="Enter baseline EvalRun ID"
                  className="w-full bg-gauntlet-surface border border-gauntlet-border text-gauntlet-text text-sm px-3 py-2 focus:outline-none focus:border-gauntlet-accent font-mono"
                />
              </div>
            )}

            {submitError && (
              <div className="border border-gauntlet-danger/30 bg-gauntlet-danger/10 text-gauntlet-danger text-sm px-4 py-3 font-mono">
                {submitError}
              </div>
            )}

            <button
              type="submit"
              disabled={submitting}
              className="w-full bg-gauntlet-accent hover:bg-gauntlet-accent/80 disabled:opacity-50 text-white text-sm font-medium py-3 transition-colors"
            >
              {submitting ? 'Dispatching...' : 'Dispatch Run'}
            </button>
          </form>
        )}
      </div>
    </div>
  )
}

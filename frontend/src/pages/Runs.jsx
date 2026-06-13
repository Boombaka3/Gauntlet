// frontend/src/pages/Runs.jsx
import { Link } from 'react-router-dom'

export default function Runs() {
  return (
    <div className="min-h-screen bg-gauntlet-bg px-8 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-gauntlet-text">Runs</h1>
        <p className="text-gauntlet-muted text-sm mt-1">Evaluation run history</p>
      </div>

      <div className="bg-gauntlet-surface border border-gauntlet-border px-6 py-10 text-center max-w-lg">
        <div className="text-gauntlet-muted text-sm mb-2 font-mono">
          No /runs/ list endpoint available yet.
        </div>
        <p className="text-gauntlet-muted text-xs mb-6">
          Navigate directly to a run by ID, or dispatch a new run from any suite.
        </p>
        <Link
          to="/runs/new"
          className="inline-block bg-gauntlet-accent hover:bg-gauntlet-accent/80 text-white text-sm font-medium px-5 py-2 transition-colors"
        >
          + New Run
        </Link>
      </div>
    </div>
  )
}

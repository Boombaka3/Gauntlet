// frontend/src/components/StatusBadge.jsx
const STATUS_STYLES = {
  PENDING:    'bg-gauntlet-warning/10 text-gauntlet-warning border border-gauntlet-warning/30',
  DISPATCHED: 'bg-blue-500/10 text-blue-400 border border-blue-500/30',
  RUNNING:    'bg-gauntlet-accent/10 text-indigo-400 border border-gauntlet-accent/30 animate-pulse',
  DONE:       'bg-gauntlet-success/10 text-gauntlet-success border border-gauntlet-success/30',
  FAILED:     'bg-gauntlet-danger/10 text-gauntlet-danger border border-gauntlet-danger/30',
}

export default function StatusBadge({ status, size = 'sm' }) {
  const style = STATUS_STYLES[status] || 'bg-gauntlet-surface text-gauntlet-muted border border-gauntlet-border'
  const sz = size === 'lg' ? 'text-sm px-3 py-1' : 'text-xs px-2 py-0.5'
  return (
    <span className={`inline-block font-mono uppercase tracking-wider ${sz} ${style}`}>
      {status}
    </span>
  )
}

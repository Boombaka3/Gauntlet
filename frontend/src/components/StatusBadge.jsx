// frontend/src/components/StatusBadge.jsx
const STATUS_STYLES = {
  PENDING:    'bg-[#141516] text-[#d0d6e0] border border-[#34343a]',
  DISPATCHED: 'bg-[#141516] text-[#5e6ad2] border border-[#5e6ad2]/30',
  RUNNING:    'bg-[#141516] text-[#F59E0B] border border-[#F59E0B]/30 animate-pulse',
  DONE:       'bg-[#141516] text-[#27a644] border border-[#27a644]/30',
  FAILED:     'bg-[#141516] text-[#EF4444] border border-[#EF4444]/30',
}

export default function StatusBadge({ status, size = 'sm' }) {
  const style = STATUS_STYLES[status] || 'bg-[#141516] text-[#8a8f98] border border-[#23252a]'
  const sz = size === 'lg'
    ? 'text-xs px-3 py-1 rounded-[9999px]'
    : 'text-[10px] px-2 py-0.5 rounded-[9999px]'
  return (
    <span className={`inline-block font-mono uppercase tracking-wider ${sz} ${style}`}>
      {status}
    </span>
  )
}

// frontend/src/components/ConflictBadge.jsx
const STYLES = {
  CONTRADICTS: 'text-[#EF4444] bg-[#EF4444]/10 border border-[#EF4444]/20',
  SUPPORTS:    'text-[#27a644] bg-[#27a644]/10 border border-[#27a644]/20',
  PARTIAL:     'text-[#F59E0B] bg-[#F59E0B]/10 border border-[#F59E0B]/20',
  NEI:         'text-[#8a8f98] bg-[#141516] border border-[#23252a]',
}

export function ConflictBadge({ verdict }) {
  return (
    <span className={`rounded-[4px] px-2 py-0.5 text-[10px] font-mono
                      uppercase tracking-wider ${STYLES[verdict] || STYLES.NEI}`}>
      {verdict || 'NEI'}
    </span>
  )
}

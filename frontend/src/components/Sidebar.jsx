// frontend/src/components/Sidebar.jsx
import { NavLink } from 'react-router-dom'

const GridIcon = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
    <rect x="1" y="1" width="6" height="6" rx="1" />
    <rect x="9" y="1" width="6" height="6" rx="1" />
    <rect x="1" y="9" width="6" height="6" rx="1" />
    <rect x="9" y="9" width="6" height="6" rx="1" />
  </svg>
)

const PlusCircleIcon = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
    <circle cx="8" cy="8" r="6.5" />
    <line x1="8" y1="5" x2="8" y2="11" />
    <line x1="5" y1="8" x2="11" y2="8" />
  </svg>
)

const ListIcon = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
    <line x1="2" y1="4" x2="14" y2="4" />
    <line x1="2" y1="8" x2="14" y2="8" />
    <line x1="2" y1="12" x2="14" y2="12" />
  </svg>
)

const NAV = [
  { to: '/jobs',      label: 'Jobs',          Icon: GridIcon      },
  { to: '/jobs/new',  label: 'New Analysis',  Icon: PlusCircleIcon },
  { to: '/jobs/list', label: 'History',        Icon: ListIcon      },
]

export default function Sidebar() {
  return (
    <aside className="w-60 flex-shrink-0 fixed top-0 left-0 h-screen
                      bg-[#0f1011] border-r border-[#23252a]
                      flex flex-col">
      {/* Brand */}
      <div className="px-5 pt-5 pb-4">
        <div className="text-[#f7f8f8] font-mono font-bold tracking-widest text-xs uppercase">
          EVIDENCE
        </div>
        <div className="text-[#8a8f98] text-xs mt-1">
          Claim Conflict Detection
        </div>
        <div className="h-px bg-[#23252a] mt-4" />
      </div>

      {/* Nav */}
      <nav className="flex-1 pt-1 space-y-0.5">
        {NAV.map(({ to, label, Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/jobs'}
            className={({ isActive }) =>
              `flex items-center gap-2.5 px-3 py-2 mx-2 rounded-[8px] text-sm transition-colors ${
                isActive
                  ? 'text-[#5e6ad2] bg-[#0f1011] border border-[#23252a]'
                  : 'text-[#8a8f98] hover:text-[#f7f8f8] hover:bg-[#141516]'
              }`
            }
          >
            {({ isActive }) => (
              <>
                <span className={isActive ? 'text-[#5e6ad2]' : 'text-[#8a8f98]'}>
                  <Icon />
                </span>
                {label}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-3 py-4 border-t border-[#23252a] space-y-1">
        <div className="text-[#62666d] text-xs font-mono px-3">v1.0.0</div>
        <a
          href="https://github.com/Boombaka3/EvidenceLens"
          target="_blank"
          rel="noreferrer"
          className="text-[#62666d] text-xs hover:text-[#5e6ad2] transition-colors px-3 block"
        >
          github ↗
        </a>
      </div>
    </aside>
  )
}

// frontend/src/components/DeltaBadge.jsx
export default function DeltaBadge({ delta }) {
  if (delta === null || delta === undefined) {
    return <span className="text-gauntlet-muted font-mono text-xs">--</span>
  }
  if (delta > 0) {
    return <span className="text-gauntlet-success font-mono text-xs">+{delta.toFixed(2)}</span>
  }
  if (delta < 0) {
    return <span className="text-gauntlet-danger font-mono text-xs">{delta.toFixed(2)}</span>
  }
  return <span className="text-gauntlet-muted font-mono text-xs">0.00</span>
}

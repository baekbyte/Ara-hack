const ITEMS = [
  { color: '#4A9EFF', label: 'Omi Memory' },
  { color: '#FF8C42', label: 'Ara Action' },
  { color: '#50C878', label: 'Ara Observation' },
]

const EDGE_ITEMS = [
  { color: 'rgba(255,255,255,0.4)', label: 'Semantic' },
  { color: 'rgba(100,180,255,0.5)', label: 'Temporal' },
  { color: 'rgba(255,200,50,0.7)',  label: 'Causal' },
]

export default function Legend() {
  return (
    <div style={{
      position: 'absolute', bottom: 24, left: 24, zIndex: 10,
      background: 'rgba(8,8,22,0.82)',
      border: '1px solid #1a1a2e',
      borderRadius: 10,
      padding: '12px 16px',
      fontFamily: "'Courier New', monospace",
      fontSize: 11,
      color: '#666',
      backdropFilter: 'blur(8px)',
    }}>
      <div style={{ marginBottom: 8, color: '#333', textTransform: 'uppercase', letterSpacing: 1 }}>Nodes</div>
      {ITEMS.map(({ color, label }) => (
        <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 5 }}>
          <span style={{ width: 10, height: 10, borderRadius: '50%', background: color, display: 'inline-block', flexShrink: 0 }} />
          <span style={{ color: '#888' }}>{label}</span>
        </div>
      ))}
      <div style={{ margin: '10px 0 8px', color: '#333', textTransform: 'uppercase', letterSpacing: 1 }}>Edges</div>
      {EDGE_ITEMS.map(({ color, label }) => (
        <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 5 }}>
          <span style={{ width: 18, height: 2, background: color, display: 'inline-block', flexShrink: 0 }} />
          <span style={{ color: '#888' }}>{label}</span>
        </div>
      ))}
    </div>
  )
}

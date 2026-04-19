const TYPE_META = {
  omi_memory:      { label: 'Omi Memory',       color: '#4A9EFF' },
  ara_tool_call:   { label: 'Ara Action',        color: '#FF8C42' },
  ara_message:     { label: 'Ara Message',       color: '#FF8C42' },
  ara_observation: { label: 'Ara Observation',   color: '#50C878' },
}

export default function NodePanel({ node, onClose }) {
  const meta = TYPE_META[node.node_type] ?? { label: node.node_type, color: '#888' }
  const ts = new Date(node.timestamp).toLocaleString()

  return (
    <div style={{
      position: 'absolute', top: 20, right: 20, width: 360,
      background: 'rgba(8,8,22,0.93)',
      border: `1px solid ${meta.color}44`,
      borderLeft: `3px solid ${meta.color}`,
      borderRadius: 10,
      padding: '18px 20px',
      color: '#ddd',
      fontFamily: "'Courier New', monospace",
      backdropFilter: 'blur(12px)',
      zIndex: 20,
      maxHeight: '80vh',
      overflowY: 'auto',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
        <span style={{ color: meta.color, fontWeight: 700, fontSize: 13, textTransform: 'uppercase', letterSpacing: 1 }}>
          {meta.label}
        </span>
        <button
          onClick={onClose}
          style={{ background: 'none', border: 'none', color: '#555', cursor: 'pointer', fontSize: 20, lineHeight: 1 }}
        >
          ×
        </button>
      </div>

      <p style={{ fontSize: 13, lineHeight: 1.7, color: '#ccc', marginBottom: 16 }}>
        {node.content}
      </p>

      <div style={{ fontSize: 11, color: '#555', display: 'flex', flexDirection: 'column', gap: 4 }}>
        <Row label="Source"     value={node.source} />
        <Row label="Time"       value={ts} />
        <Row label="Importance" value={(node.importance ?? 0).toFixed(5)} />
        <Row label="ID"         value={node.id.slice(0, 8) + '…'} />
      </div>

      {node.metadata && Object.keys(node.metadata).length > 0 && (
        <details style={{ marginTop: 14 }}>
          <summary style={{ cursor: 'pointer', color: '#444', fontSize: 11, userSelect: 'none' }}>
            Raw metadata
          </summary>
          <pre style={{
            color: '#555', fontSize: 10, marginTop: 8,
            overflowX: 'auto', whiteSpace: 'pre-wrap', wordBreak: 'break-all',
          }}>
            {JSON.stringify(node.metadata, null, 2)}
          </pre>
        </details>
      )}
    </div>
  )
}

function Row({ label, value }) {
  return (
    <div>
      <span style={{ color: '#444' }}>{label}: </span>
      <span style={{ color: '#888' }}>{value}</span>
    </div>
  )
}

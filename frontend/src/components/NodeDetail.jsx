import React, { useMemo } from 'react';

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatTimestamp(ts) {
  if (!ts) return null;
  try {
    const d = new Date(typeof ts === 'number' ? ts * 1000 : ts);
    if (isNaN(d.getTime())) return String(ts);
    return d.toLocaleString(undefined, {
      year:   'numeric',
      month:  'short',
      day:    'numeric',
      hour:   '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch {
    return String(ts);
  }
}

const SOURCE_KEYS = new Set(['source', 'node_type', 'type', 'content', 'timestamp', 'created_at', 'id']);

function deriveSource(node) {
  const src = node.source ?? node.node_type ?? '';
  if (src.toLowerCase().startsWith('omi')) return 'omi';
  if (src.toLowerCase().startsWith('ara')) return 'ara';
  return 'other';
}

function SourceBadge({ node }) {
  const kind  = deriveSource(node);
  const label = kind === 'omi' ? 'Omi' : kind === 'ara' ? 'Ara' : 'Other';
  return (
    <span className={`source-badge ${kind}`}>
      {label}
    </span>
  );
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function NodeDetail({ node, onClose }) {
  const isOpen = Boolean(node);

  // Collect extra metadata keys (everything not in the main display)
  const metaEntries = useMemo(() => {
    if (!node) return [];
    return Object.entries(node).filter(([k]) => !SOURCE_KEYS.has(k));
  }, [node]);

  const timestamp = node
    ? formatTimestamp(node.timestamp ?? node.created_at)
    : null;

  const nodeType = node?.node_type ?? node?.type ?? null;

  return (
    <aside className={`node-detail${isOpen ? ' open' : ''}`} aria-hidden={!isOpen}>
      <div className="panel-header">
        <span className="panel-title">Node Detail</span>
        <button className="close-btn" onClick={onClose} aria-label="Close panel">
          &times;
        </button>
      </div>

      {node && (
        <div className="panel-body">
          {/* Source + type row */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            <SourceBadge node={node} />
            {nodeType && <span className="type-pill">{nodeType}</span>}
          </div>

          {/* Timestamp */}
          {timestamp && (
            <div className="timestamp">{timestamp}</div>
          )}

          {/* Content */}
          {node.content && (
            <div>
              <div className="content-label">Content</div>
              <div className="content-block">{node.content}</div>
            </div>
          )}

          {/* Node ID */}
          <div>
            <div className="content-label">Node ID</div>
            <div className="content-block" style={{ fontSize: '11px', color: '#6B6B6B', wordBreak: 'break-all' }}>
              {node.id}
            </div>
          </div>

          {/* Extra metadata */}
          {metaEntries.length > 0 && (
            <div>
              <div className="content-label">Metadata</div>
              <div className="meta-table">
                {metaEntries.map(([k, v]) => (
                  <div className="meta-row" key={k}>
                    <span className="meta-key">{k}</span>
                    <span className="meta-val">
                      {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </aside>
  );
}

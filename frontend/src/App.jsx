import React, { useState, useEffect, useCallback, useRef } from 'react';
import Graph from './components/Graph.jsx';
import NodeDetail from './components/NodeDetail.jsx';

const POLL_INTERVAL = 2000;

export default function App() {
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] });
  const [selectedNode, setSelectedNode] = useState(null);
  const [highlightIds, setHighlightIds] = useState(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [searchCount, setSearchCount] = useState(0);
  const [status, setStatus] = useState('connecting'); // 'live' | 'error' | 'connecting'
  const searchTimeout = useRef(null);

  // ── Poll /graph every 2 s ──────────────────────────────────────────────────
  useEffect(() => {
    let cancelled = false;

    const fetchGraph = async () => {
      try {
        const res = await fetch('http://localhost:8000/graph');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (!cancelled) {
          setGraphData(data);
          setStatus('live');
        }
      } catch {
        if (!cancelled) setStatus('error');
      }
    };

    fetchGraph();
    const id = setInterval(fetchGraph, POLL_INTERVAL);
    return () => { cancelled = true; clearInterval(id); };
  }, []);

  // ── Debounced search ───────────────────────────────────────────────────────
  const handleSearchChange = useCallback((e) => {
    const q = e.target.value;
    setSearchQuery(q);

    clearTimeout(searchTimeout.current);

    if (!q.trim()) {
      setHighlightIds(new Set());
      setSearchCount(0);
      return;
    }

    searchTimeout.current = setTimeout(async () => {
      try {
        const res = await fetch(`http://localhost:8000/query?q=${encodeURIComponent(q)}`);
        if (!res.ok) throw new Error();
        const data = await res.json();
        // Expect { nodes: [{id, ...}, ...] } or [{id, ...}]
        const hits = Array.isArray(data) ? data : (data.nodes ?? []);
        const ids = new Set(hits.map((n) => n.id ?? n));
        setHighlightIds(ids);
        setSearchCount(ids.size);
      } catch {
        // Fall back to client-side filter
        const lower = q.toLowerCase();
        const ids = new Set(
          graphData.nodes
            .filter((n) => (n.content ?? '').toLowerCase().includes(lower))
            .map((n) => n.id)
        );
        setHighlightIds(ids);
        setSearchCount(ids.size);
      }
    }, 300);
  }, [graphData.nodes]);

  const nodeCount = graphData.nodes.length;
  const edgeCount = (graphData.edges ?? graphData.links ?? []).length;

  return (
    <div className="app">
      {/* ── Header ── */}
      <header className="header">
        <div className="header-logo">
          <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
            <circle cx="11" cy="11" r="10" stroke="#4A9EFF" strokeWidth="1.5" />
            <circle cx="11" cy="11" r="3" fill="#4A9EFF" />
            <line x1="11" y1="1" x2="11" y2="5" stroke="#4A9EFF" strokeWidth="1.5" />
            <line x1="11" y1="17" x2="11" y2="21" stroke="#4A9EFF" strokeWidth="1.5" />
            <line x1="1" y1="11" x2="5" y2="11" stroke="#4A9EFF" strokeWidth="1.5" />
            <line x1="17" y1="11" x2="21" y2="11" stroke="#4A9EFF" strokeWidth="1.5" />
            <line x1="3.22" y1="3.22" x2="6.05" y2="6.05" stroke="#4A9EFF" strokeWidth="1" />
            <line x1="15.95" y1="15.95" x2="18.78" y2="18.78" stroke="#4A9EFF" strokeWidth="1" />
            <line x1="18.78" y1="3.22" x2="15.95" y2="6.05" stroke="#4A9EFF" strokeWidth="1" />
            <line x1="6.05" y1="15.95" x2="3.22" y2="18.78" stroke="#4A9EFF" strokeWidth="1" />
          </svg>
          <span className="header-title">Memory Palace</span>
        </div>

        <span className="header-count">
          {nodeCount} node{nodeCount !== 1 ? 's' : ''} &middot; {edgeCount} edge{edgeCount !== 1 ? 's' : ''}
        </span>

        {/* Search */}
        <div className="search-wrap">
          <svg className="search-icon" width="14" height="14" viewBox="0 0 14 14" fill="none">
            <circle cx="6" cy="6" r="4.5" stroke="currentColor" strokeWidth="1.4" />
            <line x1="9.5" y1="9.5" x2="13" y2="13" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
          </svg>
          <input
            className="search-input"
            type="text"
            placeholder="Search memory nodes..."
            value={searchQuery}
            onChange={handleSearchChange}
          />
          {searchCount > 0 && (
            <span className="search-badge">{searchCount} match{searchCount !== 1 ? 'es' : ''}</span>
          )}
        </div>

        <div className="header-status">
          <span className={`status-dot${status === 'error' ? ' error' : ''}`} />
          {status === 'live' ? 'Live' : status === 'error' ? 'Offline' : 'Connecting'}
        </div>
      </header>

      {/* ── Main ── */}
      <div className="main">
        {/* Graph */}
        <Graph
          data={graphData}
          highlightIds={highlightIds}
          selectedNode={selectedNode}
          onNodeClick={setSelectedNode}
        />

        {/* Legend */}
        <div className="legend">
          <div className="legend-item">
            <span className="legend-dot" style={{ background: '#4A9EFF' }} />
            omi_memory
          </div>
          <div className="legend-item">
            <span className="legend-dot" style={{ background: '#FF8C42' }} />
            ara_tool_call
          </div>
          <div className="legend-item">
            <span className="legend-dot" style={{ background: '#52D68A' }} />
            ara_observation / ara_message
          </div>
        </div>

        {/* Node detail panel */}
        <NodeDetail
          node={selectedNode}
          onClose={() => setSelectedNode(null)}
        />
      </div>
    </div>
  );
}

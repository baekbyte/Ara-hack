import React, { useState, useEffect, useCallback, useRef } from 'react';
import Graph, { EDGE_CONFIG } from './components/Graph.jsx';
import NodeDetail from './components/NodeDetail.jsx';
import { DUMMY_DATA } from './dummyData.js';

const POLL_INTERVAL = 2000;

export default function App() {
  const [graphData, setGraphData] = useState(DUMMY_DATA);
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
        const res = await fetch('/graph');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (!cancelled) {
          setGraphData(prev => {
            // Merge real nodes with dummy nodes — real data wins on ID collision.
            // Only trigger a re-render when the graph actually changes.
            const realNodes = data.nodes ?? [];
            const realEdges = data.edges ?? data.links ?? [];
            const realIds   = new Set(realNodes.map(n => n.id));
            const dummyNodes = DUMMY_DATA.nodes.filter(n => !realIds.has(n.id));
            const dummyEdges = DUMMY_DATA.edges.filter(e =>
              !realIds.has(e.source) && !realIds.has(e.target)
            );
            const mergedNodes = [...realNodes, ...dummyNodes];
            const mergedEdges = [...realEdges, ...dummyEdges];

            const prevIds     = new Set(prev.nodes?.map(n => n.id) ?? []);
            const prevEdgeLen = (prev.edges ?? prev.links ?? []).length;
            const same = mergedNodes.length === prevIds.size &&
                         mergedEdges.length === prevEdgeLen &&
                         mergedNodes.every(n => prevIds.has(n.id));
            return same ? prev : { nodes: mergedNodes, edges: mergedEdges };
          });
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
      // Always run client-side filter first so it works offline / with dummy data
      const lower = q.toLowerCase();
      const clientIds = new Set(
        graphData.nodes
          .filter(n => {
            const text = [n.content, n.node_type, n.type, n.id,
              ...(n.metadata ? Object.values(n.metadata).map(String) : []),
            ].join(' ').toLowerCase();
            return text.includes(lower);
          })
          .map(n => n.id)
      );

      // Try to enrich with semantic results from the backend
      try {
        const res = await fetch(`/query?q=${encodeURIComponent(q)}`);
        if (!res.ok) throw new Error();
        const data = await res.json();
        // /query returns { results: [{ node: {...}, score }], ... }
        const backendNodes = Array.isArray(data)   ? data
          : data.results ? data.results.map(r => r.node ?? r)
          : (data.nodes  ?? []);
        const backendIds = new Set(backendNodes.map(n => n.id).filter(Boolean));
        // Union: show both semantic hits and text matches
        const merged = new Set([...clientIds, ...backendIds]);
        setHighlightIds(merged);
        setSearchCount(merged.size);
      } catch {
        setHighlightIds(clientIds);
        setSearchCount(clientIds.size);
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
          <span className="header-title">Memory Galaxy</span>
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
          <div className="legend-section-title">Nodes</div>
          {[
            ['#4A9EFF', 'omi memory'],
            ['#6AB8FF', 'omi conversation'],
            ['#FF8C42', 'ara tool call'],
            ['#52D68A', 'ara message / obs'],
            ['#FFD166', 'task candidate'],
            ['#BB66FF', 'derived fact'],
          ].map(([color, label]) => (
            <div className="legend-item" key={label}>
              <span className="legend-dot" style={{ background: color, boxShadow: `0 0 6px ${color}` }} />
              {label}
            </div>
          ))}

          <div className="legend-divider" />
          <div className="legend-section-title">Edges</div>
          {Object.entries(EDGE_CONFIG).map(([type, cfg]) => {
            const hex = '#' + cfg.color.toString(16).padStart(6, '0');
            return (
              <div className="legend-item" key={type}>
                <span
                  className="legend-edge"
                  style={{
                    background: cfg.dashed
                      ? `repeating-linear-gradient(90deg, ${hex} 0px, ${hex} 5px, transparent 5px, transparent 9px)`
                      : hex,
                    opacity: cfg.baseOpacity + 0.2,
                  }}
                />
                {type}
              </div>
            );
          })}
        </div>

        {/* Controls hint */}
        <div className="controls-hint">
          <span>Drag to move</span>
          <span className="hint-sep">·</span>
          <span>Right drag to orbit</span>
          <span className="hint-sep">·</span>
          <span>Scroll to zoom</span>
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

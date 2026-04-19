import React, { useRef, useEffect, useCallback } from 'react';
import * as d3 from 'd3';

// ── Color mapping ─────────────────────────────────────────────────────────────
const NODE_COLORS = {
  omi_memory:      '#4A9EFF',
  ara_tool_call:   '#FF8C42',
  ara_observation: '#52D68A',
  ara_message:     '#52D68A',
};

function nodeColor(type) {
  return NODE_COLORS[type] ?? '#8A8A8A';
}

// ── Radius: map pagerank (0–1) to [6, 20] ────────────────────────────────────
function nodeRadius(node) {
  const score = node.pagerank ?? node.score ?? 0;
  return 6 + score * 14;
}

// ── Truncate text ─────────────────────────────────────────────────────────────
function truncate(str, n = 30) {
  if (!str) return '';
  return str.length > n ? str.slice(0, n) + '…' : str;
}

export default function Graph({ data, highlightIds, selectedNode, onNodeClick }) {
  const containerRef = useRef(null);
  const svgRef       = useRef(null);
  const simRef       = useRef(null);
  const zoomRef      = useRef(null);

  // Keep a mutable ref to the latest onNodeClick so D3 handlers don't stale-close
  const clickRef = useRef(onNodeClick);
  useEffect(() => { clickRef.current = onNodeClick; }, [onNodeClick]);

  // ── Build / update simulation whenever data changes ────────────────────────
  useEffect(() => {
    if (!containerRef.current) return;

    const nodes = (data.nodes ?? []).map((n) => ({ ...n }));
    const rawEdges = data.edges ?? data.links ?? [];
    const nodeById = new Map(nodes.map((n) => [n.id, n]));

    const links = rawEdges
      .map((e) => ({
        ...e,
        source: e.source ?? e.from,
        target: e.target ?? e.to,
      }))
      .filter((e) => nodeById.has(e.source) && nodeById.has(e.target));

    const W = containerRef.current.clientWidth  || 800;
    const H = containerRef.current.clientHeight || 600;

    // ── Clear previous SVG ───────────────────────────────────────────────────
    d3.select(containerRef.current).select('svg').remove();
    if (simRef.current) simRef.current.stop();

    if (nodes.length === 0) return;

    // ── Create SVG ───────────────────────────────────────────────────────────
    const svg = d3
      .select(containerRef.current)
      .append('svg')
      .attr('class', 'graph-svg')
      .attr('width', W)
      .attr('height', H);

    svgRef.current = svg;

    // Defs: glow filter
    const defs = svg.append('defs');
    defs.append('filter')
      .attr('id', 'glow-highlight')
      .html(`
        <feGaussianBlur stdDeviation="4" result="coloredBlur"/>
        <feMerge>
          <feMergeNode in="coloredBlur"/>
          <feMergeNode in="SourceGraphic"/>
        </feMerge>
      `);

    // Background star field (purely aesthetic)
    const starGroup = svg.append('g').attr('class', 'stars');
    d3.range(120).forEach(() => {
      const opacity = Math.random() * 0.5 + 0.05;
      const r       = Math.random() * 1.2 + 0.3;
      starGroup.append('circle')
        .attr('cx', Math.random() * W)
        .attr('cy', Math.random() * H)
        .attr('r',  r)
        .attr('fill', '#ffffff')
        .attr('opacity', opacity);
    });

    // Zoom container
    const g = svg.append('g').attr('class', 'zoom-root');

    // ── Zoom behaviour ───────────────────────────────────────────────────────
    const zoom = d3.zoom()
      .scaleExtent([0.1, 8])
      .on('zoom', (event) => g.attr('transform', event.transform));

    svg.call(zoom);
    zoomRef.current = zoom;

    // ── Link layer ───────────────────────────────────────────────────────────
    const linkSel = g.append('g').attr('class', 'links')
      .selectAll('line')
      .data(links)
      .join('line')
        .attr('stroke', '#3A3A5C')
        .attr('stroke-width', 1)
        .attr('stroke-opacity', (d) => Math.max(0.15, Math.min(1, d.weight ?? 0.5)));

    // ── Node layer ───────────────────────────────────────────────────────────
    const nodeSel = g.append('g').attr('class', 'nodes')
      .selectAll('g.node')
      .data(nodes, (d) => d.id)
      .join('g')
        .attr('class', 'node')
        .style('cursor', 'pointer');

    // Circle
    nodeSel.append('circle')
      .attr('r',    (d) => nodeRadius(d))
      .attr('fill', (d) => nodeColor(d.node_type ?? d.type))
      .attr('fill-opacity', 0.9)
      .attr('stroke', (d) => nodeColor(d.node_type ?? d.type))
      .attr('stroke-width', 1.5)
      .attr('stroke-opacity', 0.6);

    // Tooltip title (native browser tooltip via <title>)
    nodeSel.append('title')
      .text((d) => truncate(d.content ?? d.id, 30));

    // Click handler
    nodeSel.on('click', function (event, d) {
      event.stopPropagation();
      clickRef.current(d);
    });

    // Drag
    nodeSel.call(
      d3.drag()
        .on('start', (event, d) => {
          if (!event.active) sim.alphaTarget(0.3).restart();
          d.fx = d.x; d.fy = d.y;
        })
        .on('drag', (event, d) => {
          d.fx = event.x; d.fy = event.y;
        })
        .on('end', (event, d) => {
          if (!event.active) sim.alphaTarget(0);
          d.fx = null; d.fy = null;
        })
    );

    // Click on background deselects
    svg.on('click', () => clickRef.current(null));

    // ── Simulation ───────────────────────────────────────────────────────────
    const sim = d3.forceSimulation(nodes)
      .force('link',   d3.forceLink(links).id((d) => d.id).distance(80).strength(0.4))
      .force('charge', d3.forceManyBody().strength(-220))
      .force('center', d3.forceCenter(W / 2, H / 2))
      .force('collide', d3.forceCollide().radius((d) => nodeRadius(d) + 4))
      .on('tick', () => {
        linkSel
          .attr('x1', (d) => d.source.x)
          .attr('y1', (d) => d.source.y)
          .attr('x2', (d) => d.target.x)
          .attr('y2', (d) => d.target.y);

        nodeSel.attr('transform', (d) => `translate(${d.x},${d.y})`);
      });

    simRef.current = sim;

    return () => {
      sim.stop();
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  // ── Apply highlight / selection styles without re-running sim ──────────────
  useEffect(() => {
    if (!containerRef.current) return;

    d3.select(containerRef.current)
      .selectAll('g.node')
      .select('circle')
      .attr('filter', (d) => highlightIds.has(d.id) ? 'url(#glow-highlight)' : null)
      .attr('stroke', (d) => {
        if (selectedNode && d.id === selectedNode.id) return '#FFFFFF';
        return nodeColor(d.node_type ?? d.type);
      })
      .attr('stroke-width', (d) => {
        if (selectedNode && d.id === selectedNode.id) return 3;
        if (highlightIds.has(d.id)) return 2.5;
        return 1.5;
      })
      .attr('fill-opacity', (d) => {
        if (highlightIds.size === 0) return 0.9;
        return highlightIds.has(d.id) ? 1 : 0.25;
      });
  }, [highlightIds, selectedNode]);

  // ── Resize observer ────────────────────────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current) return;
    const obs = new ResizeObserver(() => {
      // Resize SVG to match container (simple approach)
      const el = containerRef.current;
      if (!el) return;
      d3.select(el).select('svg')
        .attr('width',  el.clientWidth)
        .attr('height', el.clientHeight);
      if (simRef.current) {
        simRef.current
          .force('center', d3.forceCenter(el.clientWidth / 2, el.clientHeight / 2))
          .alpha(0.1)
          .restart();
      }
    });
    obs.observe(containerRef.current);
    return () => obs.disconnect();
  }, []);

  const isEmpty  = (data.nodes ?? []).length === 0;

  return (
    <div className="graph-container" ref={containerRef}>
      {isEmpty && (
        <div className="graph-overlay">
          <div className="spinner" />
          <span>Waiting for memory nodes&hellip;</span>
        </div>
      )}
    </div>
  );
}

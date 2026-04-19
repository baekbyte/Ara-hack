import { useMemo, useRef, useEffect } from 'react'
import ForceGraph3D from 'react-force-graph-3d'
import * as THREE from 'three'

const NODE_COLORS = {
  omi_memory: '#4A9EFF',
  ara_tool_call: '#FF8C42',
  ara_message: '#FF8C42',
  ara_observation: '#50C878',
}

const EDGE_COLORS = {
  semantic: 'rgba(255,255,255,0.25)',
  temporal: 'rgba(100,180,255,0.2)',
  causal: 'rgba(255,200,50,0.5)',
}

function makeNodeObject(node) {
  const group = new THREE.Group()
  const r = Math.sqrt(node.val) * 0.35 + 0.8

  // Core
  group.add(new THREE.Mesh(
    new THREE.SphereGeometry(r, 16, 16),
    new THREE.MeshBasicMaterial({ color: node.color }),
  ))

  // Glow halo
  group.add(new THREE.Mesh(
    new THREE.SphereGeometry(r * 1.6, 12, 12),
    new THREE.MeshBasicMaterial({ color: node.color, transparent: true, opacity: 0.12 }),
  ))

  return group
}

export default function Constellation({ graphData, highlightedIds, onNodeClick }) {
  const fgRef = useRef()

  // Slowly rotate the scene when idle
  useEffect(() => {
    let frame
    const animate = () => {
      if (fgRef.current) {
        fgRef.current.scene().rotation.y += 0.0003
      }
      frame = requestAnimationFrame(animate)
    }
    frame = requestAnimationFrame(animate)
    return () => cancelAnimationFrame(frame)
  }, [])

  const { nodes, links } = useMemo(() => {
    const searching = highlightedIds.size > 0
    const nodes = graphData.nodes.map(n => ({
      ...n,
      color: searching
        ? (highlightedIds.has(n.id) ? '#FFD700' : '#222')
        : (NODE_COLORS[n.node_type] ?? '#888'),
      val: 1 + (n.importance ?? 0) * 30,
    }))
    const nodeIds = new Set(nodes.map(n => n.id))
    const links = graphData.edges
      .filter(e => nodeIds.has(e.source) && nodeIds.has(e.target))
      .map(e => ({
        source: e.source,
        target: e.target,
        color: EDGE_COLORS[e.edge_type] ?? 'rgba(255,255,255,0.15)',
        width: e.edge_type === 'causal' ? 2 : 1,
      }))
    return { nodes, links }
  }, [graphData, highlightedIds])

  return (
    <ForceGraph3D
      ref={fgRef}
      graphData={{ nodes, links }}
      nodeLabel={n => n.content.slice(0, 120)}
      nodeColor={n => n.color}
      nodeVal={n => n.val}
      nodeThreeObject={makeNodeObject}
      nodeThreeObjectExtend={false}
      linkColor={l => l.color}
      linkWidth={l => l.width}
      linkOpacity={0.6}
      backgroundColor="#050510"
      onNodeClick={onNodeClick}
      enableNodeDrag={true}
      showNavInfo={false}
    />
  )
}

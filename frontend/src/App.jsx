import { useState, useEffect, useCallback } from 'react'
import Constellation from './components/Constellation'
import NodePanel from './components/NodePanel'
import SearchBar from './components/SearchBar'
import Legend from './components/Legend'

const API = 'http://localhost:8000'

export default function App() {
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] })
  const [selectedNode, setSelectedNode] = useState(null)
  const [highlightedIds, setHighlightedIds] = useState(new Set())
  const [nodeCount, setNodeCount] = useState(0)

  useEffect(() => {
    const poll = async () => {
      try {
        const res = await fetch(`${API}/graph`)
        const data = await res.json()
        setGraphData(data)
        setNodeCount(data.nodes.length)
      } catch {
        // server not yet up
      }
    }
    poll()
    const id = setInterval(poll, 2000)
    return () => clearInterval(id)
  }, [])

  const handleSearch = useCallback(async (query) => {
    if (!query.trim()) {
      setHighlightedIds(new Set())
      return
    }
    try {
      const res = await fetch(`${API}/query?q=${encodeURIComponent(query)}`)
      const data = await res.json()
      setHighlightedIds(new Set(data.results.map(r => r.id)))
    } catch {
      setHighlightedIds(new Set())
    }
  }, [])

  return (
    <div style={{ width: '100vw', height: '100vh', background: '#050510', position: 'relative' }}>
      <header style={{
        position: 'absolute', top: 0, left: 0, right: 0, zIndex: 10,
        padding: '14px 20px', display: 'flex', alignItems: 'center', gap: 20,
        background: 'linear-gradient(to bottom, rgba(5,5,16,0.9) 0%, transparent 100%)',
        pointerEvents: 'none',
      }}>
        <span style={{ color: '#fff', fontWeight: 700, fontSize: 18, letterSpacing: 2, pointerEvents: 'none' }}>
          MEMORY PALACE
        </span>
        <span style={{ color: '#444', fontSize: 12 }}>
          {nodeCount} node{nodeCount !== 1 ? 's' : ''}
        </span>
      </header>

      <div style={{ position: 'absolute', top: 20, left: '50%', transform: 'translateX(-50%)', zIndex: 10 }}>
        <SearchBar onSearch={handleSearch} />
      </div>

      <Constellation
        graphData={graphData}
        highlightedIds={highlightedIds}
        onNodeClick={setSelectedNode}
      />

      <Legend />

      {selectedNode && (
        <NodePanel node={selectedNode} onClose={() => setSelectedNode(null)} />
      )}
    </div>
  )
}

export const DUMMY_DATA = {
  nodes: [
    // ── Omi memories ──────────────────────────────────────────────────────
    {
      id: 'd-n1',
      node_type: 'omi_memory',
      source: 'omi',
      content: 'Team meeting about Ara integration roadmap and memory architecture',
      timestamp: '2024-04-19T09:15:00Z',
      pagerank: 0.85,
    },
    {
      id: 'd-n2',
      node_type: 'omi_memory',
      source: 'omi',
      content: 'Discussed compounding memory design with Nathan and Alice',
      timestamp: '2024-04-19T10:30:00Z',
      pagerank: 0.62,
    },
    {
      id: 'd-n3',
      node_type: 'omi_memory',
      source: 'omi',
      content: 'Reviewed hackathon demo script and submission requirements',
      timestamp: '2024-04-19T14:00:00Z',
      pagerank: 0.40,
    },
    {
      id: 'd-n4',
      node_type: 'omi_memory',
      source: 'omi',
      content: 'Call with investors — AI memory product vision and roadmap',
      timestamp: '2024-04-19T16:45:00Z',
      pagerank: 0.72,
    },
    // ── Omi conversations ─────────────────────────────────────────────────
    {
      id: 'd-n5',
      node_type: 'omi_conversation',
      source: 'omi',
      content: 'Morning standup — sprint planning and task assignments',
      timestamp: '2024-04-19T08:00:00Z',
      pagerank: 0.50,
    },
    {
      id: 'd-n6',
      node_type: 'omi_conversation',
      source: 'omi',
      content: 'Pair programming session on the graph retrieval module',
      timestamp: '2024-04-19T11:00:00Z',
      pagerank: 0.44,
    },
    // ── Omi transcript chunks ─────────────────────────────────────────────
    {
      id: 'd-n7',
      node_type: 'omi_transcript_chunk',
      source: 'omi',
      content: '...the key insight is that memories should compound over time...',
      timestamp: '2024-04-19T10:32:00Z',
      pagerank: 0.28,
    },
    {
      id: 'd-n8',
      node_type: 'omi_transcript_chunk',
      source: 'omi',
      content: '...semantic search alone isn\'t enough, we need temporal context too...',
      timestamp: '2024-04-19T10:35:00Z',
      pagerank: 0.22,
    },
    // ── Ara tool calls ────────────────────────────────────────────────────
    {
      id: 'd-n9',
      node_type: 'ara_tool_call',
      source: 'ara',
      content: 'search_web: latest LLM long-term memory techniques 2024',
      timestamp: '2024-04-19T09:20:00Z',
      pagerank: 0.45,
    },
    {
      id: 'd-n10',
      node_type: 'ara_tool_call',
      source: 'ara',
      content: 'read_file: palace.py — analyzing ingestion pipeline',
      timestamp: '2024-04-19T09:25:00Z',
      pagerank: 0.38,
    },
    {
      id: 'd-n11',
      node_type: 'ara_tool_call',
      source: 'ara',
      content: 'query_memory_palace: what did the team discuss about embeddings?',
      timestamp: '2024-04-19T14:05:00Z',
      pagerank: 0.55,
    },
    // ── Ara messages ──────────────────────────────────────────────────────
    {
      id: 'd-n12',
      node_type: 'ara_message',
      source: 'ara',
      content: 'Found 3 key integration points in the codebase for memory hooks',
      timestamp: '2024-04-19T09:30:00Z',
      pagerank: 0.68,
    },
    {
      id: 'd-n13',
      node_type: 'ara_message',
      source: 'ara',
      content: 'Memory Palace is primed for the live demo — all systems nominal',
      timestamp: '2024-04-19T17:00:00Z',
      pagerank: 0.60,
    },
    // ── Ara observations ──────────────────────────────────────────────────
    {
      id: 'd-n14',
      node_type: 'ara_observation',
      source: 'ara',
      content: 'User prefers concise responses with inline code examples',
      timestamp: '2024-04-19T10:00:00Z',
      pagerank: 0.48,
    },
    {
      id: 'd-n15',
      node_type: 'ara_observation',
      source: 'ara',
      content: 'PageRank scoring significantly improves retrieval relevance',
      timestamp: '2024-04-19T11:30:00Z',
      pagerank: 0.42,
    },
    // ── Task candidates ───────────────────────────────────────────────────
    {
      id: 'd-n16',
      node_type: 'task_candidate',
      source: 'derived',
      content: 'Implement vector search for real-time memory retrieval',
      timestamp: '2024-04-19T09:18:00Z',
      pagerank: 0.35,
    },
    {
      id: 'd-n17',
      node_type: 'task_candidate',
      source: 'derived',
      content: 'Add WebSocket support for live graph streaming',
      timestamp: '2024-04-19T14:10:00Z',
      pagerank: 0.30,
    },
    // ── Derived facts ─────────────────────────────────────────────────────
    {
      id: 'd-n18',
      node_type: 'derived_fact',
      source: 'derived',
      content: 'Person: Alice — mentioned 4 times across sessions',
      timestamp: '2024-04-19T09:16:00Z',
      pagerank: 0.58,
    },
    {
      id: 'd-n19',
      node_type: 'derived_fact',
      source: 'derived',
      content: 'Person: Nathan — project lead, architecture decisions',
      timestamp: '2024-04-19T10:31:00Z',
      pagerank: 0.52,
    },
  ],

  edges: [
    // temporal — narrative chain
    { id: 'de-1',  source: 'd-n5',  target: 'd-n1',  edge_type: 'temporal',        weight: 1.0 },
    { id: 'de-2',  source: 'd-n1',  target: 'd-n2',  edge_type: 'temporal',        weight: 1.0 },
    { id: 'de-3',  source: 'd-n2',  target: 'd-n6',  edge_type: 'temporal',        weight: 1.0 },
    { id: 'de-4',  source: 'd-n3',  target: 'd-n4',  edge_type: 'temporal',        weight: 1.0 },
    { id: 'de-5',  source: 'd-n9',  target: 'd-n12', edge_type: 'temporal',        weight: 1.0 },
    // semantic — conceptual similarity
    { id: 'de-6',  source: 'd-n1',  target: 'd-n9',  edge_type: 'semantic',        weight: 0.82 },
    { id: 'de-7',  source: 'd-n2',  target: 'd-n12', edge_type: 'semantic',        weight: 0.78 },
    { id: 'de-8',  source: 'd-n1',  target: 'd-n2',  edge_type: 'semantic',        weight: 0.90 },
    { id: 'de-9',  source: 'd-n4',  target: 'd-n13', edge_type: 'semantic',        weight: 0.70 },
    { id: 'de-10', source: 'd-n9',  target: 'd-n10', edge_type: 'semantic',        weight: 0.65 },
    { id: 'de-11', source: 'd-n14', target: 'd-n15', edge_type: 'semantic',        weight: 0.72 },
    // same session — transcript clustering
    { id: 'de-12', source: 'd-n7',  target: 'd-n8',  edge_type: 'same_session',    weight: 1.0 },
    { id: 'de-13', source: 'd-n2',  target: 'd-n7',  edge_type: 'same_session',    weight: 0.95 },
    { id: 'de-14', source: 'd-n2',  target: 'd-n8',  edge_type: 'same_session',    weight: 0.95 },
    // related action — Ara ↔ Omi linkage
    { id: 'de-15', source: 'd-n9',  target: 'd-n1',  edge_type: 'related_action',  weight: 0.74 },
    { id: 'de-16', source: 'd-n11', target: 'd-n2',  edge_type: 'related_action',  weight: 0.68 },
    { id: 'de-17', source: 'd-n10', target: 'd-n12', edge_type: 'related_action',  weight: 0.60 },
    // derived from — entity / task back-links
    { id: 'de-18', source: 'd-n18', target: 'd-n1',  edge_type: 'derived_from',    weight: 1.0 },
    { id: 'de-19', source: 'd-n19', target: 'd-n2',  edge_type: 'derived_from',    weight: 1.0 },
    { id: 'de-20', source: 'd-n16', target: 'd-n12', edge_type: 'derived_from',    weight: 1.0 },
    { id: 'de-21', source: 'd-n17', target: 'd-n13', edge_type: 'derived_from',    weight: 1.0 },
    // contains task
    { id: 'de-22', source: 'd-n16', target: 'd-n1',  edge_type: 'contains_task',   weight: 0.88 },
    { id: 'de-23', source: 'd-n17', target: 'd-n11', edge_type: 'contains_task',   weight: 0.80 },
    // mentions person
    { id: 'de-24', source: 'd-n18', target: 'd-n2',  edge_type: 'mentions_person', weight: 0.85 },
    { id: 'de-25', source: 'd-n19', target: 'd-n1',  edge_type: 'mentions_person', weight: 0.85 },
    // causal
    { id: 'de-26', source: 'd-n12', target: 'd-n13', edge_type: 'causal',          weight: 0.76 },
    { id: 'de-27', source: 'd-n1',  target: 'd-n16', edge_type: 'causal',          weight: 0.65 },
  ],
};

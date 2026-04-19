from dotenv import load_dotenv
load_dotenv()

import os
import uvicorn
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from ingest import ingest_omi_memory, ingest_ara_event, embed, find_neighbors
from graph import memory_graph

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AraEvent(BaseModel):
    event_type: str
    input: str
    output: str


@app.post("/webhook/omi")
async def webhook_omi(payload: dict):
    node = ingest_omi_memory(payload)
    return {"status": "ok", "node_id": node.id}


@app.post("/webhook/ara")
async def webhook_ara(event: AraEvent):
    node = ingest_ara_event(event.event_type, event.input, event.output)
    return {"status": "ok", "node_id": node.id}


@app.get("/graph")
async def get_graph():
    pagerank = memory_graph.compute_pagerank()
    nodes = [
        {
            "id": node.id,
            "content": node.content,
            "node_type": node.node_type,
            "source": node.source,
            "timestamp": node.timestamp,
            "metadata": node.metadata,
            "pagerank": pagerank.get(node.id, 0.0),
        }
        for node in memory_graph.get_all_nodes()
    ]
    edges = [
        {
            "source_id": edge.source_id,
            "target_id": edge.target_id,
            "edge_type": edge.edge_type,
            "weight": edge.weight,
        }
        for edge in memory_graph.get_all_edges()
    ]
    return {"nodes": nodes, "edges": edges}


@app.get("/query")
async def query(q: str = Query(...)):
    embedding = embed(q)
    neighbors = find_neighbors(embedding, k=10)
    results = [{"node": {
        "id": node.id,
        "content": node.content,
        "node_type": node.node_type,
        "source": node.source,
        "timestamp": node.timestamp,
        "metadata": node.metadata,
    }, "score": score} for node, score in neighbors]
    return {"results": results}


PALACE_URL = "http://localhost:8000"

GRAPH_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Memory Palace</title>
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: #0d0d0d; color: #fff; font-family: -apple-system, sans-serif; overflow: hidden; }
  #header { padding: 12px 20px; display: flex; align-items: center; gap: 16px; border-bottom: 1px solid #222; }
  #header h1 { font-size: 16px; font-weight: 600; letter-spacing: 0.05em; }
  #stats { font-size: 12px; color: #666; }
  #search { margin-left: auto; background: #1a1a1a; border: 1px solid #333; border-radius: 6px; padding: 6px 12px; color: #fff; font-size: 13px; width: 220px; outline: none; }
  #search:focus { border-color: #555; }
  #canvas { width: 100vw; height: calc(100vh - 49px); }
  #panel { position: fixed; top: 49px; right: 0; width: 300px; height: calc(100vh - 49px); background: #111; border-left: 1px solid #222; padding: 20px; overflow-y: auto; transform: translateX(100%); transition: transform 0.2s; }
  #panel.open { transform: translateX(0); }
  #panel-close { position: absolute; top: 12px; right: 14px; cursor: pointer; color: #666; font-size: 18px; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; margin-bottom: 10px; }
  .badge.omi { background: #1a3a5c; color: #4a9eff; }
  .badge.ara { background: #3a2010; color: #ff8c42; }
  .content { font-size: 13px; line-height: 1.6; color: #ccc; margin: 10px 0; background: #1a1a1a; padding: 10px; border-radius: 6px; word-break: break-word; }
  .meta-row { font-size: 11px; color: #555; margin-top: 4px; }
  .legend { position: fixed; bottom: 20px; left: 20px; display: flex; gap: 16px; }
  .legend-item { display: flex; align-items: center; gap: 6px; font-size: 11px; color: #888; }
  .dot { width: 10px; height: 10px; border-radius: 50%; }
</style>
</head>
<body>
<div id="header">
  <h1>Memory Palace</h1>
  <span id="stats">loading...</span>
  <input id="search" type="text" placeholder="Search memories..." />
</div>
<svg id="canvas"></svg>
<div id="panel">
  <span id="panel-close">×</span>
  <div id="panel-content"></div>
</div>
<div class="legend">
  <div class="legend-item"><div class="dot" style="background:#4a9eff"></div>Omi Memory</div>
  <div class="legend-item"><div class="dot" style="background:#ff8c42"></div>Ara Action</div>
  <div class="legend-item"><div class="dot" style="background:#52d68a"></div>Ara Observation</div>
</div>
<script>
const PALACE_URL = "PALACE_URL_PLACEHOLDER";
const color = n => n.source === "omi" ? "#4a9eff" : n.node_type === "ara_observation" ? "#52d68a" : "#ff8c42";
const radius = pr => 6 + Math.min(pr * 800, 14);
let sim, nodes = [], edges = [], highlighted = new Set();
const svg = d3.select("#canvas");
const g = svg.append("g");
svg.call(d3.zoom().scaleExtent([0.2, 4]).on("zoom", e => g.attr("transform", e.transform)));
const linkSel = g.append("g").attr("stroke", "#333").attr("stroke-opacity", 0.6);
const nodeSel = g.append("g");
function update(data) {
  nodes = data.nodes; edges = data.edges;
  document.getElementById("stats").textContent = nodes.length + " nodes · " + edges.length + " edges";
  const link = linkSel.selectAll("line").data(edges, d => d.source_id + d.target_id);
  link.enter().append("line").attr("stroke-width", d => d.weight * 1.5);
  link.exit().remove();
  const node = nodeSel.selectAll("circle").data(nodes, d => d.id);
  const enter = node.enter().append("circle")
    .attr("r", d => radius(d.pagerank || 0)).attr("fill", d => color(d))
    .attr("stroke", "#000").attr("stroke-width", 1.5).style("cursor", "pointer")
    .call(d3.drag().on("start", (e,d) => { if(!e.active) sim.alphaTarget(0.3).restart(); d.fx=d.x; d.fy=d.y; })
      .on("drag", (e,d) => { d.fx=e.x; d.fy=e.y; })
      .on("end", (e,d) => { if(!e.active) sim.alphaTarget(0); d.fx=null; d.fy=null; }))
    .on("click", (_, d) => {
      document.getElementById("panel-content").innerHTML =
        '<span class="badge ' + (d.source==="omi"?"omi":"ara") + '">' + (d.source==="omi"?"Omi Memory":"Ara Action") + '</span>' +
        '<div class="content">' + d.content + '</div>' +
        '<div class="meta-row">Type: ' + d.node_type + '</div>' +
        '<div class="meta-row">Time: ' + new Date(d.timestamp).toLocaleString() + '</div>' +
        '<div class="meta-row">PageRank: ' + (d.pagerank||0).toFixed(4) + '</div>';
      document.getElementById("panel").classList.add("open");
    });
  enter.append("title").text(d => d.content.slice(0, 60));
  node.exit().remove();
  if (sim) { sim.nodes(nodes); sim.force("link").links(edges.map(e=>({source:e.source_id,target:e.target_id,weight:e.weight}))); sim.alpha(0.3).restart(); }
  else {
    sim = d3.forceSimulation(nodes)
      .force("link", d3.forceLink(edges.map(e=>({source:e.source_id,target:e.target_id,weight:e.weight}))).id(d=>d.id).distance(120))
      .force("charge", d3.forceManyBody().strength(-200))
      .force("center", d3.forceCenter(window.innerWidth/2, (window.innerHeight-49)/2))
      .on("tick", () => {
        linkSel.selectAll("line")
          .attr("x1", d => { const s=nodes.find(n=>n.id===d.source_id); return s?s.x:0; })
          .attr("y1", d => { const s=nodes.find(n=>n.id===d.source_id); return s?s.y:0; })
          .attr("x2", d => { const t=nodes.find(n=>n.id===d.target_id); return t?t.x:0; })
          .attr("y2", d => { const t=nodes.find(n=>n.id===d.target_id); return t?t.y:0; });
        nodeSel.selectAll("circle").attr("cx", d=>d.x).attr("cy", d=>d.y);
      });
  }
  nodeSel.selectAll("circle").attr("opacity", d => highlighted.size===0||highlighted.has(d.id)?1:0.15)
    .attr("filter", d => highlighted.has(d.id)?"drop-shadow(0 0 8px #fff)":null);
}
document.getElementById("panel-close").onclick = () => document.getElementById("panel").classList.remove("open");
let t;
document.getElementById("search").addEventListener("input", e => {
  clearTimeout(t);
  const q = e.target.value.trim();
  if (!q) { highlighted.clear(); nodeSel.selectAll("circle").attr("opacity",1).attr("filter",null); return; }
  t = setTimeout(() => fetch(PALACE_URL+"/query?q="+encodeURIComponent(q)).then(r=>r.json()).then(d => {
    highlighted = new Set(d.results.map(r=>r.node.id));
    nodeSel.selectAll("circle").attr("opacity", d => highlighted.has(d.id)?1:0.15).attr("filter", d => highlighted.has(d.id)?"drop-shadow(0 0 8px #fff)":null);
  }), 400);
});
function poll() { fetch(PALACE_URL+"/graph").then(r=>r.json()).then(update).catch(()=>{}); }
poll(); setInterval(poll, 2000);
</script>
</body>
</html>"""


@app.get("/palace", response_class=HTMLResponse)
async def palace_ui():
    return GRAPH_HTML.replace("PALACE_URL_PLACEHOLDER", PALACE_URL)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

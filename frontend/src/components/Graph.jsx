import React, { useRef, useEffect, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { CSS2DRenderer, CSS2DObject } from 'three/examples/jsm/renderers/CSS2DRenderer.js';
import * as d3 from 'd3';

// ── Tight glow texture — bright core, fast falloff ────────────────────────────
function makeGlowTexture() {
  const size = 128;
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = size;
  const ctx = canvas.getContext('2d');
  const cx = size / 2;
  const g = ctx.createRadialGradient(cx, cx, 0, cx, cx, cx);
  g.addColorStop(0,    'rgba(255,255,255,1)');
  g.addColorStop(0.08, 'rgba(255,255,255,0.92)');
  g.addColorStop(0.22, 'rgba(255,255,255,0.48)');
  g.addColorStop(0.48, 'rgba(255,255,255,0.09)');
  g.addColorStop(0.72, 'rgba(255,255,255,0.02)');
  g.addColorStop(1,    'rgba(255,255,255,0)');
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, size, size);
  return new THREE.CanvasTexture(canvas);
}
const GLOW_TEX = makeGlowTexture();

// ── Colors ────────────────────────────────────────────────────────────────────
const NODE_HEX = {
  omi_memory:           0x4A9EFF,
  omi_transcript_chunk: 0x5588DD,
  omi_conversation:     0x6AB8FF,
  ara_tool_call:        0xFF8C42,
  ara_observation:      0x52D68A,
  ara_message:          0x52D68A,
  task_candidate:       0xFFD166,
  derived_fact:         0xBB66FF,
};
const NODE_CSS = {
  omi_memory:           '#4A9EFF',
  omi_transcript_chunk: '#5588DD',
  omi_conversation:     '#6AB8FF',
  ara_tool_call:        '#FF8C42',
  ara_observation:      '#52D68A',
  ara_message:          '#52D68A',
  task_candidate:       '#FFD166',
  derived_fact:         '#BB66FF',
};

export const EDGE_CONFIG = {
  semantic:        { color: 0x4A9EFF, baseOpacity: 0.42, dashed: false, pulseSpeed: 0.18 },
  temporal:        { color: 0xCCDDFF, baseOpacity: 0.62, dashed: false, pulseSpeed: 0.40 },
  derived_from:    { color: 0xBB66FF, baseOpacity: 0.36, dashed: true,  pulseSpeed: 0.12 },
  same_session:    { color: 0x44DDCC, baseOpacity: 0.36, dashed: false, pulseSpeed: 0.22 },
  related_action:  { color: 0xFF8C42, baseOpacity: 0.36, dashed: true,  pulseSpeed: 0.20 },
  mentions_person: { color: 0xFFD166, baseOpacity: 0.24, dashed: true,  pulseSpeed: 0.10 },
  contains_task:   { color: 0x98FB98, baseOpacity: 0.24, dashed: true,  pulseSpeed: 0.10 },
};

const getHex    = t => NODE_HEX[t] ?? 0x888888;
const getCSS    = t => NODE_CSS[t] ?? '#888888';
const getEdgeCfg = t => EDGE_CONFIG[t] ?? { color: 0x2A3A55, baseOpacity: 0.12, dashed: false, pulseSpeed: 0.14 };
const nodeBaseR  = n => 5 + (n.pagerank ?? n.score ?? 0) * 13;
const trunc      = (s, n = 32) => !s ? '' : s.length > n ? s.slice(0, n) + '…' : s;

function makeSprite(hex, opacity) {
  return new THREE.Sprite(new THREE.SpriteMaterial({
    map: GLOW_TEX, color: new THREE.Color(hex),
    transparent: true, blending: THREE.AdditiveBlending,
    depthWrite: false, opacity,
  }));
}

// ── Component ─────────────────────────────────────────────────────────────────
export default function Graph({ data, highlightIds, selectedNode, onNodeClick }) {
  const containerRef = useRef(null);
  const threeRef     = useRef(null);
  const nodeMapRef   = useRef(new Map()); // id → { group, glow, core, baseGlowScale, breathPhase, scaleMult }
  const pulsesRef    = useRef([]);
  const clickRef     = useRef(onNodeClick);
  const prevSigRef   = useRef('');
  const [tooltip, setTooltip] = useState(null); // { node, x, y }

  useEffect(() => { clickRef.current = onNodeClick; }, [onNodeClick]);

  // ── One-time setup ────────────────────────────────────────────────────────
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const W = container.clientWidth  || 800;
    const H = container.clientHeight || 600;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(W, H);
    renderer.setClearColor(0x000000, 0);
    container.appendChild(renderer.domElement);

    const labelRenderer = new CSS2DRenderer();
    labelRenderer.setSize(W, H);
    Object.assign(labelRenderer.domElement.style, {
      position: 'absolute', top: '0', left: '0',
      pointerEvents: 'none', overflow: 'hidden',
    });
    container.appendChild(labelRenderer.domElement);

    const scene  = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(58, W / H, 1, 6000);
    camera.position.z = 620;

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping    = true;
    controls.dampingFactor    = 0.07;
    controls.autoRotate       = true;
    controls.autoRotateSpeed  = 0.12;
    controls.minDistance      = 80;
    controls.maxDistance      = 2800;
    controls.enablePan          = true;
    controls.screenSpacePanning = true;
    controls.panSpeed           = 1.2;
    // Left drag → pan (grab & move), right drag → rotate, scroll → zoom
    controls.mouseButtons = {
      LEFT:   THREE.MOUSE.PAN,
      MIDDLE: THREE.MOUSE.DOLLY,
      RIGHT:  THREE.MOUSE.ROTATE,
    };
    renderer.domElement.addEventListener('contextmenu', e => e.preventDefault());

    let lastInteract = -Infinity;
    renderer.domElement.addEventListener('pointerdown', () => {
      lastInteract = performance.now();
      controls.autoRotate = false;
    });

    const nodeGroup  = new THREE.Group();
    const edgeGroup  = new THREE.Group();
    const pulseGroup = new THREE.Group();
    scene.add(edgeGroup, pulseGroup, nodeGroup);

    // Click
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();
    let mdX = 0, mdY = 0;
    renderer.domElement.addEventListener('mousedown', e => { mdX = e.clientX; mdY = e.clientY; });
    renderer.domElement.addEventListener('click', e => {
      if (Math.hypot(e.clientX - mdX, e.clientY - mdY) > 6) return;
      const rect = renderer.domElement.getBoundingClientRect();
      mouse.x =  ((e.clientX - rect.left) / rect.width)  * 2 - 1;
      mouse.y = -((e.clientY - rect.top)  / rect.height) * 2 + 1;
      raycaster.setFromCamera(mouse, camera);
      const cores = [...nodeMapRef.current.values()].map(v => v.core);
      const hits  = raycaster.intersectObjects(cores, false);
      clickRef.current(hits.length > 0 ? hits[0].object.userData.node : null);
    });

    // Hover tooltip via mousemove raycasting
    const hoverRay   = new THREE.Raycaster();
    const hoverMouse = new THREE.Vector2();
    renderer.domElement.addEventListener('mousemove', e => {
      const rect = renderer.domElement.getBoundingClientRect();
      hoverMouse.x =  ((e.clientX - rect.left) / rect.width)  * 2 - 1;
      hoverMouse.y = -((e.clientY - rect.top)  / rect.height) * 2 + 1;
      hoverRay.setFromCamera(hoverMouse, camera);
      const cores = [...nodeMapRef.current.values()].map(v => v.core);
      const hits  = hoverRay.intersectObjects(cores, false);
      setTooltip(hits.length > 0
        ? { node: hits[0].object.userData.node, x: e.clientX, y: e.clientY }
        : null
      );
    });
    renderer.domElement.addEventListener('mouseleave', () => setTooltip(null));

    let animId;
    const clock = new THREE.Clock();
    const animate = () => {
      animId = requestAnimationFrame(animate);
      const t = clock.getElapsedTime();

      if (!controls.autoRotate && performance.now() - lastInteract > 8000) {
        controls.autoRotate = true;
      }

      // Breathing: only the glow layer pulses, core stays crisp
      nodeMapRef.current.forEach(info => {
        const breathe = 1 + 0.14 * Math.sin(t * 1.15 + info.breathPhase);
        const s = info.baseGlowScale * breathe * (info.scaleMult ?? 1);
        info.glow.scale.set(s, s, 1);
      });

      // Pulse dots along edges
      pulsesRef.current.forEach(p => {
        p.progress += p.speed * 0.016;
        if (p.progress >= 1) p.progress = 0;
        p.sprite.position.lerpVectors(p.srcPos, p.tgtPos, p.progress);
        p.sprite.material.opacity = 0.85 * Math.sin(p.progress * Math.PI);
      });

      // Fade labels out as user zooms away
      const dist = camera.position.distanceTo(controls.target);
      const labelOpacity = THREE.MathUtils.clamp(1 - (dist - 450) / 350, 0, 1);
      labelRenderer.domElement.style.opacity = String(labelOpacity);

      controls.update();
      renderer.render(scene, camera);
      labelRenderer.render(scene, camera);
    };
    animate();

    const resizeObs = new ResizeObserver(() => {
      const w = container.clientWidth, h = container.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
      labelRenderer.setSize(w, h);
    });
    resizeObs.observe(container);

    threeRef.current = { renderer, labelRenderer, scene, camera, controls, nodeGroup, edgeGroup, pulseGroup };

    return () => {
      cancelAnimationFrame(animId);
      resizeObs.disconnect();
      controls.dispose();
      renderer.dispose();
      if (container.contains(renderer.domElement))      container.removeChild(renderer.domElement);
      if (container.contains(labelRenderer.domElement)) container.removeChild(labelRenderer.domElement);
      threeRef.current = null;
    };
  }, []);

  // ── Rebuild when data changes ─────────────────────────────────────────────
  useEffect(() => {
    if (!threeRef.current) return;
    const { nodeGroup, edgeGroup, pulseGroup } = threeRef.current;
    const nodes    = data.nodes ?? [];
    const rawEdges = data.edges ?? data.links ?? [];

    const sig = `${nodes.length}:${rawEdges.length}`;
    if (sig === prevSigRef.current) return;
    prevSigRef.current = sig;

    // Clear
    nodeMapRef.current.forEach(({ group }) => nodeGroup.remove(group));
    nodeMapRef.current.clear();
    while (edgeGroup.children.length) {
      const c = edgeGroup.children[0];
      c.geometry?.dispose(); c.material?.dispose(); edgeGroup.remove(c);
    }
    pulsesRef.current.forEach(p => { pulseGroup.remove(p.sprite); p.sprite.material.dispose(); });
    pulsesRef.current = [];
    if (!nodes.length) return;

    // D3 force layout
    const simNodes = nodes.map(n => ({ ...n, _z: (Math.random() - 0.5) * 80 }));
    const nodeById = new Map(simNodes.map(n => [n.id, n]));
    const simLinks = rawEdges
      .map(e => ({ ...e, source: e.source ?? e.from, target: e.target ?? e.to }))
      .filter(e => nodeById.has(e.source) && nodeById.has(e.target));

    d3.forceSimulation(simNodes)
      .force('link',    d3.forceLink(simLinks).id(d => d.id).distance(110).strength(0.30))
      .force('charge',  d3.forceManyBody().strength(-280))
      .force('center',  d3.forceCenter(0, 0))
      .force('collide', d3.forceCollide().radius(d => nodeBaseR(d) + 8))
      .stop().tick(300);

    // Nodes — glow corona + crisp core + always-on label
    simNodes.forEach(n => {
      const baseR  = nodeBaseR(n);
      const hex    = getHex(n.node_type ?? n.type);
      const cssCol = getCSS(n.node_type ?? n.type);

      const glow = makeSprite(hex, 0.48);
      const baseGlowScale = baseR * 3.2;
      glow.scale.set(baseGlowScale, baseGlowScale, 1);

      const core = makeSprite(hex, 1.0);
      core.scale.set(baseR * 1.1, baseR * 1.1, 1);
      core.userData.node = n;

      // Always-on label
      const div = document.createElement('div');
      div.className = 'node-label';

      const typeEl = document.createElement('span');
      typeEl.className = 'node-label-type';
      typeEl.textContent = (n.node_type ?? n.type ?? 'node').replace(/_/g, ' ');
      typeEl.style.color = cssCol;

      const contentEl = document.createElement('span');
      contentEl.className = 'node-label-content';
      contentEl.textContent = trunc(n.content ?? n.id, 22);

      div.appendChild(typeEl);
      div.appendChild(contentEl);

      const labelObj = new CSS2DObject(div);
      labelObj.position.set(0, -(baseR * 1.5 + 6), 0);

      const group = new THREE.Group();
      group.add(glow, core, labelObj);
      group.position.set(n.x ?? 0, n.y ?? 0, n._z ?? 0);
      nodeGroup.add(group);

      nodeMapRef.current.set(n.id, {
        group, glow, core, labelDiv: div, baseGlowScale,
        breathPhase: Math.random() * Math.PI * 2,
        scaleMult: 1,
      });
    });

    // Edges + pulse dots
    simLinks.forEach(link => {
      const srcId = typeof link.source === 'object' ? link.source.id : link.source;
      const tgtId = typeof link.target === 'object' ? link.target.id : link.target;
      const src   = nodeMapRef.current.get(srcId);
      const tgt   = nodeMapRef.current.get(tgtId);
      if (!src || !tgt) return;

      const cfg = getEdgeCfg(link.edge_type ?? link.type);
      const w   = Math.max(0.2, link.weight ?? 0.5);
      const p0  = src.group.position.clone();
      const p1  = tgt.group.position.clone();

      const geo = new THREE.BufferGeometry().setFromPoints([p0, p1]);
      const mat = cfg.dashed
        ? new THREE.LineDashedMaterial({ color: cfg.color, transparent: true, opacity: cfg.baseOpacity * w, dashSize: 10, gapSize: 7, depthWrite: false })
        : new THREE.LineBasicMaterial({ color: cfg.color, transparent: true, opacity: cfg.baseOpacity * w, depthWrite: false });
      const line = new THREE.Line(geo, mat);
      if (cfg.dashed) line.computeLineDistances();
      edgeGroup.add(line);

      const ps = makeSprite(cfg.color, 0);
      ps.scale.set(6, 6, 1);
      ps.position.copy(p0);
      pulseGroup.add(ps);
      pulsesRef.current.push({ sprite: ps, srcPos: p0.clone(), tgtPos: p1.clone(), progress: Math.random(), speed: cfg.pulseSpeed });
    });
  }, [data]);

  // ── Highlights ────────────────────────────────────────────────────────────
  useEffect(() => {
    const hasSearch = highlightIds.size > 0;
    nodeMapRef.current.forEach((info, id) => {
      const isSel  = selectedNode?.id === id;
      const isHit  = highlightIds.has(id);
      const active = !hasSearch || isHit || isSel;
      info.scaleMult             = isSel ? 2.0 : isHit ? 1.4 : 1.0;
      info.glow.material.opacity = active ? 0.48 : 0.04;
      info.core.material.opacity = active ? 1.00 : 0.08;
      if (info.labelDiv) {
        info.labelDiv.style.opacity = active ? '1' : '0.08';
      }
    });
  }, [highlightIds, selectedNode]);

  const isEmpty = (data.nodes ?? []).length === 0;

  return (
    <div className="graph-container" ref={containerRef}>
      {isEmpty && (
        <div className="graph-overlay">
          <div className="spinner" />
          <span>Waiting for memory nodes&hellip;</span>
        </div>
      )}

      {tooltip && (
        <div
          className="node-tooltip"
          style={{ left: tooltip.x + 16, top: tooltip.y - 10 }}
        >
          <span
            className="tooltip-type"
            style={{ color: getCSS(tooltip.node.node_type ?? tooltip.node.type) }}
          >
            {(tooltip.node.node_type ?? tooltip.node.type ?? 'node').replace(/_/g, ' ')}
          </span>
          {tooltip.node.content && (
            <span className="tooltip-content">
              {trunc(tooltip.node.content)}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Knowledge Graph Visualization Widget
 * Renders an interactive force-directed graph using SVG.
 * Uses /api/health to check API availability, then falls back to data.json.
 */
(function () {
  "use strict";

  const API_BASE = window.__API_BASE__ || "http://localhost:8000";

  // Color palette for entity types
  const TYPE_COLORS = {
    startup: "#0d6efd",
    industry: "#198754",
    investor: "#ffc107",
    region: "#6f42c1",
    sector: "#fd7e14",
    failure_reason: "#dc3545",
    technology: "#20c997",
  };

  const TYPE_ICONS = {
    startup: "🏢",
    industry: "🏭",
    investor: "💰",
    region: "🌍",
    sector: "📊",
    failure_reason: "⚠️",
    technology: "🔧",
  };

  let simulation = null;

  function createStyles() {
    const s = document.createElement("style");
    s.textContent = `
      .kg-widget {
        background: var(--bg, #fff);
        border: 1px solid var(--border, #dee2e6);
        border-radius: 12px;
        padding: 20px;
        margin: 24px 0;
        overflow: hidden;
      }
      [data-theme="dark"] .kg-widget { background: var(--bg-secondary, #16213e); }
      .kg-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
      }
      .kg-header h3 { margin: 0; font-size: 16px; }
      .kg-controls { display: flex; gap: 8px; }
      .kg-controls select, .kg-controls input {
        padding: 6px 10px;
        border: 1px solid var(--border, #dee2e6);
        border-radius: 6px;
        font-size: 12px;
        background: var(--bg, #fff);
        color: var(--text, #212529);
      }
      .kg-legend {
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        margin-bottom: 12px;
        font-size: 12px;
      }
      .kg-legend-item {
        display: flex;
        align-items: center;
        gap: 4px;
        cursor: pointer;
        opacity: 0.8;
        transition: opacity 0.2s;
      }
      .kg-legend-item:hover { opacity: 1; }
      .kg-legend-item.hidden { opacity: 0.3; text-decoration: line-through; }
      .kg-legend-dot {
        width: 12px;
        height: 12px;
        border-radius: 50%;
        display: inline-block;
      }
      .kg-stats {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
        gap: 12px;
        margin-bottom: 16px;
      }
      .kg-stat {
        text-align: center;
        padding: 10px;
        background: var(--bg-secondary, #f8f9fa);
        border-radius: 8px;
      }
      .kg-stat-value { font-size: 22px; font-weight: 700; }
      .kg-stat-label { font-size: 11px; opacity: 0.7; }
      .kg-svg-container {
        border: 1px solid var(--border, #dee2e6);
        border-radius: 8px;
        overflow: hidden;
        background: var(--bg-secondary, #fafafa);
      }
      [data-theme="dark"] .kg-svg-container { background: #0d1117; }
      .kg-tooltip {
        position: absolute;
        background: var(--bg, #fff);
        border: 1px solid var(--border, #dee2e6);
        border-radius: 8px;
        padding: 10px 14px;
        font-size: 12px;
        max-width: 280px;
        box-shadow: 0 4px 16px rgba(0,0,0,0.15);
        pointer-events: none;
        z-index: 100;
        display: none;
      }
      .kg-tooltip-title { font-weight: 700; margin-bottom: 4px; }
      .kg-tooltip-type { font-size: 11px; opacity: 0.7; }
      .kg-search {
        width: 180px;
        padding: 6px 10px;
        border: 1px solid var(--border);
        border-radius: 6px;
        font-size: 12px;
        background: var(--bg);
        color: var(--text);
      }
    `;
    document.head.appendChild(s);
  }

  async function loadGraphData() {
    try {
      // Try API first
      const resp = await fetch(`${API_BASE}/api/stats`);
      if (!resp.ok) throw new Error("API unavailable");
      // API is live, try to get KG data from data.json (dashboard data)
    } catch (e) {
      // API not available
    }

    // Load from the dashboard's data.json
    try {
      const resp = await fetch("data.json");
      if (resp.ok) {
        const data = await resp.json();
        return data.knowledge_graph || null;
      }
    } catch (e) {}

    return null;
  }

  function renderWidget(data) {
    createStyles();

    const widget = document.createElement("div");
    widget.className = "kg-widget";
    widget.innerHTML = `
      <div class="kg-header">
        <h3>🔗 Knowledge Graph</h3>
        <div class="kg-controls">
          <input class="kg-search" placeholder="Search entities..." id="kgSearch" />
          <select id="kgFilter">
            <option value="all">All Types</option>
            <option value="startup">Startups</option>
            <option value="industry">Industries</option>
            <option value="investor">Investors</option>
            <option value="region">Regions</option>
            <option value="sector">Sectors</option>
            <option value="failure_reason">Failure Reasons</option>
          </select>
        </div>
      </div>
      <div class="kg-stats" id="kgStats"></div>
      <div class="kg-legend" id="kgLegend"></div>
      <div class="kg-svg-container">
        <svg id="kgSvg" width="100%" height="500"></svg>
      </div>
      <div class="kg-tooltip" id="kgTooltip">
        <div class="kg-tooltip-title" id="kgTooltipTitle"></div>
        <div class="kg-tooltip-type" id="kgTooltipType"></div>
        <div id="kgTooltipBody"></div>
      </div>
    `;

    return { widget, data };
  }

  function renderFallback() {
    createStyles();
    const widget = document.createElement("div");
    widget.className = "kg-widget";
    widget.innerHTML = `
      <div class="kg-header"><h3>🔗 Knowledge Graph</h3></div>
      <div style="padding:20px;text-align:center;opacity:0.7">
        <p>Knowledge graph visualization requires data from the analysis pipeline.</p>
        <p><small>Generate with: <code>python run_agent.py --pipeline analysis</code></small></p>
      </div>
    `;
    return widget;
  }

  function computeStats(entities, relationships) {
    const typeCounts = {};
    entities.forEach((e) => {
      typeCounts[e.type] = (typeCounts[e.type] || 0) + 1;
    });

    const statsEl = document.getElementById("kgStats");
    statsEl.innerHTML = `
      <div class="kg-stat">
        <div class="kg-stat-value">${entities.length}</div>
        <div class="kg-stat-label">Entities</div>
      </div>
      <div class="kg-stat">
        <div class="kg-stat-value">${relationships.length}</div>
        <div class="kg-stat-label">Relationships</div>
      </div>
      ${Object.entries(typeCounts)
        .map(
          ([type, count]) => `
        <div class="kg-stat">
          <div class="kg-stat-value">${count}</div>
          <div class="kg-stat-label">${TYPE_ICONS[type] || "📎"} ${type}</div>
        </div>
      `
        )
        .join("")}
    `;
  }

  function renderLegend(entities) {
    const types = [...new Set(entities.map((e) => e.type))];
    const legend = document.getElementById("kgLegend");
    const hiddenTypes = new Set();

    legend.innerHTML = types
      .map(
        (type) => `
      <div class="kg-legend-item" data-type="${type}">
        <span class="kg-legend-dot" style="background:${TYPE_COLORS[type] || "#6c757d"}"></span>
        ${TYPE_ICONS[type] || "📎"} ${type}
      </div>
    `
      )
      .join("");

    legend.addEventListener("click", (e) => {
      const item = e.target.closest(".kg-legend-item");
      if (!item) return;
      const type = item.dataset.type;
      if (hiddenTypes.has(type)) {
        hiddenTypes.delete(type);
        item.classList.remove("hidden");
      } else {
        hiddenTypes.add(type);
        item.classList.add("hidden");
      }
      // Update node visibility
      d3.selectAll(".kg-node").style("display", (d) =>
        hiddenTypes.has(d.type) ? "none" : "block"
      );
    });
  }

  function renderGraph(entities, relationships) {
    const svg = document.getElementById("kgSvg");
    const container = svg.parentElement;
    const width = container.clientWidth;
    const height = 500;

    svg.setAttribute("viewBox", `0 0 ${width} ${height}`);

    // Simple force simulation (no d3 dependency)
    const nodes = entities.map((e, i) => ({
      id: i,
      name: e.name,
      type: e.type,
      x: width / 2 + (Math.random() - 0.5) * 200,
      y: height / 2 + (Math.random() - 0.5) * 200,
      vx: 0,
      vy: 0,
      radius: Math.min(8 + Math.log2(e.mentions + 1) * 3, 24),
    }));

    const nameToIdx = {};
    entities.forEach((e, i) => {
      nameToIdx[e.name.toLowerCase()] = i;
    });

    const links = [];
    relationships.forEach((r) => {
      const si = nameToIdx[r.source.toLowerCase()];
      const ti = nameToIdx[r.target.toLowerCase()];
      if (si !== undefined && ti !== undefined) {
        links.push({ source: si, target: ti, type: r.relationship_type });
      }
    });

    // SVG elements
    const svgNS = "http://www.w3.org/2000/svg";

    // Clear
    while (svg.firstChild) svg.removeChild(svg.firstChild);

    // Defs for arrow markers
    const defs = document.createElementNS(svgNS, "defs");
    const marker = document.createElementNS(svgNS, "marker");
    marker.setAttribute("id", "arrow");
    marker.setAttribute("viewBox", "0 0 10 10");
    marker.setAttribute("refX", "20");
    marker.setAttribute("refY", "5");
    marker.setAttribute("markerWidth", "6");
    marker.setAttribute("markerHeight", "6");
    marker.setAttribute("orient", "auto");
    const path = document.createElementNS(svgNS, "path");
    path.setAttribute("d", "M 0 0 L 10 5 L 0 10 z");
    path.setAttribute("fill", "#999");
    marker.appendChild(path);
    defs.appendChild(marker);
    svg.appendChild(defs);

    // Link lines
    const linkElements = links.map((l) => {
      const line = document.createElementNS(svgNS, "line");
      line.setAttribute("stroke", "rgba(128,128,128,0.3)");
      line.setAttribute("stroke-width", "1.5");
      line.setAttribute("marker-end", "url(#arrow)");
      svg.appendChild(line);
      return line;
    });

    // Node groups
    const nodeGroups = nodes.map((n, i) => {
      const g = document.createElementNS(svgNS, "g");
      g.classList.add("kg-node");
      g.style.cursor = "pointer";

      const circle = document.createElementNS(svgNS, "circle");
      circle.setAttribute("r", n.radius);
      circle.setAttribute("fill", TYPE_COLORS[n.type] || "#6c757d");
      circle.setAttribute("stroke", "#fff");
      circle.setAttribute("stroke-width", "2");
      g.appendChild(circle);

      // Label for important nodes
      if (n.radius > 10) {
        const text = document.createElementNS(svgNS, "text");
        text.setAttribute("text-anchor", "middle");
        text.setAttribute("dy", n.radius + 14);
        text.setAttribute("font-size", "10");
        text.setAttribute("fill", "var(--text-secondary, #6c757d)");
        text.textContent = n.name.length > 20 ? n.name.substring(0, 18) + "…" : n.name;
        g.appendChild(text);
      }

      // Tooltip events
      g.addEventListener("mouseenter", (e) => {
        const tooltip = document.getElementById("kgTooltip");
        const rect = container.getBoundingClientRect();
        tooltip.style.display = "block";
        tooltip.style.left = e.clientX - rect.left + 15 + "px";
        tooltip.style.top = e.clientY - rect.top - 10 + "px";
        document.getElementById("kgTooltipTitle").textContent = n.name;
        document.getElementById("kgTooltipType").textContent =
          `${TYPE_ICONS[n.type] || ""} ${n.type}`;
        document.getElementById("kgTooltipBody").innerHTML = `
          <div style="margin-top:4px">Connections: ${links.filter((l) => l.source === i || l.target === i).length}</div>
        `;
        circle.setAttribute("stroke", "#0d6efd");
        circle.setAttribute("stroke-width", "3");
      });
      g.addEventListener("mouseleave", () => {
        document.getElementById("kgTooltip").style.display = "none";
        circle.setAttribute("stroke", "#fff");
        circle.setAttribute("stroke-width", "2");
      });

      // Drag
      let dragging = false;
      g.addEventListener("mousedown", () => { dragging = true; });
      document.addEventListener("mouseup", () => { dragging = false; });
      document.addEventListener("mousemove", (e) => {
        if (!dragging) return;
        const rect = container.getBoundingClientRect();
        n.x = e.clientX - rect.left;
        n.y = e.clientY - rect.top;
        n.vx = 0;
        n.vy = 0;
      });

      svg.appendChild(g);
      return g;
    });

    // Simple force simulation
    const alpha = 0.3;
    let frame = 0;

    function tick() {
      frame++;
      // Repulsion between nodes
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const dx = nodes[j].x - nodes[i].x;
          const dy = nodes[j].y - nodes[i].y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const force = (800 * alpha) / (dist * dist);
          nodes[i].vx -= (dx / dist) * force;
          nodes[i].vy -= (dy / dist) * force;
          nodes[j].vx += (dx / dist) * force;
          nodes[j].vy += (dy / dist) * force;
        }
      }

      // Attraction along links
      for (const l of links) {
        const s = nodes[l.source];
        const t = nodes[l.target];
        const dx = t.x - s.x;
        const dy = t.y - s.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = (dist - 80) * 0.005;
        s.vx += (dx / dist) * force;
        s.vy += (dy / dist) * force;
        t.vx -= (dx / dist) * force;
        t.vy -= (dy / dist) * force;
      }

      // Center gravity
      for (const n of nodes) {
        n.vx += (width / 2 - n.x) * 0.001;
        n.vy += (height / 2 - n.y) * 0.001;
        n.vx *= 0.9;
        n.vy *= 0.9;
        n.x += n.vx;
        n.y += n.vy;
        n.x = Math.max(20, Math.min(width - 20, n.x));
        n.y = Math.max(20, Math.min(height - 20, n.y));
      }

      // Update positions
      for (let i = 0; i < nodes.length; i++) {
        nodeGroups[i].setAttribute("transform", `translate(${nodes[i].x},${nodes[i].y})`);
      }
      for (let i = 0; i < links.length; i++) {
        linkElements[i].setAttribute("x1", nodes[links[i].source].x);
        linkElements[i].setAttribute("y1", nodes[links[i].source].y);
        linkElements[i].setAttribute("x2", nodes[links[i].target].x);
        linkElements[i].setAttribute("y2", nodes[links[i].target].y);
      }

      if (frame < 300) requestAnimationFrame(tick);
    }

    requestAnimationFrame(tick);

    // Search filter
    document.getElementById("kgSearch").addEventListener("input", (e) => {
      const q = e.target.value.toLowerCase();
      nodeGroups.forEach((g, i) => {
        const match = !q || nodes[i].name.toLowerCase().includes(q);
        g.style.opacity = match ? 1 : 0.1;
      });
    });

    // Type filter
    document.getElementById("kgFilter").addEventListener("change", (e) => {
      const type = e.target.value;
      nodeGroups.forEach((g, i) => {
        const match = type === "all" || nodes[i].type === type;
        g.style.display = match ? "block" : "none";
      });
    });
  }

  // ── Initialize ──
  async function init() {
    const data = await loadGraphData();

    if (!data || !data.entities || data.entities.length === 0) {
      const widget = renderFallback();
      const main = document.querySelector("main") || document.querySelector(".content") || document.body;
      main.appendChild(widget);
      return;
    }

    const { widget, data: graphData } = renderWidget(data);
    const main = document.querySelector("main") || document.querySelector(".content") || document.body;
    main.appendChild(widget);

    computeStats(graphData.entities, graphData.relationships);
    renderLegend(graphData.entities);
    renderGraph(graphData.entities, graphData.relationships);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();

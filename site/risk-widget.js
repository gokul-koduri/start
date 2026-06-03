/**
 * Risk Score Dashboard Widget
 * Renders a risk score breakdown chart in the dashboard.
 * Uses the /api/risk-scores endpoint.
 */
(function () {
  "use strict";

  const API_BASE = window.__API_BASE__ || "http://localhost:8000";

  async function loadRiskScores() {
    try {
      const resp = await fetch(`${API_BASE}/api/risk-scores?limit=50`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      return data.results || [];
    } catch (err) {
      console.warn("Risk scores unavailable:", err);
      return null;
    }
  }

  function renderRiskSection(scores) {
    const section = document.createElement("div");
    section.id = "risk-section";
    section.innerHTML = `
      <h2>⚠️ Startup Failure Risk Scores</h2>
      <div id="risk-content">
        ${scores ? renderContent(scores) : renderFallback()}
      </div>
    `;
    return section;
  }

  function renderFallback() {
    return `
      <div style="padding:20px;text-align:center;opacity:0.7">
        <p>Risk scoring requires the API server running at <code>${API_BASE}</code></p>
        <p><small>Start with: <code>python api_server.py</code></small></p>
        <p><small>Score startups with: <code>python run_agent.py --pipeline analysis</code></small></p>
      </div>
    `;
  }

  function renderContent(scores) {
    // Distribution
    const dist = { critical: 0, high: 0, moderate: 0, low: 0 };
    scores.forEach((s) => dist[s.risk_level] = (dist[s.risk_level] || 0) + 1);

    const total = scores.length || 1;
    const bars = Object.entries(dist).map(([level, count]) => {
      const pct = ((count / total) * 100).toFixed(1);
      const colors = { critical: "#dc3545", high: "#fd7e14", moderate: "#ffc107", low: "#198754" };
      return `
        <div style="display:flex;align-items:center;gap:8px;margin:6px 0">
          <span style="width:80px;font-weight:600;text-transform:uppercase;font-size:12px">${level}</span>
          <div style="flex:1;background:#e9ecef;border-radius:4px;height:24px;overflow:hidden">
            <div style="width:${pct}%;background:${colors[level]};height:100%;border-radius:4px;transition:width 0.5s"></div>
          </div>
          <span style="width:60px;text-align:right;font-size:13px">${count} (${pct}%)</span>
        </div>
      `;
    }).join("");

    // Top risky
    const topRisky = scores
      .sort((a, b) => b.risk_score - a.risk_score)
      .slice(0, 10)
      .map(
        (s) => `
      <tr>
        <td><strong>${s.name}</strong></td>
        <td>${s.sector || "—"}</td>
        <td>${s.funding_raised_usd ? "$" + (s.funding_raised_usd / 1e6).toFixed(1) + "M" : "—"}</td>
        <td>
          <span style="
            display:inline-block;
            width:48px;text-align:center;
            padding:2px 8px;border-radius:4px;
            font-size:12px;font-weight:600;
            background:${riskColor(s.risk_level)};
            color:white
          ">${(s.risk_score * 100).toFixed(0)}%</span>
        </td>
        <td style="font-size:12px;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap"
            title="${s.recommendation || ""}">${s.recommendation || "—"}</td>
      </tr>
    `
      )
      .join("");

    return `
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-bottom:24px">
        <div>
          <h3 style="margin:0 0 12px;font-size:14px">Risk Distribution</h3>
          ${bars}
        </div>
        <div>
          <h3 style="margin:0 0 12px;font-size:14px">Summary</h3>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
            <div style="padding:16px;background:var(--bg-secondary);border-radius:8px;text-align:center">
              <div style="font-size:28px;font-weight:700">${total}</div>
              <div style="font-size:12px;opacity:0.7">Scored Startups</div>
            </div>
            <div style="padding:16px;background:var(--bg-secondary);border-radius:8px;text-align:center">
              <div style="font-size:28px;font-weight:700;color:#dc3545">${dist.critical + dist.high}</div>
              <div style="font-size:12px;opacity:0.7">High Risk</div>
            </div>
            <div style="padding:16px;background:var(--bg-secondary);border-radius:8px;text-align:center">
              <div style="font-size:28px;font-weight:700">${(scores.reduce((a, s) => a + s.risk_score, 0) / total * 100).toFixed(0)}%</div>
              <div style="font-size:12px;opacity:0.7">Avg Risk Score</div>
            </div>
            <div style="padding:16px;background:var(--bg-secondary);border-radius:8px;text-align:center">
              <div style="font-size:28px;font-weight:700;color:#198754">${dist.low}</div>
              <div style="font-size:12px;opacity:0.7">Low Risk</div>
            </div>
          </div>
        </div>
      </div>
      <h3 style="margin:16px 0 8px;font-size:14px">Top 10 Riskiest Startups</h3>
      <table style="width:100%;border-collapse:collapse;font-size:13px">
        <thead>
          <tr style="border-bottom:2px solid var(--border)">
            <th style="text-align:left;padding:8px">Name</th>
            <th style="text-align:left;padding:8px">Sector</th>
            <th style="text-align:left;padding:8px">Funding</th>
            <th style="text-align:center;padding:8px">Risk</th>
            <th style="text-align:left;padding:8px">Recommendation</th>
          </tr>
        </thead>
        <tbody>${topRisky}</tbody>
      </table>
    `;
  }

  function riskColor(level) {
    return { critical: "#dc3545", high: "#fd7e14", moderate: "#ffc107", low: "#198754" }[level] || "#6c757d";
  }

  // Initialize — append to the dashboard when DOM is ready
  async function init() {
    const scores = await loadRiskScores();
    const section = renderRiskSection(scores);

    // Try to insert into the dashboard's main content area
    const main = document.querySelector("main") || document.querySelector(".content") || document.body;
    main.appendChild(section);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();

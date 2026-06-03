"""Dashboard agent — converts markdown report to an interactive HTML site."""

import json
import logging
import re
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

from agents.base import AgentResult, BaseAgent
from config import get_project_root, load_config
from db.connection import get_connection
from db import schema

_logger = logging.getLogger(__name__)

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
/* ── Base theme ── */
:root {{
  --bg: #ffffff;
  --bg-secondary: #f8f9fa;
  --text: #212529;
  --text-secondary: #6c757d;
  --border: #dee2e6;
  --accent: #0d6efd;
  --accent-light: #e7f1ff;
  --success: #198754;
  --danger: #dc3545;
  --warning: #ffc107;
  --sidebar-width: 280px;
  --header-height: 60px;
}}
/* ── Dark theme (manual toggle) ── */
[data-theme="dark"] {{
  --bg: #1a1a2e;
  --bg-secondary: #16213e;
  --text: #e8e8e8;
  --text-secondary: #a0a0a0;
  --border: #2a2a4a;
  --accent: #4dabf7;
  --accent-light: #1a2a4a;
  --success: #51cf66;
  --danger: #ff6b6b;
  --warning: #ffd43b;
}}
/* ── Dark theme (auto-detect fallback) ── */
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme]) {{
    --bg: #1a1a2e;
    --bg-secondary: #16213e;
    --text: #e8e8e8;
    --text-secondary: #a0a0a0;
    --border: #2a2a4a;
    --accent: #4dabf7;
    --accent-light: #1a2a4a;
    --success: #51cf66;
    --danger: #ff6b6b;
    --warning: #ffd43b;
  }}
}}
/* ── Smooth scroll + header offset ── */
html {{ scroll-behavior: smooth; scroll-padding-top: calc(var(--header-height) + 16px); }}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.6;
}}
/* ── Header ── */
.header {{
  position: fixed; top: 0; left: 0; right: 0; height: var(--header-height);
  background: var(--bg-secondary); border-bottom: 1px solid var(--border);
  display: flex; align-items: center; padding: 0 24px; z-index: 100;
  backdrop-filter: blur(10px); gap: 8px;
}}
.header h1 {{ font-size: 18px; font-weight: 600; white-space: nowrap; }}
.header .meta {{ margin-left: auto; font-size: 13px; color: var(--text-secondary); white-space: nowrap; }}
/* ── Hamburger (mobile) ── */
.hamburger {{
  display: none; background: none; border: none; cursor: pointer;
  padding: 8px; flex-direction: column; gap: 4px;
}}
.hamburger span {{
  display: block; width: 20px; height: 2px;
  background: var(--text); transition: all 0.3s;
}}
.hamburger.active span:nth-child(1) {{ transform: rotate(45deg) translate(4px, 4px); }}
.hamburger.active span:nth-child(2) {{ opacity: 0; }}
.hamburger.active span:nth-child(3) {{ transform: rotate(-45deg) translate(4px, -4px); }}
/* ── Sidebar overlay (mobile) ── */
.sidebar-overlay {{
  display: none; position: fixed; inset: 0;
  background: rgba(0,0,0,0.5); z-index: 90;
}}
.sidebar-overlay.active {{ display: block; }}
/* ── Search ── */
.search-container {{
  position: relative; margin-left: 16px;
  display: flex; align-items: center;
}}
.search-container input {{
  background: var(--bg); border: 1px solid var(--border);
  border-radius: 6px; padding: 6px 28px 6px 12px;
  color: var(--text); font-size: 13px; width: 180px;
  outline: none; transition: width 0.3s, border-color 0.2s;
}}
.search-container input:focus {{ border-color: var(--accent); width: 260px; }}
.search-clear {{
  position: absolute; right: 8px; cursor: pointer;
  color: var(--text-secondary); font-size: 16px;
  display: none; line-height: 1;
}}
.search-clear.visible {{ display: block; }}
.search-dimmed {{ opacity: 0.25; transition: opacity 0.2s; }}
/* ── Theme toggle ── */
.theme-toggle {{
  background: none; border: 1px solid var(--border);
  border-radius: 6px; padding: 4px 8px; cursor: pointer;
  color: var(--text); font-size: 18px; margin-left: 8px;
  transition: background 0.2s;
}}
.theme-toggle:hover {{ background: var(--accent-light); }}
[data-theme="dark"] .theme-icon {{ transform: rotate(180deg); }}
.theme-icon {{ display: inline-block; transition: transform 0.3s; }}
/* ── Sidebar ── */
.sidebar {{
  position: fixed; top: var(--header-height); left: 0;
  width: var(--sidebar-width); height: calc(100vh - var(--header-height));
  background: var(--bg-secondary); border-right: 1px solid var(--border);
  overflow-y: auto; padding: 16px 0;
  transition: transform 0.3s ease;
}}
.sidebar a {{
  display: block; padding: 8px 20px; color: var(--text-secondary);
  text-decoration: none; font-size: 13px; border-left: 3px solid transparent;
  transition: all 0.15s;
}}
.sidebar a:hover {{ color: var(--accent); background: var(--accent-light); }}
.sidebar a.h2 {{ padding-left: 32px; font-weight: 600; color: var(--text); }}
.sidebar a.h3 {{ padding-left: 48px; }}
/* ── Main ── */
.main {{
  margin-left: var(--sidebar-width); margin-top: var(--header-height);
  padding: 32px 40px; max-width: 960px;
}}
/* ── Stats cards ── */
.stats-grid {{
  display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px; margin-bottom: 32px;
}}
.stat-card {{
  background: var(--bg-secondary); border: 1px solid var(--border);
  border-radius: 8px; padding: 20px; text-align: center;
  transition: transform 0.2s, box-shadow 0.2s;
  position: relative; overflow: hidden;
}}
.stat-card:hover {{ transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
.stat-card .icon {{ font-size: 24px; margin-bottom: 6px; display: block; }}
.stat-card .value {{ font-size: 32px; font-weight: 700; }}
.stat-card .label {{
  font-size: 12px; color: var(--text-secondary); margin-top: 4px;
  text-transform: uppercase; letter-spacing: 0.5px;
}}
.stat-card::before {{
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
}}
.stat-card.accent-blue .value {{ color: #0d6efd; }}
.stat-card.accent-blue::before {{ background: #0d6efd; }}
.stat-card.accent-red .value {{ color: #dc3545; }}
.stat-card.accent-red::before {{ background: #dc3545; }}
.stat-card.accent-green .value {{ color: #198754; }}
.stat-card.accent-green::before {{ background: #198754; }}
.stat-card.accent-amber .value {{ color: #fd7e14; }}
.stat-card.accent-amber::before {{ background: #fd7e14; }}
/* ── Charts ── */
.chart-container {{
  background: var(--bg-secondary); border: 1px solid var(--border);
  border-radius: 8px; padding: 20px; margin-bottom: 24px;
}}
.chart-container h3 {{ margin-bottom: 12px; font-size: 16px; }}
.charts-grid {{
  display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 32px;
}}
@media (max-width: 900px) {{ .charts-grid {{ grid-template-columns: 1fr; }} }}
/* ── Content ── */
h1 {{ font-size: 28px; margin: 32px 0 16px; padding-bottom: 8px; border-bottom: 2px solid var(--accent); }}
h2 {{ font-size: 22px; margin: 28px 0 12px; color: var(--accent); }}
h3 {{ font-size: 18px; margin: 20px 0 8px; }}
p {{ margin: 8px 0; }}
ul, ol {{ margin: 8px 0 8px 24px; }}
li {{ margin: 4px 0; }}
strong {{ color: var(--accent); }}
table {{
  width: 100%; border-collapse: collapse; margin: 16px 0;
  font-size: 14px;
}}
th, td {{
  padding: 10px 12px; text-align: left; border: 1px solid var(--border);
}}
th {{
  background: var(--accent-light); font-weight: 600;
  position: sticky; top: 0;
}}
tr:nth-child(even) {{ background: var(--bg-secondary); }}
tr:hover {{ background: var(--accent-light); }}
code {{
  background: var(--bg-secondary); padding: 2px 6px; border-radius: 3px;
  font-size: 13px;
}}
blockquote {{
  border-left: 4px solid var(--accent); padding: 12px 20px; margin: 16px 0;
  background: var(--accent-light); border-radius: 0 8px 8px 0;
}}
hr {{ border: none; border-top: 1px solid var(--border); margin: 24px 0; }}
/* ── Collapsible sections ── */
h2.collapsible {{
  cursor: pointer; user-select: none;
  position: relative; padding-right: 30px;
}}
h2.collapsible::after {{
  content: ''; position: absolute; right: 4px; top: 50%;
  border: solid var(--accent); border-width: 0 2px 2px 0;
  padding: 4px; display: inline-block;
  transform: translateY(-65%) rotate(-135deg);
  transition: transform 0.2s;
}}
h2.collapsible.collapsed::after {{
  transform: translateY(-35%) rotate(45deg);
}}
.section-content {{ transition: max-height 0.3s ease, opacity 0.2s; overflow: hidden; }}
.section-content.collapsed {{ max-height: 0 !important; opacity: 0; }}
/* ── Styled TOC ── */
h2#table-of-contents + ol {{
  background: var(--bg-secondary); border: 1px solid var(--border);
  border-radius: 8px; padding: 20px 20px 20px 40px;
  margin: 16px 0; column-count: 2; column-gap: 24px;
}}
h2#table-of-contents + ol li {{ margin: 6px 0; break-inside: avoid; }}
h2#table-of-contents + ol a {{ color: var(--accent); text-decoration: none; }}
h2#table-of-contents + ol a:hover {{ text-decoration: underline; }}
/* ── Back to top ── */
.back-to-top {{
  position: fixed; bottom: 24px; right: 24px;
  width: 44px; height: 44px; border-radius: 50%;
  background: var(--accent); color: white; border: none;
  cursor: pointer; font-size: 18px; z-index: 80;
  opacity: 0; transform: translateY(20px);
  transition: opacity 0.3s, transform 0.3s;
  box-shadow: 0 2px 8px rgba(0,0,0,0.2);
}}
.back-to-top.visible {{ opacity: 1; transform: translateY(0); }}
.back-to-top:hover {{ opacity: 0.9; transform: translateY(-2px); }}
/* ── Print ── */
@media print {{
  .sidebar, .header, .back-to-top {{ display: none; }}
  .main {{ margin: 0; padding: 0; }}
}}
/* ── Mobile ── */
@media (max-width: 768px) {{
  .hamburger {{ display: flex; }}
  .sidebar {{
    transform: translateX(-100%); z-index: 95;
  }}
  .sidebar.open {{ transform: translateX(0); }}
  .main {{ margin-left: 0; padding: 20px; }}
  .search-container input {{ width: 120px; }}
  .search-container input:focus {{ width: 160px; }}
  h2#table-of-contents + ol {{ column-count: 1; }}
}}
/* ── Tier badge ── */
.tier-badge {{
  display: inline-block; padding: 2px 10px; border-radius: 12px;
  font-size: 11px; font-weight: 600; cursor: pointer;
  transition: background 0.2s, color 0.2s;
}}
.tier-badge.free {{ background: var(--border); color: var(--text-secondary); }}
.tier-badge.pro {{ background: var(--accent); color: white; }}
.tier-badge.enterprise {{ background: #6f42c1; color: white; }}
/* ── Gated content ── */
.gated-content {{ display: none; }}
.gated-content.unlocked {{ display: block; }}
/* ── Pro lock overlay ── */
.pro-lock-overlay {{
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  min-height: 200px; padding: 40px 20px; text-align: center;
  background: var(--bg-secondary); border: 2px dashed var(--border);
  border-radius: 12px; margin: 16px 0;
}}
.pro-lock-overlay .lock-icon {{ font-size: 36px; margin-bottom: 12px; opacity: 0.4; }}
.pro-lock-overlay h3 {{ font-size: 18px; color: var(--text); margin-bottom: 8px; }}
.pro-lock-overlay p {{ font-size: 14px; color: var(--text-secondary); margin-bottom: 16px; max-width: 400px; }}
.pro-lock-overlay .upgrade-btn {{
  display: inline-block; padding: 8px 20px; border-radius: 8px;
  background: var(--accent); color: white; font-weight: 600; font-size: 14px;
  text-decoration: none; transition: background 0.2s; border: none; cursor: pointer;
}}
.pro-lock-overlay .upgrade-btn:hover {{ opacity: 0.9; }}
/* ── Pricing cards ── */
.pricing-grid {{
  display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 24px; margin: 32px 0;
}}
.pricing-card {{
  background: var(--bg-secondary); border: 2px solid var(--border);
  border-radius: 12px; padding: 32px 24px; text-align: center;
  transition: transform 0.2s, box-shadow 0.2s; position: relative;
}}
.pricing-card:hover {{ transform: translateY(-4px); box-shadow: 0 8px 24px rgba(0,0,0,0.1); }}
.pricing-card.featured {{ border-color: var(--accent); }}
.pricing-card.featured::before {{
  content: 'MOST POPULAR'; position: absolute; top: -12px; left: 50%; transform: translateX(-50%);
  background: var(--accent); color: white; padding: 2px 12px; border-radius: 10px;
  font-size: 10px; font-weight: 700; letter-spacing: 0.5px;
}}
.pricing-card .price {{ font-size: 48px; font-weight: 800; margin: 16px 0 4px; }}
.pricing-card .price small {{ font-size: 16px; font-weight: 400; color: var(--text-secondary); }}
.pricing-card .tier-name {{ font-size: 14px; text-transform: uppercase; letter-spacing: 1px; color: var(--text-secondary); margin-bottom: 8px; }}
.pricing-card .features {{ text-align: left; margin: 24px 0; }}
.pricing-card .features li {{
  padding: 8px 0; border-bottom: 1px solid var(--border); font-size: 13px;
  list-style: none; padding-left: 20px; position: relative;
}}
.pricing-card .features li::before {{
  content: '\\2713'; position: absolute; left: 0; color: var(--success); font-weight: bold;
}}
.pricing-card .cta-btn {{
  display: block; padding: 12px 24px; border-radius: 8px;
  font-weight: 600; font-size: 15px; text-decoration: none;
  cursor: pointer; transition: all 0.2s; border: 2px solid;
}}
.pricing-card .cta-btn.primary {{ background: var(--accent); color: white; border-color: var(--accent); }}
.pricing-card .cta-btn.primary:hover {{ opacity: 0.9; }}
.pricing-card .cta-btn.secondary {{ background: transparent; color: var(--accent); border-color: var(--accent); }}
.pricing-card .cta-btn.secondary:hover {{ background: var(--accent-light); }}
.pricing-card .cta-btn.current {{ background: var(--border); color: var(--text-secondary); border-color: var(--border); cursor: default; }}
/* ── Modal ── */
.modal-overlay {{
  display: none; position: fixed; inset: 0;
  background: rgba(0,0,0,0.6); z-index: 200;
  justify-content: center; align-items: center;
}}
.modal-overlay.active {{ display: flex; }}
.modal {{
  background: var(--bg); border: 1px solid var(--border);
  border-radius: 12px; padding: 32px; max-width: 440px; width: 90%;
  box-shadow: 0 16px 48px rgba(0,0,0,0.2); position: relative;
}}
.modal h2 {{ font-size: 20px; margin-bottom: 8px; color: var(--text); }}
.modal p {{ font-size: 13px; color: var(--text-secondary); margin-bottom: 16px; }}
.modal input[type="text"] {{
  width: 100%; padding: 10px 14px; border: 1px solid var(--border);
  border-radius: 8px; font-size: 15px; font-family: monospace;
  background: var(--bg-secondary); color: var(--text); outline: none;
  margin-bottom: 12px; text-transform: uppercase; letter-spacing: 1px;
}}
.modal input[type="text"]:focus {{ border-color: var(--accent); }}
.modal .modal-actions {{ display: flex; gap: 8px; }}
.modal .modal-actions button {{
  flex: 1; padding: 10px; border-radius: 8px; font-size: 14px; font-weight: 600;
  cursor: pointer; border: none; transition: all 0.2s;
}}
.modal .modal-actions .btn-activate {{ background: var(--accent); color: white; }}
.modal .modal-actions .btn-activate:hover {{ opacity: 0.9; }}
.modal .modal-actions .btn-cancel {{ background: var(--border); color: var(--text); }}
.modal .modal-actions .btn-cancel:hover {{ background: var(--bg-secondary); }}
.modal .modal-close {{
  position: absolute; top: 12px; right: 16px; background: none; border: none;
  font-size: 20px; cursor: pointer; color: var(--text-secondary);
}}
.modal .error-msg {{ color: var(--danger); font-size: 13px; min-height: 18px; margin-top: 4px; }}
.modal .purchase-link {{ display: block; margin-top: 12px; font-size: 13px; }}
.modal .purchase-link a {{ color: var(--accent); text-decoration: underline; }}
@media (max-width: 768px) {{
  .pricing-grid {{ grid-template-columns: 1fr; }}
}}
</style>
</head>
<body>
<div class="header">
  <button class="hamburger" id="hamburgerBtn" aria-label="Toggle navigation">
    <span></span><span></span><span></span>
  </button>
  <h1>{title}</h1>
  <div class="search-container">
    <input type="text" id="searchInput" placeholder="Search report..." autocomplete="off" />
    <span class="search-clear" id="searchClear">&times;</span>
  </div>
  <span class="tier-badge free" id="tierBadge" onclick="showTierAction()">FREE</span>
  <span class="meta">Updated: {generated}</span>
  <button class="theme-toggle" id="themeToggle" aria-label="Toggle dark mode" title="Toggle dark mode">
    <span class="theme-icon" id="themeIcon">&#9788;</span>
  </button>
</div>
<div class="sidebar-overlay" id="sidebarOverlay"></div>
<nav class="sidebar">
{nav}
</nav>
<div class="main">
{stats}
{charts}
{body}
{pricing_section}
</div>
<!-- Activation Modal -->
<div class="modal-overlay" id="activateOverlay">
  <div class="modal">
    <button class="modal-close" onclick="closeModal()">&times;</button>
    <h2>Activate Pro Access</h2>
    <p>Enter your license key to unlock premium features.</p>
    <input type="text" id="licenseKeyInput" placeholder="PRO-XXXX-XXXX-XXXX" autocomplete="off" />
    <div class="error-msg" id="licenseError"></div>
    <div class="modal-actions">
      <button class="btn-activate" onclick="activateLicense()">Activate</button>
      <button class="btn-cancel" onclick="closeModal()">Cancel</button>
    </div>
    <div class="purchase-link" id="purchaseLink">
      <a href="#" target="_blank" id="purchaseUrl">Purchase a Pro license</a>
    </div>
  </div>
</div>
<button class="back-to-top" id="backToTop" aria-label="Back to top">&#9650;</button>
<script>
// ── Hamburger menu (mobile) ──
(function() {{
  var btn = document.getElementById('hamburgerBtn');
  var sidebar = document.querySelector('.sidebar');
  var overlay = document.getElementById('sidebarOverlay');
  function toggleMenu() {{
    btn.classList.toggle('active');
    sidebar.classList.toggle('open');
    overlay.classList.toggle('active');
  }}
  btn.addEventListener('click', toggleMenu);
  overlay.addEventListener('click', toggleMenu);
  sidebar.querySelectorAll('a').forEach(function(link) {{
    link.addEventListener('click', function() {{
      if (sidebar.classList.contains('open')) toggleMenu();
    }});
  }});
}})();

// ── Dark mode toggle ──
(function() {{
  var toggle = document.getElementById('themeToggle');
  var icon = document.getElementById('themeIcon');
  var html = document.documentElement;
  function applyTheme(theme) {{
    if (theme === 'dark') {{
      html.setAttribute('data-theme', 'dark');
      icon.innerHTML = '&#9790;';
    }} else {{
      html.removeAttribute('data-theme');
      icon.innerHTML = '&#9788;';
    }}
  }}
  var saved = localStorage.getItem('dashboard-theme');
  if (saved) applyTheme(saved);
  toggle.addEventListener('click', function() {{
    var isDark = html.getAttribute('data-theme') === 'dark';
    var next = isDark ? 'light' : 'dark';
    applyTheme(next);
    localStorage.setItem('dashboard-theme', next);
  }});
}})();

// ── Client-side search ──
(function() {{
  var input = document.getElementById('searchInput');
  var clear = document.getElementById('searchClear');
  var main = document.querySelector('.main');
  var sections = [];
  var debounceTimer;
  function buildSections() {{
    var headings = main.querySelectorAll('h2, h3');
    sections = [];
    headings.forEach(function(h) {{
      var content = [];
      var sibling = h.nextElementSibling;
      while (sibling && sibling.tagName !== 'H2' && sibling.tagName !== 'H3') {{
        content.push(sibling);
        sibling = sibling.nextElementSibling;
      }}
      sections.push({{ heading: h, content: content }});
    }});
  }}
  function doSearch(query) {{
    if (!sections.length) buildSections();
    var q = query.toLowerCase().trim();
    if (!q) {{
      main.querySelectorAll('.search-dimmed').forEach(function(el) {{
        el.classList.remove('search-dimmed');
      }});
      return;
    }}
    sections.forEach(function(sec) {{
      var text = sec.heading.textContent.toLowerCase();
      var contentText = sec.content.map(function(el) {{
        return el.textContent.toLowerCase();
      }}).join(' ');
      var matches = (text + ' ' + contentText).indexOf(q) !== -1;
      sec.heading.classList.toggle('search-dimmed', !matches);
      sec.content.forEach(function(el) {{
        el.classList.toggle('search-dimmed', !matches);
      }});
    }});
  }}
  input.addEventListener('input', function() {{
    clear.classList.toggle('visible', input.value.length > 0);
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(function() {{ doSearch(input.value); }}, 200);
  }});
  clear.addEventListener('click', function() {{
    input.value = '';
    clear.classList.remove('visible');
    doSearch('');
    input.focus();
  }});
}})();

// ── Collapsible sections ──
(function() {{
  var main = document.querySelector('.main');
  var h2s = main.querySelectorAll('h2');
  h2s.forEach(function(h2) {{
    if (h2.id === 'table-of-contents') return;
    h2.classList.add('collapsible');
    var wrapper = document.createElement('div');
    wrapper.className = 'section-content';
    var sibling = h2.nextElementSibling;
    while (sibling && sibling.tagName !== 'H2') {{
      var next = sibling.nextElementSibling;
      wrapper.appendChild(sibling);
      sibling = next;
    }}
    h2.parentNode.insertBefore(wrapper, h2.nextSibling);
    h2.addEventListener('click', function() {{
      h2.classList.toggle('collapsed');
      wrapper.classList.toggle('collapsed');
    }});
  }});
}})();

// ── Back to top button ──
(function() {{
  var btn = document.getElementById('backToTop');
  window.addEventListener('scroll', function() {{
    btn.classList.toggle('visible', window.scrollY > 400);
  }});
  btn.addEventListener('click', function() {{
    window.scrollTo({{ top: 0, behavior: 'smooth' }});
  }});
}})();

// ── Tier gate system ──
(function() {{
  var tierBadge = document.getElementById('tierBadge');
  var activateOverlay = document.getElementById('activateOverlay');
  var licenseInput = document.getElementById('licenseKeyInput');
  var licenseError = document.getElementById('licenseError');
  var purchaseUrl = document.getElementById('purchaseUrl');
  var _licenseData = null;
  var _currentTier = 'free';

  function hashKey(key) {{
    var hash = 0;
    for (var i = 0; i < key.length; i++) {{
      var c = key.charCodeAt(i);
      hash = ((hash << 5) - hash) + c;
      hash |= 0;
    }}
    // SHA-256 via SubtleCrypto (async, fallback to simple hash)
    return key; // Pass raw key — validation uses hashed allowlist on server
  }}

  async function sha256(str) {{
    var buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(str));
    return Array.from(new Uint8Array(buf)).map(function(b) {{ return b.toString(16).padStart(2, '0'); }}).join('');
  }}

  function updateBadge(tier) {{
    _currentTier = tier;
    tierBadge.textContent = tier.toUpperCase();
    tierBadge.className = 'tier-badge ' + tier;
  }}

  function unlockContent(tier) {{
    var tiers = ['pro'];
    if (tier === 'enterprise') tiers.push('enterprise');
    tiers.forEach(function(t) {{
      document.querySelectorAll('.gated-content[data-tier="' + t + '"]').forEach(function(el) {{
        el.classList.add('unlocked');
      }});
    }});
  }}

  async function validateAndActivate(key) {{
    try {{
      var resp = await fetch('licenses.json');
      if (!resp.ok) return false;
      var data = await resp.json();
      _licenseData = data;
      var hashedKey = await sha256(key);
      return data.keys && data.keys.indexOf(hashedKey) !== -1;
    }} catch(e) {{
      return false;
    }}
  }}

  async function initTierGate() {{
    var savedKey = localStorage.getItem('opl_license_key');
    if (savedKey) {{
      var valid = await validateAndActivate(savedKey);
      if (valid) {{
        updateBadge(savedKey.startsWith('ENT') ? 'enterprise' : 'pro');
        unlockContent(_currentTier);
      }} else {{
        localStorage.removeItem('opl_license_key');
      }}
    }}
    // Load purchase URL from licenses.json
    try {{
      if (!_licenseData) {{
        var resp = await fetch('licenses.json');
        _licenseData = await resp.json();
      }}
      if (_licenseData && _licenseData.stripe_urls) {{
        if (_licenseData.stripe_urls.pro) purchaseUrl.href = _licenseData.stripe_urls.pro;
      }}
    }} catch(e) {{}}
  }}

  window.activateLicense = async function() {{
    var key = licenseInput.value.trim().toUpperCase();
    licenseError.textContent = '';
    if (!key) {{ licenseError.textContent = 'Please enter a license key.'; return; }}
    if (!key.match(/^(PRO|ENT)-[A-Z0-9]{{4}}-[A-Z0-9]{{4}}-[A-Z0-9]{{4}}$/)) {{
      licenseError.textContent = 'Invalid format. Expected: PRO-XXXX-XXXX-XXXX';
      return;
    }}
    var valid = await validateAndActivate(key);
    if (valid) {{
      localStorage.setItem('opl_license_key', key);
      var tier = key.startsWith('ENT') ? 'enterprise' : 'pro';
      updateBadge(tier);
      unlockContent(tier);
      closeModal();
    }} else {{
      licenseError.textContent = 'Invalid or expired license key.';
    }}
  }};

  window.closeModal = function() {{
    activateOverlay.classList.remove('active');
    licenseInput.value = '';
    licenseError.textContent = '';
  }};

  window.showTierAction = function() {{
    if (_currentTier === 'free') {{
      var pricingSection = document.getElementById('pricing');
      if (pricingSection) pricingSection.scrollIntoView({{ behavior: 'smooth' }});
      else activateOverlay.classList.add('active');
    }} else {{
      activateOverlay.classList.add('active');
      document.querySelector('.modal h2').textContent = 'License Active — ' + _currentTier.toUpperCase();
      document.getElementById('licenseKeyInput').value = localStorage.getItem('opl_license_key') || '';
    }}
  }};

  activateOverlay.addEventListener('click', function(e) {{
    if (e.target === activateOverlay) closeModal();
  }});

  licenseInput.addEventListener('keydown', function(e) {{
    if (e.key === 'Enter') window.activateLicense();
  }});

  initTierGate();
}})();
</script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<script>
{chart_script}
</script>
</body>
</html>"""


class DashboardAgent(BaseAgent):
    """Agent that converts the markdown report to an interactive HTML dashboard.

    Generates:
    - site/index.html — Interactive report with charts
    - site/data.json  — Summary stats JSON endpoint
    - site/.nojekyll  — Prevents Jekyll processing
    """

    @property
    def name(self) -> str:
        return "dashboard"

    def execute(self, upstream_results: list | None = None) -> AgentResult:
        try:
            import markdown
        except ImportError:
            _logger.error("DashboardAgent: 'markdown' package not installed. Run: pip install markdown")
            return AgentResult(
                agent_name=self.name,
                status="failed",
                errors=["markdown package not installed"],
            )

        config = load_config()
        report_config = config.get("report", {})
        report_filename = report_config.get(
            "output_path", "Failed_Startups_Manufacturing_Revival_Report.md"
        )
        report_path = get_project_root() / report_filename
        site_dir = get_project_root() / self.config.get("site_dir", "site")

        if not report_path.exists():
            return AgentResult(
                agent_name=self.name,
                status="failed",
                errors=[f"Report file not found: {report_path}"],
            )

        _logger.info("DashboardAgent: Converting %s to HTML", report_path)

        # Read and convert markdown
        md_content = report_path.read_text(encoding="utf-8")
        html_body = markdown.markdown(
            md_content,
            extensions=["tables", "fenced_code", "toc", "smarty"],
        )

        # Strip {#id} syntax from visible heading text
        html_body = re.sub(
            r"(<h[1-6][^>]*>)((?:(?!</h[1-6]>).*)?)\s*\{#[^}]+\}\s*(</h[1-6]>)",
            r"\1\2\3",
            html_body,
        )

        # Build navigation from headings (deferred — must include gmv/llm sections)

        # Fetch stats from database
        stats_html, stats_json = _fetch_stats()

        # Build charts
        include_charts = self.config.get("include_charts", True)
        charts_html = ""
        chart_script = ""
        if include_charts:
            charts_html, chart_script = _build_charts()

        # Global Market Viability monitoring
        gmv_stats = _fetch_gmv_status()
        gmv_monitor_html = _build_gmv_monitor_html(gmv_stats)
        gmv_charts_html, gmv_chart_script = _build_gmv_charts(gmv_stats) if include_charts else ("", "")

        # LLM Infrastructure status
        llm_status = _fetch_ollama_status()
        llm_infra_html = _build_llm_infrastructure_html(llm_status)

        # LLM Pricing comparison
        llm_pricing_data = _fetch_llm_pricing_data()
        llm_pricing_html = _build_llm_pricing_html(llm_pricing_data)

        # Ollama Usage tracking
        ollama_usage_data = _fetch_ollama_usage_data()
        ollama_usage_html = _build_ollama_usage_html(ollama_usage_data)
        ollama_usage_charts_html, ollama_usage_chart_script = (
            _build_ollama_usage_charts(ollama_usage_data) if include_charts else ("", "")
        )

        # LLM Model Portfolio
        portfolio_data = _fetch_portfolio_data()
        portfolio_html = _build_portfolio_html(portfolio_data)
        portfolio_charts_html, portfolio_chart_script = (
            _build_portfolio_charts(portfolio_data) if include_charts else ("", "")
        )

        # LLM Benchmark Tracker
        benchmark_data = _fetch_benchmark_data()
        benchmark_html = _build_benchmark_html(benchmark_data)
        benchmark_charts_html, benchmark_chart_script = (
            _build_benchmark_charts(benchmark_data) if include_charts else ("", "")
        )

        # LLM Cost Optimizer
        optimizer_data = _fetch_optimizer_data()
        optimizer_html = _build_optimizer_html(optimizer_data)

        # Knowledge Graph
        kg_data = _fetch_knowledge_graph_data()
        kg_html = _build_knowledge_graph_html(kg_data)
        kg_charts_html, kg_chart_script = (
            _build_knowledge_graph_charts(kg_data) if include_charts else ("", "")
        )

        # Revenue Monitoring (Pro-gated)
        rev_data = _fetch_revenue_data()
        rev_html = _build_revenue_html(rev_data)
        gated_revenue = _wrap_gated("pro", rev_html)
        rev_charts_html, rev_chart_script = (
            _build_revenue_charts(rev_data) if include_charts else ("", "")
        )

        # Pipeline Health (Span)
        span_data = _fetch_span_data()
        span_html = _build_span_html(span_data)

        # Build navigation from headings (after all sections are generated)
        # Pro-gated sections: portfolio, benchmarks, optimizer, opportunity deep dives
        pro_lock = _build_pro_lock_overlay("pro-opportunity-deep-dives")
        gated_portfolio = _wrap_gated("pro", portfolio_html)
        gated_benchmarks = _wrap_gated("pro", benchmark_html)
        gated_optimizer = _wrap_gated("pro", optimizer_html)

        all_body = (gmv_monitor_html + gmv_charts_html + html_body + llm_infra_html
                    + llm_pricing_html + ollama_usage_html + gated_portfolio
                    + gated_benchmarks + gated_optimizer + kg_html + gated_revenue
                    + span_html + pro_lock)

        # Pricing page section
        pricing_html = _build_pricing_html()

        nav_html = _generate_nav(all_body)

        # Assemble final HTML
        full_html = HTML_TEMPLATE.format(
            title="Opportunity Intelligence Platform — Live Dashboard",
            generated=datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M UTC"),
            nav=nav_html,
            stats=stats_html + gmv_monitor_html,
            charts=(charts_html + gmv_charts_html + ollama_usage_charts_html
                    + portfolio_charts_html + benchmark_charts_html + kg_charts_html
                    + rev_charts_html),
            body=all_body,
            pricing_section=pricing_html,
            chart_script=(chart_script + gmv_chart_script + ollama_usage_chart_script
                          + portfolio_chart_script + benchmark_chart_script + kg_chart_script
                          + rev_chart_script),
        )

        # Write output files
        site_dir.mkdir(parents=True, exist_ok=True)
        (site_dir / "index.html").write_text(full_html, encoding="utf-8")
        (site_dir / "data.json").write_text(
            json.dumps({
                **stats_json,
                "gmv_monitoring": gmv_stats,
                "llm_infrastructure": llm_status,
                "llm_pricing": llm_pricing_data,
                "ollama_usage": ollama_usage_data,
                "llm_portfolio": portfolio_data,
                "llm_benchmarks": benchmark_data,
                "llm_optimizer": optimizer_data,
                "knowledge_graph": kg_data,
            }, indent=2, default=str),
            encoding="utf-8",
        )
        (site_dir / ".nojekyll").touch()

        file_size = (site_dir / "index.html").stat().st_size
        _logger.info("DashboardAgent: site/index.html generated (%d bytes)", file_size)

        return AgentResult(
            agent_name=self.name,
            status="success",
            data={
                "html_path": str(site_dir / "index.html"),
                "site_dir": str(site_dir),
                "html_size_bytes": file_size,
                "records_affected": 1,
            },
        )


def _generate_nav(html_body: str) -> str:
    """Extract headings and build sidebar navigation."""
    nav_items = []

    # Match headings WITH id attributes (primary path — what markdown library produces)
    for match in re.finditer(
        r'<(h[23])\s+id="([^"]*)"[^>]*>(.*?)</\1>', html_body
    ):
        tag, heading_id, text = match.group(1), match.group(2), match.group(3)
        clean = re.sub(r"<[^>]+>", "", text)  # Strip HTML tags
        clean = re.sub(r"\s*\{#[^}]+\}", "", clean)  # Strip {#id} syntax
        clean = clean.strip()
        if not clean:
            continue
        css_class = "h2" if tag == "h2" else "h3"
        nav_items.append(
            f'<a href="#{heading_id}" class="{css_class}">{clean}</a>'
        )

    # Fallback: headings WITHOUT id attributes
    if not nav_items:
        for match in re.finditer(r"<(h[23])>(.*?)</\1>", html_body):
            tag, text = match.group(1), match.group(2)
            clean = re.sub(r"<[^>]+>", "", text)
            clean = re.sub(r"\s*\{#[^}]+\}", "", clean)
            anchor = re.sub(r"[^a-z0-9]+", "-", clean.lower()).strip("-")
            if not anchor:
                continue
            css_class = "h2" if tag == "h2" else "h3"
            nav_items.append(
                f'<a href="#{anchor}" class="{css_class}">{clean}</a>'
            )

    return "\n".join(nav_items[:50])


def _fetch_stats():
    """Fetch summary statistics from the database."""
    stats_json = {}
    try:
        conn = get_connection()
        schema.init_schema(conn)

        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM failed_startups")
        total_startups = cursor.fetchone()["cnt"]
        cursor.execute(
            "SELECT COUNT(*) as cnt FROM failed_startups WHERE manufacturing_sub_sector IS NOT NULL"
        )
        mfg_startups = cursor.fetchone()["cnt"]
        cursor.execute("SELECT COUNT(*) as cnt FROM news_articles")
        total_articles = cursor.fetchone()["cnt"]
        cursor.execute(
            "SELECT COUNT(*) as cnt FROM news_articles WHERE is_manufacturing = 1"
        )
        mfg_articles = cursor.fetchone()["cnt"]
        cursor.execute(
            """SELECT name, sector, year_shutdown FROM failed_startups
               ORDER BY collected_at DESC LIMIT 5"""
        )
        recent = cursor.fetchall()
        cursor.close()

        stats_json = {
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "total_startups": total_startups,
            "manufacturing_startups": mfg_startups,
            "total_articles": total_articles,
            "manufacturing_articles": mfg_articles,
            "recent_failures": [dict(r) for r in recent],
        }

        conn.close()
    except Exception as e:
        _logger.warning("DashboardAgent: Could not fetch stats: %s", e)
        stats_json = {"last_updated": datetime.now(timezone.utc).isoformat(), "error": str(e)}

    # Build stat cards HTML
    cards = [
        ("total_startups", "Total Startups Tracked", "&#128640;", "accent-blue"),
        ("mfg_startups", "Manufacturing Failures", "&#9888;", "accent-red"),
        ("total_articles", "News Articles", "&#128240;", "accent-green"),
        ("mfg_articles", "Mfg-Related News", "&#128202;", "accent-amber"),
    ]
    value_keys = {
        "total_startups": "total_startups",
        "mfg_startups": "manufacturing_startups",
        "total_articles": "total_articles",
        "mfg_articles": "manufacturing_articles",
    }
    stats_html = '<div class="stats-grid">\n'
    for key, label, icon, accent in cards:
        value = stats_json.get(value_keys[key], 0)
        stats_html += (
            f'<div class="stat-card {accent}">'
            f'<span class="icon">{icon}</span>'
            f'<div class="value">{value}</div>'
            f'<div class="label">{label}</div>'
            f'</div>\n'
        )
    stats_html += "</div>"

    return stats_html, stats_json


def _ollama_api(endpoint: str, payload: dict | None = None, timeout: float = 5) -> dict | None:
    """Make a request to the Ollama API and return parsed JSON, or None on failure."""
    url = f"http://localhost:11434{endpoint}"
    try:
        data = json.dumps(payload).encode() if payload else None
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode())

        # Track token usage from chat completions
        if endpoint == "/api/chat" and result:
            _track_chat_tokens(result, payload)

        return result
    except Exception:
        return None


def _track_chat_tokens(result: dict, payload: dict | None = None) -> None:
    """Append token counts from a chat completion to the tracker file."""
    prompt_tokens = result.get("prompt_eval_count", 0)
    completion_tokens = result.get("eval_count", 0)
    model = payload.get("model", "unknown") if payload else "unknown"

    if prompt_tokens == 0 and completion_tokens == 0:
        return

    try:
        from agents.ollama_usage_tracker import _track_inference
        _track_inference(model, prompt_tokens, completion_tokens)
    except Exception as e:
        _logger.debug("Could not track Ollama tokens: %s", e)


def _fetch_ollama_status() -> dict:
    """Query Ollama for detailed LLM infrastructure status at build time."""
    info = {
        "status": "offline",
        "endpoint": "http://localhost:11434",
        "models": [],
        "loaded_models": [],
        "total_vram_mb": 0,
        "test_latency_s": 0,
        "test_tokens": 0,
        "model_details": {},
    }

    # 1) Check connectivity via /api/tags
    tags = _ollama_api("/api/tags")
    if tags is None:
        return info
    info["status"] = "online"
    info["models"] = [
        {"name": m["name"], "size_bytes": m.get("size", 0)}
        for m in tags.get("models", [])
    ]

    # 2) Check what's currently loaded in VRAM via /api/ps
    ps = _ollama_api("/api/ps")
    if ps:
        info["loaded_models"] = [
            {"name": m["name"], "size_bytes": m.get("size", 0), "vram_bytes": m.get("vram", 0)}
            for m in ps.get("models", [])
        ]
        info["total_vram_mb"] = round(sum(m.get("vram", 0) for m in ps.get("models", [])) / (1024 * 1024))

    # 3) Get detailed model info for first loaded model (or first available)
    primary_model = None
    if info["loaded_models"]:
        primary_model = info["loaded_models"][0]["name"]
    elif info["models"]:
        primary_model = info["models"][0]["name"]

    if primary_model:
        show = _ollama_api("/api/show", {"name": primary_model})
        if show:
            details = show.get("details", {})
            model_info = show.get("model_info", {})
            info["model_details"] = {
                "name": primary_model,
                "family": details.get("family", ""),
                "format": details.get("format", ""),
                "quantization_level": details.get("quantization_level", ""),
                "parameter_count": model_info.get("general.parameter_count", 0),
                "quantization_version": model_info.get("general.quantization_version", ""),
                "license": show.get("license", "")[:120],
            }

    # 4) Run a quick inference latency test
    test_result = _ollama_api(
        "/api/chat",
        {
            "model": primary_model or "llama3",
            "messages": [
                {"role": "system", "content": "Reply with one word."},
                {"role": "user", "content": "Hi"},
            ],
            "stream": False,
        },
        timeout=30,
    )
    if test_result:
        info["test_latency_s"] = round(test_result.get("eval_duration", 0) / 1e9, 2)
        info["test_tokens"] = test_result.get("eval_count", 0)

    return info


def _build_llm_infrastructure_html(llm: dict) -> str:
    """Build a detailed LLM Infrastructure monitoring section for the dashboard."""
    if not llm or llm.get("status") == "offline":
        return ""

    status_color = "#10B981" if llm["status"] == "online" else "#EF4444"
    status_label = "ONLINE" if llm["status"] == "online" else "OFFLINE"

    details = llm.get("model_details", {})
    params = details.get("parameter_count", 0)
    params_str = f"{params / 1e9:.1f}B" if params >= 1e9 else f"{params / 1e6:.0f}M" if params else "N/A"
    vram = llm.get("total_vram_mb", 0)
    vram_str = f"{vram / 1024:.1f} GB" if vram >= 1024 else f"{vram} MB"
    latency = llm.get("test_latency_s", 0)
    tokens = llm.get("test_tokens", 0)
    tokens_per_sec = round(tokens / latency, 1) if latency > 0 and tokens > 0 else 0

    # Latency color coding
    if tokens_per_sec >= 15:
        latency_color = "#10B981"
        latency_label = "FAST"
    elif tokens_per_sec >= 5:
        latency_color = "#F59E0B"
        latency_label = "MODERATE"
    else:
        latency_color = "#EF4444"
        latency_label = "SLOW"

    # Available models list
    models_list = ""
    for m in llm.get("models", []):
        size_gb = m.get("size_bytes", 0) / (1024**3)
        is_loaded = any(lm["name"] == m["name"] for lm in llm.get("loaded_models", []))
        loaded_badge = '<span style="display:inline-block;padding:1px 6px;border-radius:8px;font-size:10px;font-weight:600;background:#10B981;color:white;margin-left:6px;">LOADED</span>' if is_loaded else ""
        models_list += f"""
        <tr>
          <td style="padding:8px 12px;border-bottom:1px solid var(--border);font-weight:500;">{m['name']}</td>
          <td style="padding:8px 12px;border-bottom:1px solid var(--border);color:var(--text-secondary);">{size_gb:.1f} GB</td>
          <td style="padding:8px 12px;border-bottom:1px solid var(--border);">{loaded_badge if loaded_badge else '<span style="color:var(--text-secondary);font-size:12px;">Available</span>'}</td>
        </tr>"""

    html = f"""
    <div style="margin-top: 32px; border-top: 2px solid var(--border); padding-top: 24px;">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;">
        <h2 id="llm-infrastructure" style="margin:0;font-size:20px;font-weight:700;color:var(--text);">LLM Infrastructure</h2>
        <div style="display:flex;align-items:center;gap:10px;">
          <span style="display:inline-block;padding:2px 10px;border-radius:12px;font-size:11px;font-weight:600;background:{status_color};color:white;">{status_label}</span>
          <span style="display:inline-block;padding:2px 10px;border-radius:12px;font-size:11px;font-weight:600;background:{latency_color};color:white;">{latency_label} &middot; {tokens_per_sec} tok/s</span>
        </div>
      </div>

      <div class="stats-grid">
        <div class="stat-card accent-blue">
          <span class="icon">&#129302;</span>
          <div class="value">{details.get('name', 'N/A').split(':')[0]}</div>
          <div class="label">Active Model</div>
        </div>
        <div class="stat-card accent-green">
          <span class="icon">&#128202;</span>
          <div class="value">{params_str}</div>
          <div class="label">Parameters</div>
        </div>
        <div class="stat-card accent-amber">
          <span class="icon">&#128451;</span>
          <div class="value">{vram_str}</div>
          <div class="label">VRAM Usage</div>
        </div>
        <div class="stat-card accent-red">
          <span class="icon">&#9201;</span>
          <div class="value">{latency}s</div>
          <div class="label">Inference Latency</div>
          <div style="font-size:11px;color:var(--text-secondary);margin-top:4px;">{tokens} tokens generated</div>
        </div>
      </div>

      <div style="margin-top:20px;background:var(--bg-secondary);border-radius:10px;border:1px solid var(--border);overflow:hidden;">
        <div style="padding:12px 16px;border-bottom:1px solid var(--border);font-weight:600;font-size:14px;color:var(--text);">
          Model Specifications
        </div>
        <table style="width:100%;border-collapse:collapse;font-size:13px;">
          <tr>
            <td style="padding:8px 16px;border-bottom:1px solid var(--border);color:var(--text-secondary);width:35%;">Family</td>
            <td style="padding:8px 16px;border-bottom:1px solid var(--border);font-weight:500;">{details.get('family', 'N/A').title()}</td>
          </tr>
          <tr>
            <td style="padding:8px 16px;border-bottom:1px solid var(--border);color:var(--text-secondary);">Format</td>
            <td style="padding:8px 16px;border-bottom:1px solid var(--border);font-weight:500;">{details.get('format', 'N/A').upper()}</td>
          </tr>
          <tr>
            <td style="padding:8px 16px;border-bottom:1px solid var(--border);color:var(--text-secondary);">Quantization</td>
            <td style="padding:8px 16px;border-bottom:1px solid var(--border);font-weight:500;">{details.get('quantization_level', 'N/A')}</td>
          </tr>
          <tr>
            <td style="padding:8px 16px;border-bottom:1px solid var(--border);color:var(--text-secondary);">API Endpoint</td>
            <td style="padding:8px 16px;border-bottom:1px solid var(--border);font-weight:500;font-family:monospace;font-size:12px;">{llm.get('endpoint', 'N/A')}</td>
          </tr>
          <tr>
            <td style="padding:8px 16px;color:var(--text-secondary);">License</td>
            <td style="padding:8px 16px;font-weight:500;font-size:12px;">{details.get('license', 'N/A')}</td>
          </tr>
        </table>
      </div>

      <div style="margin-top:16px;background:var(--bg-secondary);border-radius:10px;border:1px solid var(--border);overflow:hidden;">
        <div style="padding:12px 16px;border-bottom:1px solid var(--border);font-weight:600;font-size:14px;color:var(--text);">
          Available Models
        </div>
        <table style="width:100%;border-collapse:collapse;font-size:13px;">
          <thead>
            <tr style="font-size:11px;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.5px;">
              <th style="padding:8px 12px;text-align:left;border-bottom:1px solid var(--border);">Model</th>
              <th style="padding:8px 12px;text-align:left;border-bottom:1px solid var(--border);">Size</th>
              <th style="padding:8px 12px;text-align:left;border-bottom:1px solid var(--border);">Status</th>
            </tr>
          </thead>
          <tbody>
            {models_list}
          </tbody>
        </table>
      </div>
    </div>
    """
    return html


# ── LLM Pricing Comparison ──────────────────────────────────────────────

def _fetch_llm_pricing_data() -> dict:
    """Fetch LLM pricing data from the database."""
    pricing: dict = {
        "providers": [],
        "models": [],
        "last_updated": "",
        "model_count": 0,
        "cheapest_input": {},
        "cheapest_output": {},
    }

    try:
        conn = get_connection()
        schema.init_schema(conn)
        cursor = conn.cursor()

        cursor.execute(
            """SELECT provider, model_name, model_id, input_price_per_1m,
                      output_price_per_1m, context_window, modality, pricing_tier, notes
               FROM llm_pricing
               ORDER BY provider, input_price_per_1m ASC"""
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        if not rows:
            return pricing

        pricing["models"] = [dict(r) for r in rows]
        pricing["model_count"] = len(rows)
        pricing["providers"] = sorted(set(m["provider"] for m in pricing["models"]))

        # Find cheapest (non-free) models
        paid = [m for m in pricing["models"] if m["input_price_per_1m"] > 0]
        if paid:
            cheapest_in = min(paid, key=lambda r: r["input_price_per_1m"])
            cheapest_out = min(paid, key=lambda r: r["output_price_per_1m"])
            pricing["cheapest_input"] = {
                "provider": cheapest_in["provider"],
                "model": cheapest_in["model_name"],
                "price": cheapest_in["input_price_per_1m"],
            }
            pricing["cheapest_output"] = {
                "provider": cheapest_out["provider"],
                "model": cheapest_out["model_name"],
                "price": cheapest_out["output_price_per_1m"],
            }

    except Exception as e:
        _logger.warning("DashboardAgent: Could not fetch LLM pricing: %s", e)

    return pricing


def _build_llm_pricing_html(pricing: dict) -> str:
    """Build LLM Pricing Comparison section for the dashboard."""
    if not pricing or pricing.get("model_count", 0) == 0:
        return ""

    models = pricing.get("models", [])
    providers = pricing.get("providers", [])
    cheapest_in = pricing.get("cheapest_input", {})
    cheapest_out = pricing.get("cheapest_output", {})
    cheapest_in_price = cheapest_in.get("price", -1)
    cheapest_out_price = cheapest_out.get("price", -1)

    # Build table rows
    table_rows = ""
    for m in models:
        in_price = m["input_price_per_1m"]
        out_price = m["output_price_per_1m"]
        ctx = m.get("context_window", 0)
        if ctx >= 1_000_000:
            ctx_str = f"{ctx / 1_000_000:.0f}M"
        elif ctx >= 1000:
            ctx_str = f"{ctx / 1000:.0f}K"
        else:
            ctx_str = str(ctx) if ctx else "N/A"

        in_color = "#10B981" if in_price > 0 and in_price == cheapest_in_price else "inherit"
        out_color = "#10B981" if out_price > 0 and out_price == cheapest_out_price else "inherit"

        notes = m.get("notes", "")
        notes_cell = f'<span style="color:var(--text-secondary);font-size:11px;margin-left:6px;">{notes}</span>' if notes else ""

        table_rows += f"""
        <tr>
          <td style="padding:8px 12px;border-bottom:1px solid var(--border);font-weight:500;">{m['provider']}</td>
          <td style="padding:8px 12px;border-bottom:1px solid var(--border);">{m['model_name']}{notes_cell}</td>
          <td style="padding:8px 12px;border-bottom:1px solid var(--border);color:{in_color};font-weight:600;text-align:right;">
            {'Free' if in_price == 0 else f'${in_price:.2f}'}
          </td>
          <td style="padding:8px 12px;border-bottom:1px solid var(--border);color:{out_color};font-weight:600;text-align:right;">
            {'Free' if out_price == 0 else f'${out_price:.2f}'}
          </td>
          <td style="padding:8px 12px;border-bottom:1px solid var(--border);color:var(--text-secondary);text-align:right;">{ctx_str}</td>
          <td style="padding:8px 12px;border-bottom:1px solid var(--border);color:var(--text-secondary);font-size:12px;">{m.get('modality', 'text')}</td>
        </tr>"""

    html = f"""
    <div style="margin-top: 32px; border-top: 2px solid var(--border); padding-top: 24px;">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;">
        <h2 id="llm-pricing" style="margin:0;font-size:20px;font-weight:700;color:var(--text);">LLM Pricing Comparison</h2>
        <span style="display:inline-block;padding:2px 10px;border-radius:12px;font-size:11px;font-weight:600;background:#3B82F6;color:white;">
          {len(providers)} PROVIDERS
        </span>
      </div>

      <div class="stats-grid">
        <div class="stat-card accent-blue">
          <span class="icon">&#127760;</span>
          <div class="value">{len(providers)}</div>
          <div class="label">Providers Tracked</div>
        </div>
        <div class="stat-card accent-green">
          <span class="icon">&#128202;</span>
          <div class="value">{pricing['model_count']}</div>
          <div class="label">Models Tracked</div>
        </div>
        <div class="stat-card accent-amber">
          <span class="icon">&#128176;</span>
          <div class="value">${cheapest_in.get('price', 0):.2f}</div>
          <div class="label">Cheapest Input/1M</div>
          <div style="font-size:11px;color:var(--text-secondary);margin-top:4px;">{cheapest_in.get('provider', 'N/A')}</div>
        </div>
        <div class="stat-card accent-red">
          <span class="icon">&#128176;</span>
          <div class="value">${cheapest_out.get('price', 0):.2f}</div>
          <div class="label">Cheapest Output/1M</div>
          <div style="font-size:11px;color:var(--text-secondary);margin-top:4px;">{cheapest_out.get('provider', 'N/A')}</div>
        </div>
      </div>

      <div style="background:var(--bg-secondary);border-radius:10px;border:1px solid var(--border);overflow:hidden;margin-top:16px;">
        <div style="padding:12px 16px;border-bottom:1px solid var(--border);font-weight:600;font-size:14px;color:var(--text);">
          Price Comparison (USD per 1M tokens) &middot; <span style="color:#10B981;">Green = cheapest</span>
        </div>
        <div style="overflow-x:auto;">
          <table style="width:100%;border-collapse:collapse;font-size:13px;">
            <thead>
              <tr style="font-size:11px;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.5px;">
                <th style="padding:8px 12px;text-align:left;border-bottom:1px solid var(--border);">Provider</th>
                <th style="padding:8px 12px;text-align:left;border-bottom:1px solid var(--border);">Model</th>
                <th style="padding:8px 12px;text-align:right;border-bottom:1px solid var(--border);">Input</th>
                <th style="padding:8px 12px;text-align:right;border-bottom:1px solid var(--border);">Output</th>
                <th style="padding:8px 12px;text-align:right;border-bottom:1px solid var(--border);">Context</th>
                <th style="padding:8px 12px;text-align:left;border-bottom:1px solid var(--border);">Modality</th>
              </tr>
            </thead>
            <tbody>
              {table_rows}
            </tbody>
          </table>
        </div>
      </div>
    </div>
    """
    return html


# ── Ollama Usage Tracking ───────────────────────────────────────────────

def _fetch_ollama_usage_data() -> dict:
    """Fetch Ollama usage history and cost equivalence from DB + tracker."""
    usage: dict = {
        "total_prompt_tokens": 0,
        "total_completion_tokens": 0,
        "total_tokens": 0,
        "inference_count": 0,
        "cost_equivalence": {},
        "snapshots": [],
        "status": "no_data",
    }

    # Read from tracker file for current totals
    tracker_file = get_project_root() / "data" / "cache" / "ollama_token_tracker.json"
    if tracker_file.exists():
        try:
            tracker = json.loads(tracker_file.read_text(encoding="utf-8"))
            totals = tracker.get("totals", {})
            usage["total_prompt_tokens"] = totals.get("total_prompt_tokens", 0)
            usage["total_completion_tokens"] = totals.get("total_completion_tokens", 0)
            usage["total_tokens"] = totals.get("total_tokens", 0)
            usage["inference_count"] = totals.get("inference_count", 0)
            usage["status"] = "tracking"
        except Exception as e:
            _logger.debug("Could not read Ollama token tracker: %s", e)

    # Read historical snapshots from DB for trend data
    try:
        conn = get_connection()
        schema.init_schema(conn)
        cursor = conn.cursor()
        cursor.execute(
            """SELECT snapshot_at, model_name, prompt_tokens, completion_tokens,
                      total_tokens, inference_count, cost_equivalence_json
               FROM ollama_usage_snapshots
               ORDER BY snapshot_at DESC
               LIMIT 30"""
        )
        snapshots = cursor.fetchall()
        cursor.close()
        conn.close()

        usage["snapshots"] = [dict(s) for s in snapshots]

        # Use the latest snapshot's cost equivalence
        if snapshots:
            latest = snapshots[0]
            ce = latest.get("cost_equivalence_json")
            if ce:
                try:
                    usage["cost_equivalence"] = json.loads(ce) if isinstance(ce, str) else ce
                except Exception:
                    pass
    except Exception as e:
        _logger.warning("Could not fetch Ollama usage from DB: %s", e)

    return usage


def _build_ollama_usage_html(usage: dict) -> str:
    """Build Ollama Usage & Cost Equivalence section."""
    if not usage or usage.get("status") == "no_data":
        return ""

    total_tok = usage.get("total_tokens", 0)
    prompt_tok = usage.get("total_prompt_tokens", 0)
    complet_tok = usage.get("total_completion_tokens", 0)
    inf_count = usage.get("inference_count", 0)
    cost_equiv = usage.get("cost_equivalence", {})

    # Format token counts
    def fmt_tokens(n):
        if n >= 1_000_000:
            return f"{n / 1_000_000:.1f}M"
        if n >= 1000:
            return f"{n / 1000:.1f}K"
        return str(n)

    # Find max cost for context
    max_cost = max(cost_equiv.values()) if cost_equiv else 1
    cost_rows = ""
    for name, cost in sorted(cost_equiv.items(), key=lambda x: x[1], reverse=True)[:8]:
        pct = (cost / max_cost * 100) if max_cost > 0 else 0
        bar_color = "#EF4444" if pct > 66 else "#F59E0B" if pct > 33 else "#10B981"
        cost_rows += f"""
        <tr>
          <td style="padding:6px 12px;border-bottom:1px solid var(--border);font-size:12px;">{name}</td>
          <td style="padding:6px 12px;border-bottom:1px solid var(--border);font-weight:600;font-size:12px;">
            ${cost:.2f}
          </td>
          <td style="padding:6px 12px;border-bottom:1px solid var(--border);width:40%;">
            <div style="background:var(--border);border-radius:4px;height:8px;overflow:hidden;">
              <div style="height:100%;width:{pct}%;background:{bar_color};border-radius:4px;"></div>
            </div>
          </td>
        </tr>"""

    status_label = "TRACKING" if usage.get("status") == "tracking" else "NO DATA"
    status_color = "#10B981" if usage.get("status") == "tracking" else "#6c757d"

    html = f"""
    <div style="margin-top: 32px; border-top: 2px solid var(--border); padding-top: 24px;">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;">
        <h2 id="ollama-usage" style="margin:0;font-size:20px;font-weight:700;color:var(--text);">Ollama Usage &amp; Cost Equivalence</h2>
        <span style="display:inline-block;padding:2px 10px;border-radius:12px;font-size:11px;font-weight:600;background:{status_color};color:white;">{status_label}</span>
      </div>

      <div class="stats-grid">
        <div class="stat-card accent-blue">
          <span class="icon">&#128256;</span>
          <div class="value">{fmt_tokens(total_tok)}</div>
          <div class="label">Total Tokens</div>
          <div style="font-size:11px;color:var(--text-secondary);margin-top:4px;">
            {fmt_tokens(prompt_tok)} in / {fmt_tokens(complet_tok)} out
          </div>
        </div>
        <div class="stat-card accent-green">
          <span class="icon">&#128640;</span>
          <div class="value">{inf_count}</div>
          <div class="label">Inferences</div>
        </div>
        <div class="stat-card accent-amber">
          <span class="icon">&#128176;</span>
          <div class="value">${max(cost_equiv.values()):.2f}</div>
          <div class="label">Max Equivalent Cost</div>
          <div style="font-size:11px;color:var(--text-secondary);margin-top:4px;">If hosted on most expensive</div>
        </div>
        <div class="stat-card accent-red">
          <span class="icon">&#127775;</span>
          <div class="value">$0.00</div>
          <div class="label">Actual Cost</div>
          <div style="font-size:11px;color:var(--text-secondary);margin-top:4px;">Self-hosted via Ollama</div>
        </div>
      </div>

      {""
      if not cost_rows else f"""
      <div style="margin-top:16px;background:var(--bg-secondary);border-radius:10px;border:1px solid var(--border);overflow:hidden;">
        <div style="padding:12px 16px;border-bottom:1px solid var(--border);font-weight:600;font-size:14px;color:var(--text);">
          Cost Equivalence — What this usage would cost on paid APIs
        </div>
        <table style="width:100%;border-collapse:collapse;font-size:13px;">
          <thead>
            <tr style="font-size:11px;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.5px;">
              <th style="padding:8px 12px;text-align:left;border-bottom:1px solid var(--border);">Provider</th>
              <th style="padding:8px 12px;text-align:left;border-bottom:1px solid var(--border);">Est. Cost</th>
              <th style="padding:8px 12px;text-align:left;border-bottom:1px solid var(--border);">Relative</th>
            </tr>
          </thead>
          <tbody>
            {cost_rows}
          </tbody>
        </table>
      </div>
      """}
    </div>
    """
    return html


def _build_ollama_usage_charts(usage: dict):
    """Build Ollama usage charts — token trend line + cost equivalence bar."""
    charts_html = ""
    chart_script = ""

    snapshots = usage.get("snapshots", [])
    if not snapshots:
        return charts_html, chart_script

    # Reverse for chronological order
    snaps = list(reversed(snapshots))
    labels = [s["snapshot_at"][:16] if len(s["snapshot_at"]) > 16 else s["snapshot_at"] for s in snaps]
    total_tokens = [s.get("total_tokens", 0) for s in snaps]
    prompt_tokens = [s.get("prompt_tokens", 0) for s in snaps]
    completion_tokens = [s.get("completion_tokens", 0) for s in snaps]

    charts_html += '<h2 id="ollama-usage-charts" style="font-size:16px;font-weight:700;margin:0 0 12px 0;color:var(--text);">Ollama Usage Charts</h2>'
    charts_html += '<div class="charts-grid">'

    # Chart 1: Token usage over time
    charts_html += '<div class="chart-container"><h3>Token Usage Over Time</h3><canvas id="ollamaUsageChart"></canvas></div>'

    chart_script += f"""
    new Chart(document.getElementById('ollamaUsageChart'), {{
        type: 'line',
        data: {{
            labels: {json.dumps(labels)},
            datasets: [
                {{ label: 'Total', data: {json.dumps(total_tokens)}, borderColor: '#3B82F6',
                   backgroundColor: 'rgba(59,130,246,0.1)', fill: true, tension: 0.3, pointRadius: 3 }},
                {{ label: 'Prompt', data: {json.dumps(prompt_tokens)}, borderColor: '#10B981',
                   backgroundColor: 'rgba(16,185,129,0.05)', fill: false, tension: 0.3, pointRadius: 2 }},
                {{ label: 'Completion', data: {json.dumps(completion_tokens)}, borderColor: '#F59E0B',
                   backgroundColor: 'rgba(245,158,11,0.05)', fill: false, tension: 0.3, pointRadius: 2 }}
            ]
        }},
        options: {{
            responsive: true,
            plugins: {{
                tooltip: {{ mode: 'index', intersect: false }},
                legend: {{ position: 'bottom', labels: {{ boxWidth: 12, padding: 12 }} }}
            }},
            scales: {{
                y: {{ beginAtZero: true, grid: {{ color: 'rgba(128,128,128,0.1)' }} }}
            }}
        }}
    }});
    """

    # Chart 2: Cost equivalence bar
    cost_equiv = usage.get("cost_equivalence", {})
    if cost_equiv:
        # Limit to top 8 providers by cost
        sorted_costs = sorted(cost_equiv.items(), key=lambda x: x[1], reverse=True)[:8]
        cost_labels = [name for name, _ in sorted_costs]
        cost_data = [cost for _, cost in sorted_costs]

        charts_html += '<div class="chart-container"><h3>Cost Equivalence (USD)</h3><canvas id="ollamaCostChart"></canvas></div>'
        charts_html += '</div>'

        chart_script += f"""
        new Chart(document.getElementById('ollamaCostChart'), {{
            type: 'bar',
            data: {{
                labels: {json.dumps(cost_labels)},
                datasets: [{{
                    label: 'Equivalent Cost ($)',
                    data: {json.dumps(cost_data)},
                    backgroundColor: function(ctx) {{
                        var v = ctx.raw;
                        var max = Math.max(...{json.dumps(cost_data)});
                        if (v >= max * 0.66) return '#EF4444';
                        if (v >= max * 0.33) return '#F59E0B';
                        return '#10B981';
                    }},
                    borderRadius: 4,
                    maxBarThickness: 40
                }}]
            }},
            options: {{
                responsive: true,
                indexAxis: 'y',
                plugins: {{
                    legend: {{ display: false }},
                    tooltip: {{
                        callbacks: {{
                            label: function(ctx) {{
                                return '$' + ctx.raw.toFixed(2);
                            }}
                        }}
                    }}
                }},
                scales: {{
                    x: {{ beginAtZero: true, grid: {{ color: 'rgba(128,128,128,0.1)' }},
                        ticks: {{ callback: function(v) {{ return '$' + v; }} }} }}
                }}
            }}
        }});
        """
    else:
        charts_html += '</div>'

    return charts_html, chart_script


def _fetch_gmv_status():
    """Fetch Global Market Viability analysis status from cache + database."""
    GMV_CACHE_FILE = get_project_root() / "data" / "cache" / "ollama_market_viability_cache.json"
    GMV_TARGET_COUNTRIES_COUNT = 10  # 10 target markets

    stats = {
        "evaluations_done": 0,
        "total_expected": 0,
        "deep_dives_done": 0,
        "avg_viability": 0,
        "top_opportunity": "",
        "top_score": 0,
        "progress_pct": 0,
        "sectors_done": [],
        "country_scores": {},
        "status": "not_started",
        "last_evaluated": "",
        "deep_dive_go": 0,
        "deep_dive_cautious": 0,
        "deep_dive_nogo": 0,
    }

    # Read from database for stored results (primary source)
    try:
        conn = get_connection()
        schema.init_schema(conn)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT insights_json, analyzed_at, record_count "
            "FROM analysis_global_market_viability "
            "WHERE analysis_type = 'global_market_viability_full' "
            "ORDER BY id DESC LIMIT 1"
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if row:
            data = json.loads(row["insights_json"])
            sector_results = data.get("sector_results", [])
            deep_dives = data.get("deep_dive_results", [])

            stats["evaluations_done"] = len(sector_results)
            stats["deep_dives_done"] = len(deep_dives)
            num_sectors = len(set(r["sector"] for r in sector_results)) if sector_results else 42
            stats["total_expected"] = num_sectors * GMV_TARGET_COUNTRIES_COUNT
            stats["avg_viability"] = data.get("avg_viability_score", 0)
            stats["last_evaluated"] = row["analyzed_at"]
            stats["status"] = (
                "complete"
                if stats["evaluations_done"] >= stats["total_expected"] and stats["total_expected"] > 0
                else "in_progress"
            )

            top = data.get("top_combinations", [])
            if top:
                t = top[0]
                stats["top_opportunity"] = f"{t['sector']} in {t['country']}"
                stats["top_score"] = t["score"]

            # Country scores
            country_scores = {}
            for r in sector_results:
                cc = r.get("country_code", "")
                cn = r.get("country_name", cc)
                score = r.get("overall_viability_score", 0)
                if cc not in country_scores:
                    country_scores[cc] = {"name": cn, "scores": []}
                country_scores[cc]["scores"].append(score)

            for cc, v in country_scores.items():
                valid = [s for s in v["scores"] if s > 0]
                stats["country_scores"][cc] = {
                    "name": v["name"],
                    "avg": round(sum(valid) / len(valid), 1) if valid else 0,
                    "count": len(valid),
                }

            stats["sectors_done"] = list(set(r["sector"] for r in sector_results))

            go_count = sum(1 for d in deep_dives if str(d.get("go_no_go", "")).lower() == "go")
            cautious_count = sum(1 for d in deep_dives if str(d.get("go_no_go", "")).lower() == "cautious")
            nogo_count = sum(1 for d in deep_dives if str(d.get("go_no_go", "")).lower() == "no-go")
            stats["deep_dive_go"] = go_count
            stats["deep_dive_cautious"] = cautious_count
            stats["deep_dive_nogo"] = nogo_count

    except Exception as e:
        _logger.warning("DashboardAgent: Could not fetch GMV status from DB: %s", e)

    # If DB empty but cache has data, use cache count as fallback
    if stats["evaluations_done"] == 0:
        try:
            if GMV_CACHE_FILE.exists():
                cache_data = json.loads(GMV_CACHE_FILE.read_text(encoding="utf-8"))
                stats["evaluations_done"] = len(cache_data)
                stats["status"] = "in_progress"
                stats["total_expected"] = 420
                stats["progress_pct"] = min(99, round(len(cache_data) / 420 * 100, 1))
                return stats
        except Exception as e:
            _logger.warning("DashboardAgent: Could not read GMV cache: %s", e)

    if stats["total_expected"] > 0:
        stats["progress_pct"] = round(
            stats["evaluations_done"] / stats["total_expected"] * 100, 1
        )

    return stats


def _build_gmv_monitor_html(gmv_stats: dict) -> str:
    """Build HTML for the Global Market Viability monitoring section."""
    if not gmv_stats or gmv_stats.get("status") == "not_started":
        return ""

    status = gmv_stats["status"]
    pct = gmv_stats.get("progress_pct", 0)
    done = gmv_stats["evaluations_done"]
    total = gmv_stats.get("total_expected", 0)
    avg = gmv_stats.get("avg_viability", 0)
    top_opp = gmv_stats.get("top_opportunity", "N/A")
    top_score = gmv_stats.get("top_score", 0)
    deep_dives = gmv_stats.get("deep_dives_done", 0)
    sectors = len(gmv_stats.get("sectors_done", []))
    last_eval = gmv_stats.get("last_evaluated", "")

    # Status badge color
    if status == "complete":
        status_color = "#10B981"
        status_label = "COMPLETE"
    elif pct > 0:
        status_color = "#F59E0B"
        status_label = "IN PROGRESS"
    else:
        status_color = "#6c757d"
        status_label = "PENDING"

    # Progress bar color
    if pct >= 100:
        bar_color = "#10B981"
    elif pct >= 50:
        bar_color = "#3B82F6"
    else:
        bar_color = "#F59E0B"

    html = f"""
    <div class="stats-grid" style="margin-top: 24px; border-top: 2px solid var(--border); padding-top: 24px;">
      <div class="stat-card accent-blue">
        <span class="icon">&#127760;</span>
        <div class="value">{done}/{total}</div>
        <div class="label">Evaluations Done</div>
      </div>
      <div class="stat-card accent-green">
        <span class="icon">&#128200;</span>
        <div class="value">{avg}/10</div>
        <div class="label">Avg Viability Score</div>
      </div>
      <div class="stat-card accent-amber">
        <span class="icon">&#127919;</span>
        <div class="value">{top_score}/10</div>
        <div class="label">Top Opportunity</div>
        <div style="font-size:11px;color:var(--text-secondary);margin-top:4px;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{top_opp}</div>
      </div>
      <div class="stat-card accent-red">
        <span class="icon">&#128269;</span>
        <div class="value">{deep_dives}</div>
        <div class="label">Company Deep-Dives</div>
      </div>
    </div>
    <div style="margin-bottom: 24px;">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">
        <h2 id="gmv-monitoring" style="margin:0;font-size:14px;font-weight:600;">Global Market Viability Analysis</h2>
        <span style="display:inline-block;padding:2px 10px;border-radius:12px;font-size:11px;font-weight:600;background:{status_color};color:white;">{status_label}</span>
      </div>
      <div style="background:var(--border);border-radius:8px;height:12px;overflow:hidden;">
        <div style="height:100%;width:{pct}%;background:{bar_color};border-radius:8px;transition:width 0.5s;"></div>
      </div>
      <div style="display:flex;justify-content:space-between;font-size:12px;color:var(--text-secondary);margin-top:4px;">
        <span>{sectors} sectors analyzed</span>
        <span>{pct}%</span>
        {f'<span>Last: {last_eval[:16]}</span>' if last_eval else '<span></span>'}
      </div>
    </div>
    """
    return html


def _build_gmv_charts(gmv_stats: dict):
    """Build Global Market Viability monitoring charts."""
    charts_html = ""
    chart_script = ""

    if not gmv_stats or gmv_stats.get("evaluations_done", 0) == 0:
        return charts_html, chart_script

    # Chart 1: Viability by Country (bar chart)
    country_scores = gmv_stats.get("country_scores", {})
    if country_scores:
        charts_html += '<h2 id="gmv-charts" style="font-size:16px;font-weight:700;margin:0 0 12px 0;color:var(--text);">Market Viability Charts</h2>'
        charts_html += '<div class="charts-grid">'
        charts_html += '<div class="chart-container"><h3>Avg Viability Score by Market</h3><canvas id="gmvCountryChart"></canvas></div>'

        sorted_countries = sorted(country_scores.items(), key=lambda x: x[1]["avg"], reverse=True)
        labels = json.dumps([v["name"][:20] for _, v in sorted_countries])
        data = json.dumps([v["avg"] for _, v in sorted_countries])
        counts = json.dumps([v["count"] for _, v in sorted_countries])

        chart_script += f"""
        new Chart(document.getElementById('gmvCountryChart'), {{
            type: 'bar',
            data: {{
                labels: {labels},
                datasets: [{{
                    label: 'Avg Viability /10',
                    data: {data},
                    backgroundColor: function(ctx) {{
                        var v = ctx.raw;
                        if (v >= 7) return '#10B981';
                        if (v >= 5) return '#F59E0B';
                        return '#EF4444';
                    }},
                    borderRadius: 4,
                    maxBarThickness: 30
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ display: false }},
                    tooltip: {{
                        callbacks: {{
                            afterLabel: function(ctx) {{
                                var cnts = {counts};
                                return cnts[ctx.dataIndex] + ' evaluations';
                            }}
                        }}
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true, max: 10,
                        title: {{ display: true, text: 'Viability Score' }},
                        grid: {{ color: 'rgba(128,128,128,0.1)' }}
                    }}
                }}
            }}
        }});
        """

    # Chart 2: Deep-dive Go/No-Go (doughnut)
    if gmv_stats.get("deep_dives_done", 0) > 0:
        go = gmv_stats.get("deep_dive_go", 0)
        cautious = gmv_stats.get("deep_dive_cautious", 0)
        nogo = gmv_stats.get("deep_dive_nogo", 0)

        charts_html += '<div class="chart-container"><h3>Company Deep-Dive Results</h3><canvas id="gmvGoNoGo"></canvas></div>'
        charts_html += '</div>'

        chart_script += f"""
        new Chart(document.getElementById('gmvGoNoGo'), {{
            type: 'doughnut',
            data: {{
                labels: ['Go', 'Cautious', 'No-Go'],
                datasets: [{{ data: [{go}, {cautious}, {nogo}],
                    backgroundColor: ['#10B981', '#F59E0B', '#EF4444']
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ position: 'bottom', labels: {{ boxWidth: 12, padding: 16 }} }}
                }}
            }}
        }});
        """

    return charts_html, chart_script


def _build_charts():
    """Build Chart.js charts using data from the database."""
    charts_html = ""
    chart_script = ""

    try:
        conn = get_connection()
        schema.init_schema(conn)

        # Chart.js global defaults for better styling
        chart_script += """
        Chart.defaults.font.family = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
        Chart.defaults.color = getComputedStyle(document.documentElement).getPropertyValue('--text-secondary').trim();
        Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(0,0,0,0.85)';
        Chart.defaults.plugins.tooltip.padding = 12;
        Chart.defaults.plugins.tooltip.cornerRadius = 8;
        Chart.defaults.animation.duration = 800;
        Chart.defaults.animation.easing = 'easeOutQuart';
        """

        # Chart 1: Failure by category (doughnut)
        cursor = conn.cursor()
        cursor.execute(
            """SELECT COALESCE(failure_category, 'Unknown') as cat, COUNT(*) as cnt
               FROM failed_startups GROUP BY failure_category ORDER BY cnt DESC LIMIT 8"""
        )
        categories = cursor.fetchall()
        cursor.close()

        if categories:
            charts_html += '<div class="charts-grid">'
            charts_html += '<div class="chart-container"><h3>Failure by Category</h3><canvas id="categoryChart"></canvas></div>'

            cat_labels = json.dumps([r["cat"] for r in categories])
            cat_data = json.dumps([r["cnt"] for r in categories])
            chart_script += f"""
            new Chart(document.getElementById('categoryChart'), {{
                type: 'doughnut',
                data: {{
                    labels: {cat_labels},
                    datasets: [{{ data: {cat_data},
                        backgroundColor: ['#3B82F6','#EF4444','#10B981','#F59E0B','#8B5CF6','#F97316','#14B8A6','#EC4899']
                    }}]
                }},
                options: {{
                    responsive: true,
                    plugins: {{
                        legend: {{ position: 'bottom', labels: {{ boxWidth: 12, padding: 16 }} }},
                        tooltip: {{ backgroundColor: 'rgba(0,0,0,0.85)', padding: 12, cornerRadius: 8 }}
                    }}
                }}
            }});
            """

        # Chart 2: Failures by year (bar chart)
        cursor = conn.cursor()
        cursor.execute(
            """SELECT year_shutdown, COUNT(*) as cnt FROM failed_startups
               WHERE year_shutdown > 2015 GROUP BY year_shutdown ORDER BY year_shutdown"""
        )
        by_year = cursor.fetchall()
        cursor.close()

        if by_year:
            charts_html += '<div class="chart-container"><h3>Failures by Year</h3><canvas id="yearChart"></canvas></div>'
            charts_html += '</div>'

            year_labels = json.dumps([str(r["year_shutdown"]) for r in by_year])
            year_data = json.dumps([r["cnt"] for r in by_year])
            chart_script += f"""
            new Chart(document.getElementById('yearChart'), {{
                type: 'bar',
                data: {{
                    labels: {year_labels},
                    datasets: [{{ label: 'Startups Failed', data: {year_data},
                        backgroundColor: '#3B82F6', borderRadius: 4, maxBarThickness: 40
                    }}]
                }},
                options: {{
                    responsive: true,
                    plugins: {{
                        legend: {{ display: false }},
                        tooltip: {{ backgroundColor: 'rgba(0,0,0,0.85)', padding: 12, cornerRadius: 8 }}
                    }},
                    scales: {{ y: {{ beginAtZero: true, grid: {{ color: 'rgba(128,128,128,0.1)' }} }} }}
                }}
            }});
            """

        # Chart 3: BLS survival rates (line chart)
        cursor = conn.cursor()
        cursor.execute(
            """SELECT year, age_1_yr_survival, age_2_yr_survival, age_3_yr_survival, age_5_yr_survival
               FROM bls_survival_rates WHERE quarter IS NULL ORDER BY year"""
        )
        survival = cursor.fetchall()
        cursor.close()

        if survival:
            charts_html += '<div class="charts-grid">'
            charts_html += '<div class="chart-container"><h3>Manufacturing Survival Rates (BLS)</h3><canvas id="survivalChart"></canvas></div>'

            s_1yr = json.dumps([r["age_1_yr_survival"] for r in survival if r["age_1_yr_survival"]])
            s_5yr = json.dumps([r["age_5_yr_survival"] for r in survival if r["age_5_yr_survival"]])
            s_years_1 = json.dumps([str(r["year"]) for r in survival if r["age_1_yr_survival"]])

            chart_script += f"""
            new Chart(document.getElementById('survivalChart'), {{
                type: 'line',
                data: {{
                    labels: {s_years_1},
                    datasets: [
                        {{ label: '1-Year Survival %', data: {s_1yr}, borderColor: '#3B82F6',
                           backgroundColor: 'rgba(59,130,246,0.1)', fill: true, tension: 0.3, pointRadius: 3 }},
                        {{ label: '5-Year Survival %', data: {s_5yr}, borderColor: '#EF4444',
                           backgroundColor: 'rgba(239,68,68,0.1)', fill: true, tension: 0.3, pointRadius: 3 }}
                    ]
                }},
                options: {{
                    responsive: true,
                    plugins: {{
                        tooltip: {{ backgroundColor: 'rgba(0,0,0,0.85)', padding: 12, cornerRadius: 8 }}
                    }},
                    scales: {{
                        y: {{ beginAtZero: false, grid: {{ color: 'rgba(128,128,128,0.1)' }} }}
                    }}
                }}
            }});
            """

        # Chart 4: Regional breakdown
        cursor = conn.cursor()
        cursor.execute(
            """SELECT COALESCE(region, country, 'Unknown') as reg, COUNT(*) as cnt
               FROM failed_startups GROUP BY reg ORDER BY cnt DESC LIMIT 10"""
        )
        regions = cursor.fetchall()
        cursor.close()

        if regions:
            charts_html += '<div class="chart-container"><h3>Failures by Region</h3><canvas id="regionChart"></canvas></div>'
            charts_html += '</div>'

            reg_labels = json.dumps([r["reg"] for r in regions])
            reg_data = json.dumps([r["cnt"] for r in regions])
            chart_script += f"""
            new Chart(document.getElementById('regionChart'), {{
                type: 'bar',
                data: {{
                    labels: {reg_labels},
                    datasets: [{{ label: 'Startups', data: {reg_data},
                        backgroundColor: '#10B981', borderRadius: 4, maxBarThickness: 24
                    }}]
                }},
                options: {{
                    responsive: true,
                    indexAxis: 'y',
                    plugins: {{
                        legend: {{ display: false }},
                        tooltip: {{ backgroundColor: 'rgba(0,0,0,0.85)', padding: 12, cornerRadius: 8 }}
                    }},
                    scales: {{ x: {{ beginAtZero: true, grid: {{ color: 'rgba(128,128,128,0.1)' }} }} }}
                }}
            }});
            """

        conn.close()

    except Exception as e:
        _logger.warning("DashboardAgent: Could not build charts: %s", e)

    return charts_html, chart_script


# ── LLM Model Portfolio ──────────────────────────────────────────────────

def _fetch_portfolio_data() -> dict:
    """Fetch LLM portfolio recommendations from database."""
    data: dict = {
        "categories": {},
        "total_recommendations": 0,
        "estimated_savings_pct": 0,
        "last_recommended": "",
    }

    try:
        conn = get_connection()
        schema.init_schema(conn)
        cursor = conn.cursor()

        cursor.execute(
            """SELECT task_category, provider, model_name, allocation_pct, rank_position,
                      composite_score, quality_score, cost_score, speed_score, context_score,
                      cost_per_1m_tokens, recommended_at
               FROM llm_portfolio
               ORDER BY task_category, rank_position ASC"""
        )
        rows = [dict(r) for r in cursor.fetchall()]

        cursor.execute("SELECT MAX(recommended_at) as latest FROM llm_portfolio")
        latest = cursor.fetchone()
        cursor.close()
        conn.close()

        data["total_recommendations"] = len(rows)
        if latest and latest["latest"]:
            data["last_recommended"] = str(latest["latest"])

        # Group by task category
        for r in rows:
            cat = r["task_category"]
            if cat not in data["categories"]:
                data["categories"][cat] = []
            data["categories"][cat].append(r)

    except Exception as e:
        _logger.warning("DashboardAgent: Could not fetch portfolio data: %s", e)

    return data


def _build_portfolio_html(data: dict) -> str:
    """Build Model Portfolio recommendations section."""
    if not data or not data.get("categories"):
        return ""

    categories = data["categories"]
    total = data.get("total_recommendations", 0)
    last = data.get("last_recommended", "")[:16]

    # Build recommended stack table
    stack_rows = ""
    for cat_id, models in categories.items():
        if not models:
            continue
        primary = models[0]
        score = primary.get("composite_score", 0)
        cost = primary.get("cost_per_1m_tokens", 0)
        quality = primary.get("quality_score", 0)

        # Color coding by score
        if score >= 80:
            score_color = "#10B981"
        elif score >= 60:
            score_color = "#F59E0B"
        else:
            score_color = "#EF4444"

        stack_rows += f"""
        <tr>
          <td style="padding:8px 12px;border-bottom:1px solid var(--border);font-weight:500;">{cat_id.replace('_', ' ').title()}</td>
          <td style="padding:8px 12px;border-bottom:1px solid var(--border);">{primary['model_name']}</td>
          <td style="padding:8px 12px;border-bottom:1px solid var(--border);color:var(--text-secondary);">{primary['provider']}</td>
          <td style="padding:8px 12px;border-bottom:1px solid var(--border);color:{score_color};font-weight:600;text-align:right;">{score:.1f}</td>
          <td style="padding:8px 12px;border-bottom:1px solid var(--border);text-align:right;">
            {'Free' if cost == 0 else f'${cost:.2f}'}
          </td>
          <td style="padding:8px 12px;border-bottom:1px solid var(--border);text-align:right;">{quality:.1f}</td>
        </tr>"""

    # Count categories
    cat_count = len(categories)

    html = f"""
    <div style="margin-top: 32px; border-top: 2px solid var(--border); padding-top: 24px;">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;">
        <h2 id="llm-portfolio" style="margin:0;font-size:20px;font-weight:700;color:var(--text);">LLM Model Portfolio</h2>
        <span style="display:inline-block;padding:2px 10px;border-radius:12px;font-size:11px;font-weight:600;background:#8B5CF6;color:white;">
          {cat_count} TASK CATEGORIES
        </span>
      </div>

      <div class="stats-grid">
        <div class="stat-card accent-blue">
          <span class="icon">&#128200;</span>
          <div class="value">{total}</div>
          <div class="label">Portfolio Picks</div>
        </div>
        <div class="stat-card accent-green">
          <span class="icon">&#127919;</span>
          <div class="value">{cat_count}</div>
          <div class="label">Task Categories</div>
        </div>
        <div class="stat-card accent-amber">
          <span class="icon">&#128176;</span>
          <div class="value">70/20/10</div>
          <div class="label">Allocation Strategy</div>
        </div>
        <div class="stat-card accent-red">
          <span class="icon">&#128197;</span>
          <div class="value" style="font-size:14px;">{last}</div>
          <div class="label">Last Updated</div>
        </div>
      </div>

      <div style="margin-top:16px;background:var(--bg-secondary);border-radius:10px;border:1px solid var(--border);overflow:hidden;">
        <div style="padding:12px 16px;border-bottom:1px solid var(--border);font-weight:600;font-size:14px;color:var(--text);">
          Recommended Stack — Primary model per task category &middot; <span style="color:#10B981;">Score &ge; 80 = strong</span>
        </div>
        <div style="overflow-x:auto;">
          <table style="width:100%;border-collapse:collapse;font-size:13px;">
            <thead>
              <tr style="font-size:11px;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.5px;">
                <th style="padding:8px 12px;text-align:left;border-bottom:1px solid var(--border);">Task</th>
                <th style="padding:8px 12px;text-align:left;border-bottom:1px solid var(--border);">Recommended Model</th>
                <th style="padding:8px 12px;text-align:left;border-bottom:1px solid var(--border);">Provider</th>
                <th style="padding:8px 12px;text-align:right;border-bottom:1px solid var(--border);">Score</th>
                <th style="padding:8px 12px;text-align:right;border-bottom:1px solid var(--border);">Cost/1M</th>
                <th style="padding:8px 12px;text-align:right;border-bottom:1px solid var(--border);">Quality</th>
              </tr>
            </thead>
            <tbody>
              {stack_rows}
            </tbody>
          </table>
        </div>
      </div>

      <div style="margin-top:12px;padding:12px 16px;background:var(--accent-light);border-radius:8px;border:1px solid var(--border);font-size:13px;color:var(--text-secondary);">
        <strong style="color:var(--accent);">How it works:</strong>
        Each task category gets a 70/20/10 allocation (primary/secondary/tertiary model).
        Scores are weighted composites: quality, cost, speed, and context window.
        Weights vary per category (e.g., code gen prioritizes quality; summarization prioritizes cost).
      </div>
    </div>
    """
    return html


def _build_portfolio_charts(data: dict):
    """Build portfolio visualization charts."""
    charts_html = ""
    chart_script = ""

    if not data or not data.get("categories"):
        return charts_html, chart_script

    categories = data["categories"]

    charts_html += '<div class="charts-grid">'

    # Chart 1: Allocation pie chart (how many categories each provider wins)
    provider_wins = {}
    for cat_id, models in categories.items():
        if models:
            provider = models[0]["provider"]
            provider_wins[provider] = provider_wins.get(provider, 0) + 1

    if provider_wins:
        sorted_providers = sorted(provider_wins.items(), key=lambda x: x[1], reverse=True)
        p_labels = json.dumps([p for p, _ in sorted_providers])
        p_data = json.dumps([c for _, c in sorted_providers])
        colors = ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#F97316", "#14B8A6", "#EC4899", "#6366F1"]

        charts_html += '<div class="chart-container"><h3>Provider Market Share (Categories Won)</h3><canvas id="portfolioPieChart"></canvas></div>'

        chart_script += f"""
        new Chart(document.getElementById('portfolioPieChart'), {{
            type: 'doughnut',
            data: {{
                labels: {p_labels},
                datasets: [{{ data: {p_data},
                    backgroundColor: {json.dumps(colors[:len(sorted_providers)])}
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ position: 'bottom', labels: {{ boxWidth: 12, padding: 16 }} }}
                }}
            }}
        }});
        """

    # Chart 2: Composite score comparison across top task categories
    top_cats = list(categories.items())[:6]
    if top_cats:
        cat_labels = [cat.replace("_", " ").title() for cat, _ in top_cats]
        primary_scores = [m[0]["composite_score"] if m else 0 for _, m in top_cats]
        primary_quality = [m[0].get("quality_score", 0) if m else 0 for _, m in top_cats]

        charts_html += '<div class="chart-container"><h3>Score vs Quality by Task Category</h3><canvas id="portfolioScoreChart"></canvas></div>'
        charts_html += '</div>'

        chart_script += f"""
        new Chart(document.getElementById('portfolioScoreChart'), {{
            type: 'bar',
            data: {{
                labels: {json.dumps(cat_labels)},
                datasets: [
                    {{ label: 'Composite Score', data: {json.dumps(primary_scores)},
                      backgroundColor: '#3B82F6', borderRadius: 4, maxBarThickness: 30 }},
                    {{ label: 'Quality Score', data: {json.dumps(primary_quality)},
                      backgroundColor: '#10B981', borderRadius: 4, maxBarThickness: 30 }}
                ]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ position: 'bottom', labels: {{ boxWidth: 12, padding: 16 }} }}
                }},
                scales: {{
                    y: {{ beginAtZero: true, max: 100, grid: {{ color: 'rgba(128,128,128,0.1)' }} }}
                }}
            }}
        }});
        """

    return charts_html, chart_script


# ── LLM Benchmark Tracker ────────────────────────────────────────────────

def _fetch_benchmark_data() -> dict:
    """Fetch LLM benchmark data from database."""
    data: dict = {
        "models": [],
        "categories": {},
        "total_benchmarks": 0,
        "top_models": [],
    }

    try:
        conn = get_connection()
        schema.init_schema(conn)
        cursor = conn.cursor()

        cursor.execute(
            """SELECT provider, model_name, benchmark_name, benchmark_score,
                      benchmark_category, speed_tokens_per_sec
               FROM llm_benchmarks
               ORDER BY benchmark_score DESC"""
        )
        rows = [dict(r) for r in cursor.fetchall()]
        cursor.close()
        conn.close()

        data["total_benchmarks"] = len(rows)

        # Group by category
        for r in rows:
            cat = r.get("benchmark_category", "general")
            if cat not in data["categories"]:
                data["categories"][cat] = []
            data["categories"][cat].append(r)

        # Top models by average score
        model_scores = {}
        for r in rows:
            key = f"{r['provider']}:{r['model_name']}"
            if key not in model_scores:
                model_scores[key] = {"scores": [], "provider": r["provider"], "model_name": r["model_name"]}
            model_scores[key]["scores"].append(r["benchmark_score"])

        top = sorted(model_scores.items(), key=lambda x: sum(x[1]["scores"]) / len(x[1]["scores"]), reverse=True)[:10]
        data["top_models"] = [
            {"provider": v["provider"], "model_name": v["model_name"],
             "avg_score": round(sum(v["scores"]) / len(v["scores"]), 1),
             "benchmarks": len(v["scores"])}
            for _, v in top
        ]

    except Exception as e:
        _logger.warning("DashboardAgent: Could not fetch benchmark data: %s", e)

    return data


def _build_benchmark_html(data: dict) -> str:
    """Build Benchmark Tracker section."""
    if not data or data.get("total_benchmarks", 0) == 0:
        return ""

    top_models = data.get("top_models", [])
    categories = data.get("categories", {})
    total = data.get("total_benchmarks", 0)

    # Top models table
    model_rows = ""
    for m in top_models:
        score = m["avg_score"]
        if score >= 85:
            color = "#10B981"
        elif score >= 70:
            color = "#F59E0B"
        else:
            color = "#EF4444"

        model_rows += f"""
        <tr>
          <td style="padding:8px 12px;border-bottom:1px solid var(--border);font-weight:500;">{m['model_name']}</td>
          <td style="padding:8px 12px;border-bottom:1px solid var(--border);color:var(--text-secondary);">{m['provider']}</td>
          <td style="padding:8px 12px;border-bottom:1px solid var(--border);color:{color};font-weight:600;text-align:right;">{score}</td>
          <td style="padding:8px 12px;border-bottom:1px solid var(--border);text-align:right;">{m['benchmarks']}</td>
        </tr>"""

    # Category breakdown
    cat_badges = ""
    for cat, benchmarks in sorted(categories.items()):
        avg = sum(b["benchmark_score"] for b in benchmarks if b["benchmark_score"]) / max(len([b for b in benchmarks if b["benchmark_score"]]), 1)
        cat_badges += f"""
        <span style="display:inline-block;padding:4px 10px;margin:3px;border-radius:6px;font-size:12px;background:var(--bg);border:1px solid var(--border);">
          {cat.replace('_', ' ').title()} <strong>{len(benchmarks)}</strong> &middot; avg {avg:.1f}
        </span>"""

    html = f"""
    <div style="margin-top: 32px; border-top: 2px solid var(--border); padding-top: 24px;">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;">
        <h2 id="llm-benchmarks" style="margin:0;font-size:20px;font-weight:700;color:var(--text);">Benchmark Tracker</h2>
        <span style="display:inline-block;padding:2px 10px;border-radius:12px;font-size:11px;font-weight:600;background:#F59E0B;color:white;">
          {total} DATA POINTS
        </span>
      </div>

      <div class="stats-grid">
        <div class="stat-card accent-blue">
          <span class="icon">&#128200;</span>
          <div class="value">{len(top_models)}</div>
          <div class="label">Models Ranked</div>
        </div>
        <div class="stat-card accent-green">
          <span class="icon">&#128202;</span>
          <div class="value">{total}</div>
          <div class="label">Benchmark Scores</div>
        </div>
        <div class="stat-card accent-amber">
          <span class="icon">&#127942;</span>
          <div class="value">{top_models[0]['avg_score'] if top_models else 0}</div>
          <div class="label">Top Model Score</div>
          <div style="font-size:11px;color:var(--text-secondary);margin-top:4px;">{top_models[0]['model_name'] if top_models else 'N/A'}</div>
        </div>
        <div class="stat-card accent-red">
          <span class="icon">&#128293;</span>
          <div class="value">{len(categories)}</div>
          <div class="label">Benchmark Categories</div>
        </div>
      </div>

      <div style="margin-top:16px;background:var(--bg-secondary);border-radius:10px;border:1px solid var(--border);overflow:hidden;">
        <div style="padding:12px 16px;border-bottom:1px solid var(--border);font-weight:600;font-size:14px;color:var(--text);">
          Top Models by Average Benchmark Score (0-100 scale)
        </div>
        <div style="overflow-x:auto;">
          <table style="width:100%;border-collapse:collapse;font-size:13px;">
            <thead>
              <tr style="font-size:11px;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.5px;">
                <th style="padding:8px 12px;text-align:left;border-bottom:1px solid var(--border);">Model</th>
                <th style="padding:8px 12px;text-align:left;border-bottom:1px solid var(--border);">Provider</th>
                <th style="padding:8px 12px;text-align:right;border-bottom:1px solid var(--border);">Avg Score</th>
                <th style="padding:8px 12px;text-align:right;border-bottom:1px solid var(--border);">Benchmarks</th>
              </tr>
            </thead>
            <tbody>
              {model_rows}
            </tbody>
          </table>
        </div>
      </div>

      <div style="margin-top:12px;">
        <div style="font-size:13px;font-weight:600;color:var(--text);margin-bottom:8px;">Categories:</div>
        <div>{cat_badges}</div>
      </div>
    </div>
    """
    return html


def _build_benchmark_charts(data: dict):
    """Build benchmark visualization charts."""
    charts_html = ""
    chart_script = ""

    if not data or data.get("total_benchmarks", 0) == 0:
        return charts_html, chart_script

    top_models = data.get("top_models", [])[:8]
    categories = data.get("categories", {})

    charts_html += '<div class="charts-grid">'

    # Chart: Top model scores horizontal bar
    if top_models:
        labels = [f"{m['model_name']}" for m in reversed(top_models)]
        scores = [m["avg_score"] for m in reversed(top_models)]
        colors_list = []
        for s in scores:
            if s >= 85:
                colors_list.append("#10B981")
            elif s >= 70:
                colors_list.append("#F59E0B")
            else:
                colors_list.append("#EF4444")

        charts_html += '<div class="chart-container"><h3>Top Models — Average Benchmark Score</h3><canvas id="benchmarkBarChart"></canvas></div>'

        chart_script += f"""
        new Chart(document.getElementById('benchmarkBarChart'), {{
            type: 'bar',
            data: {{
                labels: {json.dumps(labels)},
                datasets: [{{
                    label: 'Avg Score',
                    data: {json.dumps(scores)},
                    backgroundColor: {json.dumps(colors_list)},
                    borderRadius: 4,
                    maxBarThickness: 24
                }}]
            }},
            options: {{
                responsive: true,
                indexAxis: 'y',
                plugins: {{
                    legend: {{ display: false }}
                }},
                scales: {{
                    x: {{ beginAtZero: true, max: 100, grid: {{ color: 'rgba(128,128,128,0.1)' }} }}
                }}
            }}
        }});
        """

    # Chart: Radar chart comparing providers across categories
    cat_names = sorted(categories.keys())
    if len(cat_names) >= 3 and top_models:
        # Get top provider scores per category
        provider_cats = {}
        for cat in cat_names:
            benchmarks = [b for b in categories[cat] if b["benchmark_score"]]
            if benchmarks:
                # Best score per category across all models
                best = max(benchmarks, key=lambda b: b["benchmark_score"])
                provider = best["provider"]
                if provider not in provider_cats:
                    provider_cats[provider] = {}
                provider_cats[provider][cat] = best["benchmark_score"]

        if len(provider_cats) >= 2:
            radar_labels = json.dumps([c.replace("_", " ").title() for c in cat_names])
            datasets = []
            radar_colors = ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6"]
            for i, (provider, cat_scores) in enumerate(provider_cats.items()):
                datasets.append({
                    "label": provider.title(),
                    "data": [cat_scores.get(c, 0) for c in cat_names],
                    "borderColor": radar_colors[i % len(radar_colors)],
                    "backgroundColor": radar_colors[i % len(radar_colors)].replace(")", ",0.1)").replace("rgb", "rgba"),
                    "pointRadius": 4,
                })

            charts_html += '<div class="chart-container"><h3>Provider Comparison Across Categories</h3><canvas id="benchmarkRadarChart"></canvas></div>'
            charts_html += '</div>'

            chart_script += f"""
            new Chart(document.getElementById('benchmarkRadarChart'), {{
                type: 'radar',
                data: {{
                    labels: {radar_labels},
                    datasets: {json.dumps(datasets)}
                }},
                options: {{
                    responsive: true,
                    plugins: {{
                        legend: {{ position: 'bottom', labels: {{ boxWidth: 12, padding: 16 }} }}
                    }},
                    scales: {{
                        r: {{ beginAtZero: true, max: 100, grid: {{ color: 'rgba(128,128,128,0.2)' }} }}
                    }}
                }}
            }});
            """
        else:
            charts_html += '</div>'

    return charts_html, chart_script


# ── LLM Cost Optimizer ───────────────────────────────────────────────────

def _fetch_optimizer_data() -> dict:
    """Fetch cost optimization alerts and price changes from database."""
    data: dict = {
        "alerts": [],
        "price_changes": [],
        "total_savings_pct": 0,
        "active_alerts": 0,
    }

    try:
        conn = get_connection()
        schema.init_schema(conn)
        cursor = conn.cursor()

        # Active alerts
        cursor.execute(
            """SELECT alert_type, title, description, affected_models,
                      estimated_savings_pct, priority, created_at
               FROM llm_optimization_alerts
               WHERE dismissed = 0
               ORDER BY
                 CASE priority WHEN 'critical' THEN 1 WHEN 'high' THEN 2
                      WHEN 'medium' THEN 3 ELSE 4 END,
                 created_at DESC
               LIMIT 20"""
        )
        alerts = [dict(r) for r in cursor.fetchall()]

        # Price changes
        cursor.execute(
            """SELECT provider, model_name, old_input_price, old_output_price,
                      new_input_price, new_output_price, input_change_pct,
                      output_change_pct, detected_at
               FROM llm_price_changes
               ORDER BY detected_at DESC
               LIMIT 15"""
        )
        changes = [dict(r) for r in cursor.fetchall()]

        # Total savings estimate
        cursor.execute(
            "SELECT AVG(estimated_savings_pct) as avg_savings "
            "FROM llm_optimization_alerts WHERE dismissed = 0 AND alert_type = 'better_alternative'"
        )
        savings_row = cursor.fetchone()
        cursor.close()
        conn.close()

        data["alerts"] = alerts
        data["price_changes"] = changes
        data["active_alerts"] = len(alerts)
        data["total_savings_pct"] = int(savings_row["avg_savings"]) if savings_row and savings_row["avg_savings"] else 0

    except Exception as e:
        _logger.warning("DashboardAgent: Could not fetch optimizer data: %s", e)

    return data


def _build_optimizer_html(data: dict) -> str:
    """Build Cost Optimizer section with alerts and savings."""
    alerts = data.get("alerts", [])
    changes = data.get("price_changes", [])
    savings = data.get("total_savings_pct", 0)
    active = data.get("active_alerts", 0)

    if not alerts and not changes:
        return ""

    # Priority colors
    priority_colors = {
        "critical": "#EF4444", "high": "#F97316", "medium": "#F59E0B", "low": "#10B981"
    }

    # Alert cards
    alert_cards = ""
    for alert in alerts[:10]:
        priority = alert.get("priority", "medium")
        p_color = priority_colors.get(priority, "#6c757d")
        alert_type = alert.get("alert_type", "")
        type_icons = {
            "price_drop": "&#128176;",
            "new_model": "&#128640;",
            "better_alternative": "&#128161;",
            "portfolio_rebalance": "&#128200;",
        }
        icon = type_icons.get(alert_type, "&#128276;")
        savings_pct = alert.get("estimated_savings_pct", 0)

        alert_cards += f"""
        <div style="padding:12px 16px;border-bottom:1px solid var(--border);display:flex;gap:12px;align-items:flex-start;">
          <span style="font-size:20px;flex-shrink:0;">{icon}</span>
          <div style="flex:1;min-width:0;">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
              <span style="font-size:13px;font-weight:600;color:var(--text);">{alert['title']}</span>
              <span style="display:inline-block;padding:1px 6px;border-radius:8px;font-size:10px;font-weight:600;background:{p_color};color:white;text-transform:uppercase;">{priority}</span>
            </div>
            <div style="font-size:12px;color:var(--text-secondary);line-height:1.5;">
              {alert.get('description', '')}
            </div>
            {"<div style=\"margin-top:4px;font-size:12px;font-weight:600;color:#10B981;\">~" + str(int(savings_pct)) + "% potential savings</div>" if savings_pct > 0 else ""}
          </div>
        </div>"""

    # Price changes table
    price_rows = ""
    for pc in changes[:8]:
        in_change = pc.get("input_change_pct", 0)
        out_change = pc.get("output_change_pct", 0)
        max_change = max(abs(in_change or 0), abs(out_change or 0))

        if max_change > 0:
            change_color = "#10B981"  # Price drop = good
            arrow = "&#8595;" if in_change < 0 or out_change < 0 else "&#8593;"
        else:
            change_color = "var(--text-secondary)"
            arrow = "&#8594;"

        price_rows += f"""
        <tr>
          <td style="padding:6px 12px;border-bottom:1px solid var(--border);font-size:12px;">{pc['model_name']}</td>
          <td style="padding:6px 12px;border-bottom:1px solid var(--border);font-size:12px;color:var(--text-secondary);">{pc['provider']}</td>
          <td style="padding:6px 12px;border-bottom:1px solid var(--border);font-size:12px;color:{change_color};font-weight:600;text-align:right;">
            {arrow} {in_change:+.1f}% / {out_change:+.1f}%
          </td>
        </tr>"""

    # Count by priority
    critical = sum(1 for a in alerts if a.get("priority") == "critical")
    high = sum(1 for a in alerts if a.get("priority") == "high")

    html = f"""
    <div style="margin-top: 32px; border-top: 2px solid var(--border); padding-top: 24px;">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;">
        <h2 id="llm-cost-optimizer" style="margin:0;font-size:20px;font-weight:700;color:var(--text);">Cost Optimizer</h2>
        <div style="display:flex;gap:6px;">
          {"<span style=\"padding:2px 10px;border-radius:12px;font-size:11px;font-weight:600;background:#EF4444;color:white;\">CRITICAL " + str(critical) + "</span>" if critical > 0 else ""}
          {"<span style=\"padding:2px 10px;border-radius:12px;font-size:11px;font-weight:600;background:#F97316;color:white;\">HIGH " + str(high) + "</span>" if high > 0 else ""}
          <span style="padding:2px 10px;border-radius:12px;font-size:11px;font-weight:600;background:#3B82F6;color:white;">
            {active} ALERTS
          </span>
        </div>
      </div>

      <div class="stats-grid">
        <div class="stat-card accent-green">
          <span class="icon">&#128176;</span>
          <div class="value">~{savings}%</div>
          <div class="label">Potential Savings</div>
        </div>
        <div class="stat-card accent-blue">
          <span class="icon">&#128276;</span>
          <div class="value">{active}</div>
          <div class="label">Active Alerts</div>
        </div>
        <div class="stat-card accent-amber">
          <span class="icon">&#128200;</span>
          <div class="value">{len(changes)}</div>
          <div class="label">Price Changes</div>
        </div>
        <div class="stat-card accent-red">
          <span class="icon">&#128161;</span>
          <div class="value">{sum(1 for a in alerts if a.get('alert_type') == 'better_alternative')}</div>
          <div class="label">Better Alternatives</div>
        </div>
      </div>

      {"<div style=\"margin-top:16px;background:var(--bg-secondary);border-radius:10px;border:1px solid var(--border);overflow:hidden;\"><div style=\"padding:12px 16px;border-bottom:1px solid var(--border);font-weight:600;font-size:14px;color:var(--text);\">Active Optimization Alerts</div>" + alert_cards + "</div>" if alert_cards else ""}

      {"<div style=\"margin-top:16px;background:var(--bg-secondary);border-radius:10px;border:1px solid var(--border);overflow:hidden;\"><div style=\"padding:12px 16px;border-bottom:1px solid var(--border);font-weight:600;font-size:14px;color:var(--text);\">Recent Price Changes</div><table style=\"width:100%;border-collapse:collapse;\"><thead><tr style=\"font-size:11px;color:var(--text-secondary);text-transform:uppercase;\"><th style=\"padding:8px 12px;text-align:left;border-bottom:1px solid var(--border);\">Model</th><th style=\"padding:8px 12px;text-align:left;border-bottom:1px solid var(--border);\">Provider</th><th style=\"padding:8px 12px;text-align:right;border-bottom:1px solid var(--border);\">Change</th></tr></thead><tbody>" + price_rows + "</tbody></table></div>" if price_rows else ""}
    </div>
    """
    return html


def _wrap_gated(tier: str, html: str) -> str:
    """Wrap an HTML section in a gated-content div for tier-based access."""
    if not html:
        return ""
    return f'<div class="gated-content" data-tier="{tier}">\n{html}\n</div>\n'


def _build_pro_lock_overlay(section_id: str) -> str:
    """Build a Pro lock overlay placeholder for a gated section."""
    return f"""
    <div class="gated-content" data-tier="pro" id="{section_id}">
      <div class="pro-lock-overlay">
        <span class="lock-icon">&#128274;</span>
        <h3>Opportunity Deep Dives</h3>
        <p>AI-powered sector analysis, scored opportunities, and competitive landscape — available with Pro.</p>
        <button class="upgrade-btn" onclick="showTierAction()">Upgrade to Pro</button>
      </div>
    </div>
    """


def _build_pricing_html() -> str:
    """Build the pricing/landing page section with Free, Pro, and Enterprise tiers."""
    from agents.license_agent import TIER_FEATURES, TIER_PRICING

    free_features = TIER_FEATURES.get("free", [])
    pro_features = TIER_FEATURES.get("pro", [])
    ent_features = TIER_FEATURES.get("enterprise", [])
    free_price = TIER_PRICING.get("free", {})
    pro_price = TIER_PRICING.get("pro", {})
    ent_price = TIER_PRICING.get("enterprise", {})

    def _feature_list(features):
        items = ""
        for f in features:
            label = f.replace("_", " ").title()
            items += f'<li>{label}</li>\n'
        return items

    html = f"""
    <div id="pricing" style="margin-top:48px;padding-top:32px;border-top:2px solid var(--border);">
      <h2 style="text-align:center;font-size:24px;margin-bottom:8px;">Choose Your Plan</h2>
      <p style="text-align:center;color:var(--text-secondary);font-size:14px;margin-bottom:32px;">
        From failed startups to found opportunities. Unlock the full platform.
      </p>

      <div class="pricing-grid">
        <!-- Free -->
        <div class="pricing-card">
          <div class="tier-name">{free_price.get('label', 'Free')}</div>
          <div class="price">${{0}}<small>/{free_price.get('period', 'forever')}</small></div>
          <ul class="features">{_feature_list(free_features)}</ul>
          <a class="cta-btn current" href="javascript:void(0)">Current</a>
        </div>

        <!-- Pro (featured) -->
        <div class="pricing-card featured">
          <div class="tier-name">{pro_price.get('label', 'Pro')}</div>
          <div class="price">${{49}}<small>/{pro_price.get('period', 'month')}</small></div>
          <ul class="features">{_feature_list(pro_features)}</ul>
          <a class="cta-btn primary" href="javascript:void(0)" onclick="showTierAction()">Get Pro</a>
        </div>

        <!-- Enterprise -->
        <div class="pricing-card">
          <div class="tier-name">{ent_price.get('label', 'Enterprise')}</div>
          <div class="price">${{1,000}}<small>/{ent_price.get('period', 'month')}</small></div>
          <ul class="features">{_feature_list(ent_features)}</ul>
          <a class="cta-btn secondary" href="mailto:contact@oplatform.dev?subject=Enterprise%20Inquiry">Contact Us</a>
        </div>
      </div>
    </div>
    """
    return html


def _fetch_knowledge_graph_data() -> dict:
    """Fetch knowledge graph statistics from the database."""
    kg_data: dict = {
        "total_entities": 0,
        "total_relationships": 0,
        "entity_types": [],
        "top_entities": [],
        "relationship_types": [],
        "status": "no_data",
    }
    try:
        conn = get_connection()
        schema.init_schema(conn)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) as cnt FROM kg_entities")
        kg_data["total_entities"] = cursor.fetchone()["cnt"]

        cursor.execute("SELECT COUNT(*) as cnt FROM kg_relationships")
        kg_data["total_relationships"] = cursor.fetchone()["cnt"]

        cursor.execute(
            """SELECT et.type_name, et.icon, COUNT(e.id) as entity_count
               FROM kg_entity_types et
               LEFT JOIN kg_entities e ON et.id = e.entity_type_id
               GROUP BY et.id, et.type_name, et.icon
               ORDER BY entity_count DESC"""
        )
        kg_data["entity_types"] = [dict(r) for r in cursor.fetchall()]

        cursor.execute(
            """SELECT e.name, et.type_name, e.mention_count,
                      (SELECT COUNT(*) FROM kg_relationships r
                       WHERE r.source_entity_id = e.id OR r.target_entity_id = e.id) as connections
               FROM kg_entities e
               JOIN kg_entity_types et ON e.entity_type_id = et.id
               ORDER BY connections DESC
               LIMIT 15"""
        )
        kg_data["top_entities"] = [dict(r) for r in cursor.fetchall()]

        cursor.execute(
            """SELECT relationship_type, COUNT(*) as count, AVG(weight) as avg_weight
               FROM kg_relationships
               GROUP BY relationship_type
               ORDER BY count DESC"""
        )
        kg_data["relationship_types"] = [dict(r) for r in cursor.fetchall()]

        cursor.close()
        conn.close()
        kg_data["status"] = "active" if kg_data["total_entities"] > 0 else "no_data"
    except Exception as e:
        _logger.debug("Could not fetch knowledge graph data: %s", e)

    return kg_data


def _build_knowledge_graph_html(kg_data: dict) -> str:
    """Build HTML for the Knowledge Graph section."""
    if not kg_data or kg_data.get("status") == "no_data":
        return ""

    total_e = kg_data["total_entities"]
    total_r = kg_data["total_relationships"]

    html = f"""
    <h2 id="knowledge-graph" style="font-size:18px;font-weight:700;margin:32px 0 16px 0;">
      Knowledge Graph
    </h2>

    <div class="stats-grid">
      <div class="stat-card accent-blue">
        <span class="icon">&#128268;</span>
        <div class="value">{total_e:,}</div>
        <div class="label">Entities</div>
      </div>
      <div class="stat-card accent-green">
        <span class="icon">&#128279;</span>
        <div class="value">{total_r:,}</div>
        <div class="label">Relationships</div>
      </div>
    </div>
    """

    entity_types = kg_data.get("entity_types", [])
    if entity_types:
        html += '<h3 style="font-size:14px;font-weight:600;margin:16px 0 8px 0;">Entity Types</h3>'
        html += '<table style="width:100%;border-collapse:collapse;margin-bottom:24px;">'
        html += '<thead><tr style="font-size:11px;color:var(--text-secondary);text-transform:uppercase;"><th style="padding:8px 12px;text-align:left;border-bottom:1px solid var(--border);">Type</th><th style="padding:8px 12px;text-align:right;border-bottom:1px solid var(--border);">Count</th></tr></thead><tbody>'
        for et in entity_types:
            icon = et.get("icon", "")
            html += f'<tr><td style="padding:6px 12px;border-bottom:1px solid var(--border);font-size:13px;">{icon} {et["type_name"]}</td><td style="padding:6px 12px;border-bottom:1px solid var(--border);font-size:13px;text-align:right;">{et["entity_count"]}</td></tr>'
        html += '</tbody></table>'

    top_entities = kg_data.get("top_entities", [])
    if top_entities:
        html += '<h3 style="font-size:14px;font-weight:600;margin:16px 0 8px 0;">Most Connected Entities</h3>'
        html += '<table style="width:100%;border-collapse:collapse;margin-bottom:24px;">'
        html += '<thead><tr style="font-size:11px;color:var(--text-secondary);text-transform:uppercase;"><th style="padding:8px 12px;text-align:left;border-bottom:1px solid var(--border);">Entity</th><th style="padding:8px 12px;text-align:left;border-bottom:1px solid var(--border);">Type</th><th style="padding:8px 12px;text-align:right;border-bottom:1px solid var(--border);">Links</th><th style="padding:8px 12px;text-align:right;border-bottom:1px solid var(--border);">Mentions</th></tr></thead><tbody>'
        for ent in top_entities[:10]:
            html += f'<tr><td style="padding:6px 12px;border-bottom:1px solid var(--border);font-size:13px;">{ent["name"]}</td><td style="padding:6px 12px;border-bottom:1px solid var(--border);font-size:12px;color:var(--text-secondary);">{ent["type_name"]}</td><td style="padding:6px 12px;border-bottom:1px solid var(--border);font-size:13px;text-align:right;">{ent["connections"]}</td><td style="padding:6px 12px;border-bottom:1px solid var(--border);font-size:13px;text-align:right;">{ent["mention_count"]}</td></tr>'
        html += '</tbody></table>'

    rel_types = kg_data.get("relationship_types", [])
    if rel_types:
        html += '<h3 style="font-size:14px;font-weight:600;margin:16px 0 8px 0;">Relationship Types</h3>'
        html += '<table style="width:100%;border-collapse:collapse;margin-bottom:24px;">'
        html += '<thead><tr style="font-size:11px;color:var(--text-secondary);text-transform:uppercase;"><th style="padding:8px 12px;text-align:left;border-bottom:1px solid var(--border);">Type</th><th style="padding:8px 12px;text-align:right;border-bottom:1px solid var(--border);">Count</th><th style="padding:8px 12px;text-align:right;border-bottom:1px solid var(--border);">Avg Weight</th></tr></thead><tbody>'
        for rt in rel_types:
            avg_w = rt.get("avg_weight", 0) or 0
            html += f'<tr><td style="padding:6px 12px;border-bottom:1px solid var(--border);font-size:13px;">{rt["relationship_type"]}</td><td style="padding:6px 12px;border-bottom:1px solid var(--border);font-size:13px;text-align:right;">{rt["count"]}</td><td style="padding:6px 12px;border-bottom:1px solid var(--border);font-size:13px;text-align:right;">{avg_w:.1f}</td></tr>'
        html += '</tbody></table>'

    return html


def _build_knowledge_graph_charts(kg_data: dict):
    """Build Knowledge Graph visualization charts. Returns (charts_html, chart_script)."""
    charts_html = ""
    chart_script = ""

    if not kg_data or kg_data.get("total_entities", 0) == 0:
        return charts_html, chart_script

    entity_types = kg_data.get("entity_types", [])
    if entity_types:
        labels = json.dumps([et["type_name"] for et in entity_types])
        data = json.dumps([et["entity_count"] for et in entity_types])
        charts_html += '<div class="charts-grid">'
        charts_html += '<div class="chart-container"><h3>Entity Type Distribution</h3><canvas id="kgEntityChart"></canvas></div></div>'
        chart_script += f"""
        new Chart(document.getElementById('kgEntityChart'), {{
            type: 'doughnut',
            data: {{
                labels: {labels},
                datasets: [{{
                    data: {data},
                    backgroundColor: ['#3B82F6','#10B981','#F59E0B','#EF4444','#8B5CF6','#EC4899','#06B6D4','#84CC16'],
                    borderWidth: 1
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{ legend: {{ position: 'right' }} }}
            }}
        }});"""

    top_entities = kg_data.get("top_entities", [])[:10]
    if top_entities:
        labels = json.dumps([e["name"][:20] for e in top_entities])
        data = json.dumps([e["connections"] for e in top_entities])
        charts_html += '<div class="charts-grid">'
        charts_html += '<div class="chart-container"><h3>Top Connected Entities</h3><canvas id="kgConnectionChart"></canvas></div></div>'
        chart_script += f"""
        new Chart(document.getElementById('kgConnectionChart'), {{
            type: 'bar',
            data: {{
                labels: {labels},
                datasets: [{{
                    label: 'Connections',
                    data: {data},
                    backgroundColor: '#3B82F6',
                    borderRadius: 4
                }}]
            }},
            options: {{
                responsive: true,
                indexAxis: 'y',
                plugins: {{ legend: {{ display: false }} }}
            }}
        }});"""

    return charts_html, chart_script


# ── Revenue Dashboard ──

def _fetch_revenue_data():
    """Fetch revenue data from payment_events and subscription_metrics."""
    data = {"payments": [], "metrics": [], "tier_distribution": {"free": 0, "pro": 0, "enterprise": 0}, "total_revenue": 0.0}
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """SELECT stripe_session_id, customer_email, tier, amount_usd, status, created_at
               FROM payment_events ORDER BY created_at DESC LIMIT 30"""
        )
        data["payments"] = [dict(r) for r in cursor.fetchall()]

        cursor.execute(
            "SELECT metric_date, free_users, pro_users, enterprise_users, revenue_usd "
            "FROM subscription_metrics ORDER BY metric_date DESC LIMIT 30"
        )
        data["metrics"] = [dict(r) for r in cursor.fetchall()]

        cursor.execute(
            "SELECT tier, COUNT(*) as cnt FROM user_licenses WHERE status = 'active' GROUP BY tier"
        )
        for row in cursor.fetchall():
            data["tier_distribution"][row["tier"]] = row["cnt"]

        cursor.execute("SELECT COALESCE(SUM(amount_usd), 0) FROM payment_events WHERE status = 'completed'")
        data["total_revenue"] = float(cursor.fetchone()[0])

        cursor.close()
        conn.close()
    except Exception as e:
        _logger.debug("Revenue data fetch error: %s", e)
    return data


def _build_revenue_html(rev_data):
    """Build the revenue dashboard section (Pro-gated)."""
    if not rev_data:
        return ""
    td = rev_data["tier_distribution"]
    total_licenses = sum(td.values())
    active_payments = [p for p in rev_data["payments"] if p["status"] == "completed"]

    html = (
        '<div id="revenue-monitoring" class="dashboard-section">\n'
        '  <h2 class="section-title" style="display:flex;align-items:center;gap:8px;">'
        '<span class="tier-badge pro-badge">PRO</span> Revenue Monitoring</h2>\n'
        '  <div class="stats-grid">\n'
        f'    <div class="stat-card"><div class="stat-value">${rev_data["total_revenue"]:,.2f}</div>'
        '<div class="stat-label">Total Revenue</div></div>\n'
        f'    <div class="stat-card"><div class="stat-value">{total_licenses:,}</div>'
        '<div class="stat-label">Active Licenses</div></div>\n'
        f'    <div class="stat-card"><div class="stat-value">{td["pro"]}</div>'
        '<div class="stat-label">Pro Users</div></div>\n'
        f'    <div class="stat-card"><div class="stat-value">{td["enterprise"]}</div>'
        '<div class="stat-label">Enterprise Users</div></div>\n'
        '  </div>\n'
        '  <h3>Tier Distribution</h3>\n'
        '  <table class="data-table">\n'
        '    <thead><tr><th>Tier</th><th>Users</th><th>Share</th></tr></thead>\n'
        '    <tbody>\n'
    )
    for tier in ["free", "pro", "enterprise"]:
        pct = (td[tier] / total_licenses * 100) if total_licenses > 0 else 0
        html += f'      <tr><td>{tier.title()}</td><td>{td[tier]}</td><td>{pct:.1f}%</td></tr>\n'
    html += (
        '    </tbody>\n'
        '  </table>\n'
    )
    if active_payments:
        html += (
            '  <h3>Recent Payments</h3>\n'
            '  <table class="data-table">\n'
            '    <thead><tr><th>Date</th><th>Email</th><th>Tier</th><th>Amount</th><th>Status</th></tr></thead>\n'
            '    <tbody>\n'
        )
        for p in active_payments[:10]:
            email = (p["customer_email"] or "N/A")[:30]
            html += (
                f'      <tr><td>{p["created_at"][:10]}</td><td>{email}</td>'
                f'<td>{p["tier"]}</td><td>${p["amount_usd"]:.2f}</td><td>{p["status"]}</td></tr>\n'
            )
        html += '    </tbody>\n  </table>\n'
    html += '</div>\n'
    return html


def _build_revenue_charts(rev_data):
    """Build revenue chart scripts (Pro-gated)."""
    charts_html = '<div class="chart-container" style="position:relative;height:300px;">'
    charts_html += '<canvas id="revenueChart"></canvas></div>'
    chart_script = ""

    metrics = list(reversed(rev_data["metrics"][-30:]))
    if metrics:
        labels = [m["metric_date"].strftime("%m/%d") if hasattr(m["metric_date"], "strftime")
                  else str(m["metric_date"])[-5:] for m in metrics]
        revenue_data = [float(m.get("revenue_usd", 0) or 0) for m in metrics]

        chart_script += f"""
        new Chart(document.getElementById('revenueChart'), {{
            type: 'line',
            data: {{
                labels: {labels},
                datasets: [{{
                    label: 'Revenue ($)',
                    data: {revenue_data},
                    borderColor: '#10B981',
                    backgroundColor: 'rgba(16,185,129,0.1)',
                    fill: true,
                    tension: 0.3
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{ legend: {{ display: false }} }},
                scales: {{ y: {{ beginAtZero: true }} }}
            }}
        }});"""

    return charts_html, chart_script


# ── Pipeline Health (Span) ──

def _fetch_span_data():
    """Fetch pipeline health data from span_snapshots."""
    data = {"agents": [], "anomalies": [], "recent_snapshots": []}
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Latest snapshot per agent
        cursor.execute(
            """SELECT s.agent_name, s.duration_seconds, s.records_affected, s.status,
                      s.anomaly_detected, s.anomaly_type, s.snapshot_at,
                      (SELECT COUNT(*) FROM span_snapshots s2
                       WHERE s2.agent_name = s.agent_name) as total_runs,
                      (SELECT AVG(s2.duration_seconds) FROM span_snapshots s2
                       WHERE s2.agent_name = s.agent_name) as avg_duration
               FROM span_snapshots s
               INNER JOIN (
                   SELECT agent_name, MAX(snapshot_at) as max_at
                   FROM span_snapshots GROUP BY agent_name
               ) latest ON s.agent_name = latest.agent_name AND s.snapshot_at = latest.max_at
               ORDER BY s.agent_name"""
        )
        data["agents"] = [dict(r) for r in cursor.fetchall()]

        # Recent anomalies
        cursor.execute(
            """SELECT agent_name, anomaly_type, anomaly_detail, snapshot_at
               FROM span_snapshots
               WHERE anomaly_detected = 1
               ORDER BY snapshot_at DESC LIMIT 20"""
        )
        data["anomalies"] = [dict(r) for r in cursor.fetchall()]

        cursor.close()
        conn.close()
    except Exception as e:
        _logger.debug("Span data fetch error: %s", e)
    return data


def _build_span_html(span_data):
    """Build the pipeline health monitoring section."""
    if not span_data["agents"]:
        return ""

    html = (
        '<div id="pipeline-health" class="dashboard-section">\n'
        '  <h2 class="section-title">Pipeline Health</h2>\n'
        '  <div class="stats-grid">\n'
    )

    total = len(span_data["agents"])
    healthy = sum(1 for a in span_data["agents"] if a["anomaly_detected"] == 0)
    anomalous = total - healthy

    html += (
        f'    <div class="stat-card"><div class="stat-value">{total}</div>'
        '<div class="stat-label">Agents Tracked</div></div>\n'
        f'    <div class="stat-card"><div class="stat-value" style="color:#10B981">{healthy}</div>'
        '<div class="stat-label">Healthy</div></div>\n'
        f'    <div class="stat-card"><div class="stat-value" style="color:{"#EF4444" if anomalous > 0 else "#10B981"}">{anomalous}</div>'
        '<div class="stat-label">Anomalies</div></div>\n'
        '  </div>\n'
        '  <h3>Agent Health</h3>\n'
        '  <table class="data-table">\n'
        '    <thead><tr><th>Agent</th><th>Last Duration</th><th>Avg Duration</th>'
        '<th>Records</th><th>Status</th><th>Health</th></tr></thead>\n'
        '    <tbody>\n'
    )

    for a in span_data["agents"]:
        health_badge = "OK" if a["anomaly_detected"] == 0 else "WARN"
        health_color = "#10B981" if a["anomaly_detected"] == 0 else "#F59E0B"
        dur = a["duration_seconds"] or 0
        avg = a["avg_duration"] or 0
        html += (
            f'      <tr><td>{a["agent_name"]}</td>'
            f'<td>{dur:.1f}s</td><td>{avg:.1f}s</td>'
            f'<td>{a["records_affected"] or 0}</td>'
            f'<td>{a["status"]}</td>'
            f'<td style="color:{health_color};font-weight:600">{health_badge}</td></tr>\n'
        )

    html += '    </tbody>\n  </table>\n'

    if span_data["anomalies"]:
        html += (
            '  <h3>Recent Anomalies</h3>\n'
            '  <table class="data-table">\n'
            '    <thead><tr><th>Agent</th><th>Type</th><th>Detail</th><th>When</th></tr></thead>\n'
            '    <tbody>\n'
        )
        for an in span_data["anomalies"][:10]:
            detail = (an.get("anomaly_detail") or "")[:80]
            when = str(an.get("snapshot_at", ""))[:16]
            html += (
                f'      <tr><td>{an["agent_name"]}</td>'
                f'<td>{an["anomaly_type"]}</td>'
                f'<td>{detail}</td><td>{when}</td></tr>\n'
            )
        html += '    </tbody>\n  </table>\n'

    html += '</div>\n'
    return html

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

        # Build navigation from headings
        nav_html = _generate_nav(html_body)

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

        # Assemble final HTML
        full_html = HTML_TEMPLATE.format(
            title="Startup Research Report — Live Dashboard",
            generated=datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M UTC"),
            nav=nav_html,
            stats=stats_html + gmv_monitor_html,
            charts=charts_html + gmv_charts_html,
            body=html_body + llm_infra_html,
            chart_script=chart_script + gmv_chart_script,
        )

        # Write output files
        site_dir.mkdir(parents=True, exist_ok=True)
        (site_dir / "index.html").write_text(full_html, encoding="utf-8")
        (site_dir / "data.json").write_text(
            json.dumps({**stats_json, "gmv_monitoring": gmv_stats, "llm_infrastructure": llm_status}, indent=2, default=str),
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
        r'<(h[23])\s+id="([^"]*)">(.*?)</\1>', html_body
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
            return json.loads(resp.read().decode())
    except Exception:
        return None


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
        <h2 style="margin:0;font-size:20px;font-weight:700;color:var(--text);">LLM Infrastructure</h2>
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
        <span style="font-size:14px;font-weight:600;">Global Market Viability Analysis</span>
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

"""Dashboard agent — converts markdown report to an interactive HTML site."""

import json
import logging
import re
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
@media (prefers-color-scheme: dark) {{
  :root {{
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
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.6;
}}
/* Header */
.header {{
  position: fixed; top: 0; left: 0; right: 0; height: var(--header-height);
  background: var(--bg-secondary); border-bottom: 1px solid var(--border);
  display: flex; align-items: center; padding: 0 24px; z-index: 100;
  backdrop-filter: blur(10px);
}}
.header h1 {{ font-size: 18px; font-weight: 600; }}
.header .meta {{ margin-left: auto; font-size: 13px; color: var(--text-secondary); }}
/* Sidebar */
.sidebar {{
  position: fixed; top: var(--header-height); left: 0;
  width: var(--sidebar-width); height: calc(100vh - var(--header-height));
  background: var(--bg-secondary); border-right: 1px solid var(--border);
  overflow-y: auto; padding: 16px 0;
}}
.sidebar a {{
  display: block; padding: 8px 20px; color: var(--text-secondary);
  text-decoration: none; font-size: 13px; border-left: 3px solid transparent;
  transition: all 0.15s;
}}
.sidebar a:hover {{ color: var(--accent); background: var(--accent-light); }}
.sidebar a.h2 {{ padding-left: 32px; font-weight: 600; color: var(--text); }}
.sidebar a.h3 {{ padding-left: 48px; }}
/* Main */
.main {{
  margin-left: var(--sidebar-width); margin-top: var(--header-height);
  padding: 32px 40px; max-width: 960px;
}}
/* Stats cards */
.stats-grid {{
  display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px; margin-bottom: 32px;
}}
.stat-card {{
  background: var(--bg-secondary); border: 1px solid var(--border);
  border-radius: 8px; padding: 20px; text-align: center;
}}
.stat-card .value {{ font-size: 32px; font-weight: 700; color: var(--accent); }}
.stat-card .label {{ font-size: 12px; color: var(--text-secondary); margin-top: 4px; text-transform: uppercase; letter-spacing: 0.5px; }}
/* Charts */
.chart-container {{
  background: var(--bg-secondary); border: 1px solid var(--border);
  border-radius: 8px; padding: 20px; margin-bottom: 24px;
}}
.chart-container h3 {{ margin-bottom: 12px; font-size: 16px; }}
.charts-grid {{
  display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 32px;
}}
@media (max-width: 900px) {{ .charts-grid {{ grid-template-columns: 1fr; }} }}
/* Content */
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
/* Print */
@media print {{
  .sidebar, .header {{ display: none; }}
  .main {{ margin: 0; padding: 0; }}
}}
/* Mobile */
@media (max-width: 768px) {{
  .sidebar {{ display: none; }}
  .main {{ margin-left: 0; padding: 20px; }}
}}
</style>
</head>
<body>
<div class="header">
  <h1>{title}</h1>
  <span class="meta">Last updated: {generated}</span>
</div>
<nav class="sidebar">
{nav}
</nav>
<div class="main">
{stats}
{charts}
{body}
</div>
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

        # Assemble final HTML
        full_html = HTML_TEMPLATE.format(
            title="Startup Research Report — Live Dashboard",
            generated=datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M UTC"),
            nav=nav_html,
            stats=stats_html,
            charts=charts_html,
            body=html_body,
            chart_script=chart_script,
        )

        # Write output files
        site_dir.mkdir(parents=True, exist_ok=True)
        (site_dir / "index.html").write_text(full_html, encoding="utf-8")
        (site_dir / "data.json").write_text(
            json.dumps(stats_json, indent=2, default=str),
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
    for match in re.finditer(r"<(h[23])>(.*?)</\1>", html_body):
        tag, text = match.group(1), match.group(2)
        # Clean HTML from heading text
        clean = re.sub(r"<[^>]+>", "", text)
        anchor = re.sub(r"[^a-z0-9]+", "-", clean.lower()).strip("-")
        css_class = "h2" if tag == "h2" else "h3"
        nav_items.append(f'<a href="#{anchor}" class="{css_class}">{clean}</a>')

    # Add anchors to the html body for navigation
    # (This modifies the headings in the body to include id attributes)
    return "\n".join(nav_items[:50])  # Limit nav items


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
        ("total_startups", "Total Startups Tracked", stats_json.get("total_startups", 0)),
        ("mfg_startups", "Manufacturing Failures", stats_json.get("manufacturing_startups", 0)),
        ("total_articles", "News Articles", stats_json.get("total_articles", 0)),
        ("mfg_articles", "Mfg-Related News", stats_json.get("manufacturing_articles", 0)),
    ]
    stats_html = '<div class="stats-grid">\n'
    for _, label, value in cards:
        stats_html += f'<div class="stat-card"><div class="value">{value}</div><div class="label">{label}</div></div>\n'
    stats_html += "</div>"

    return stats_html, stats_json


def _build_charts():
    """Build Chart.js charts using data from the database."""
    charts_html = ""
    chart_script = ""

    try:
        conn = get_connection()
        schema.init_schema(conn)

        # Chart 1: Failure by category (pie chart)
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
                        backgroundColor: ['#0d6efd','#dc3545','#198754','#ffc107','#6f42c1','#fd7e14','#20c997','#e83e8c']
                    }}]
                }},
                options: {{ responsive: true, plugins: {{ legend: {{ position: 'bottom', labels: {{ boxWidth: 12 }} }} }} }}
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
                        backgroundColor: '#0d6efd', borderRadius: 4
                    }}]
                }},
                options: {{ responsive: true, scales: {{ y: {{ beginAtZero: true }} }} }}
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

            s_labels = json.dumps([str(r["year"]) for r in survival])
            s_1yr = json.dumps([r["age_1_yr_survival"] for r in survival if r["age_1_yr_survival"]])
            s_2yr = json.dumps([r["age_2_yr_survival"] for r in survival if r["age_2_yr_survival"]])
            s_5yr = json.dumps([r["age_5_yr_survival"] for r in survival if r["age_5_yr_survival"]])
            # Use years that have corresponding data
            s_years_1 = json.dumps([str(r["year"]) for r in survival if r["age_1_yr_survival"]])
            s_years_5 = json.dumps([str(r["year"]) for r in survival if r["age_5_yr_survival"]])

            chart_script += f"""
            new Chart(document.getElementById('survivalChart'), {{
                type: 'line',
                data: {{
                    labels: {s_years_1},
                    datasets: [
                        {{ label: '1-Year Survival %', data: {s_1yr}, borderColor: '#0d6efd', tension: 0.3 }},
                        {{ label: '5-Year Survival %', data: {s_5yr}, borderColor: '#dc3545', tension: 0.3 }}
                    ]
                }},
                options: {{ responsive: true, scales: {{ y: {{ beginAtZero: false }} }} }}
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
                        backgroundColor: '#198754', borderRadius: 4
                    }}]
                }},
                options: {{ responsive: true, indexAxis: 'y', scales: {{ x: {{ beginAtZero: true }} }} }}
            }});
            """

        conn.close()

    except Exception as e:
        _logger.warning("DashboardAgent: Could not build charts: %s", e)

    return charts_html, chart_script

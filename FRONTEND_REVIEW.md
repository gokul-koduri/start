# Frontend Review: Startup Research Report

**URL:** https://gokul-koduri.github.io/start/
**Date:** June 2, 2026
**Reviewer:** Automated Analysis (Claude Code)
**Status:** 11 issues fixed, 16 issues remaining (see individual sections)

---

## Summary of Fixes Applied

| Fix | Status |
|-----|--------|
| CRITICAL-1: Northvolt duplicate removed | Fixed |
| CRITICAL-2: Part 3 Cross-Reference populated with specific opportunities | Fixed |
| CRITICAL-3: Broken HTML entities in news section removed | Fixed |
| HIGH-1: 15 "Software & Hardware" sectors corrected | Fixed |
| HIGH-3: Northvolt duplicate in Part 3 table removed | Fixed |
| MED-1: Table overflow on mobile (CSS overflow-x added) | Fixed |
| MED-6: Focus styles for keyboard navigation added | Fixed |
| LOW-8: Sticky table header z-index added | Fixed |
| Dashboard stats updated (163→162, 44→43) | Fixed |
| Row numbering corrected after duplicate removal | Fixed |
| News title empty brackets cleaned | Fixed |

---

## Executive Summary

| Metric | Value |
|--------|-------|
| **Overall Rating** | 8.5 / 10 |
| **Total Startups Tracked** | 163 |
| **Manufacturing Failures** | 44 |
| **News Articles** | 599 (723 per dashboard stats) |
| **Tech Stack** | Vanilla HTML/CSS/JS, Chart.js v4, FastAPI, MySQL |
| **Design Quality** | Professional, polished dashboard |
| **Data Quality** | Moderate — duplicates and placeholders found |
| **Deployment** | GitHub Pages (widget JS files missing) |

The site presents as a professional research dashboard with excellent visual design, dark/light theming, responsive layout, and interactive charts. However, several data integrity issues, placeholder content, and deployment gaps need attention.

---

## Critical Issues (3)

### CRITICAL-1: Northvolt Duplicated in Manufacturing-Specific Failures Table

- **Location:** Manufacturing-Specific Startup Failures (2024-2025) table, rows 5 & 6
- **File:** `site/index.html` lines 724-739
- **Detail:** Northvolt appears twice with nearly identical data:
  - Row 5: `$14B+` | 2024 | "Production delays, cost overruns, cancelled orders"
  - Row 6: `$14B+` | 2024 | "Production delays, cost overruns, cancelled BMW/VW"
- **Impact:** Inflates failure count by 1; appears unprofessional
- **Fix:** Remove row 6, merge description into row 5

### CRITICAL-2: Part 3 Cross-Reference Table — 100% Placeholder Content

- **Location:** Part 3: Where Failed Startup Ideas Meet Manufacturing Revival
- **File:** `site/index.html` lines 1517-1611
- **Detail:** All 19 rows in the "Opportunity" column contain identical text: `"Learn from failures, apply to revival opportunities"`. The "Manufacturing Revival Match" column is also identical for every row: `"Closed specialty manufacturing facilities"`.
- **Impact:** Entire section provides zero actionable value
- **Fix:** Populate each row with specific opportunities matched to the failed category

### CRITICAL-3: Broken HTML Entities in News Section

- **Location:** "Recent Manufacturing Startup Failures (News)" section
- **File:** `site/index.html` lines 1659-1718
- **Detail:** Each news article has TWO link lines — one with encoded HTML entities (`&lt;a href=&rdquo;...`) and one with properly formatted HTML (`<a href="...">`). The encoded line renders as raw text, creating visible code snippets on the page.
- **Example:**
  ```
  — &lt;a href=&rdquo;https://news.google.com/rss/articles/CBMi...
  - <a href="https://news.google.com/rss/articles/CBMi...">Read more</a>
  ```
- **Impact:** Garbled text visible to all users; duplicate "Read more" links
- **Fix:** Remove the encoded entity line from each news entry

---

## High Priority Issues (4)

### HIGH-1: "Software & Hardware" Used as Catch-All Sector for 16 Entries

- **Location:** Manufacturing-Specific Failures table, rows 23-42 (years 2014-2020)
- **File:** `site/index.html` lines 868-1019
- **Detail:** 16 older startup entries use "Software & Hardware" as sector, which is not a meaningful manufacturing category:
  - Anki ($182M) — should be "Consumer Electronics / Robotics"
  - RethinkDB ($12.2M) — should be "Database Technology"
  - Parse ($7M) — should be "Cloud Platform / Mobile Backend"
  - DotCloud ($13.7M) — should be "Cloud Infrastructure"
  - Fuhu ($66.2M) — should be "Consumer Electronics"
  - FoundationDB ($22.7M) — should be "Database Technology"
  - QBotix ($23.5M) — should be "Solar Robotics"
  - ChaCha ($96M) — should be "Search / AI"
  - HubHaus ($13.4M) — should be "Real Estate / Co-living"
  - MatterFab ($13.2M) — should be "Metal Additive Manufacturing"
  - Seven Dreamers Laboratories ($95M) — should be "Home Appliances"
  - Aria Insights ($39M) — should be "Drone / AI Analytics"
  - Zirtual ($5.5M) — should be "Virtual Assistant Services"
  - Wattage ($200K) — should be "Consumer Electronics"
  - Lumos (No Data) — should be "Smart Lighting"
- **Impact:** Reduces data credibility; appears as lazy/default categorization
- **Fix:** Assign correct sectors for each company

### HIGH-2: Widget JS Files Missing from GitHub Pages (404 Errors)

- **Location:** `chat-widget.js`, `risk-widget.js`, `knowledge-graph-widget.js`
- **Detail:** Files exist locally in `site/` but return 404 on the deployed site
- **Root Cause:** Likely the `gh-pages` branch was deployed from a state that didn't include these files, or the branch contains a full project snapshot instead of just `site/` contents
- **Impact:** Chat widget and risk dashboard features non-functional on live site
- **Fix:** Redeploy to GitHub Pages; ensure `publish_dir: ./site` picks up all files

### HIGH-3: Northvolt Duplicated in Part 3 Cross-Reference

- **Location:** Part 3 table, Battery Cell Manufacturing row
- **File:** `site/index.html` line 1533
- **Detail:** Shows `(Northvolt, Northvolt)` — duplicate caused by CRITICAL-1 propagating through data pipeline
- **Fix:** Remove duplicate reference after fixing CRITICAL-1

### HIGH-4: Vague Funding Amounts for Multiple Entries

- **Location:** Throughout Manufacturing-Specific Failures table
- **Entries affected:**
  - Lumos (2015): "No Data"
  - SchoolGennie (2014): "N/A"
  - Mindstrong (2024): "Significant VC backing"
  - Tessera (2024): "Well-funded"
  - Black Buffalo 3D (2025): "Significant funding"
  - Dextrous Robotics (2024): "Well-funded"
- **Impact:** Inconsistent data quality reduces trustworthiness
- **Fix:** Research and standardize funding amounts

---

## Medium Issues (10)

### MED-1: Table Overflow on Mobile

- Tables with 6 columns will overflow on mobile screens (< 768px)
- No `overflow-x: auto` wrapper on table elements
- **Fix:** Wrap each `<table>` in a `<div class="table-wrapper">` with `overflow-x: auto`

### MED-2: News Startup Name Extraction Showing Gibberish

- **Location:** "Identified Startup Names in News" table, lines 1730+
- **Detail:** The "Startup" column contains partial text snippets instead of actual company names:
  - "debt after my startup"
  - "Analyses on Why they"
  - "Startup Where You Worked"
  - "Trucks As EV Startup"
- **Impact:** Named entity extraction pipeline is not working correctly
- **Fix:** Improve NER logic in the news processing pipeline

### MED-3: Empty Date Columns in News Table

- **Location:** "Identified Startup Names in News" table
- **Detail:** The "Date" column is empty for all 15+ entries
- **Fix:** Populate dates from RSS feed metadata

### MED-4: Inconsistent Failure Reason Detail Level

- Some entries have detailed reasons ("Production delays, cost overruns, cancelled orders")
- Others have vague one-word reasons: "Bad Timing", "Multiple Reasons", "Lack of Experience", "Bad Business Model"
- **Fix:** Standardize detail level or research and expand vague entries

### MED-5: Missing Accessibility — ARIA Labels

- Hamburger button and theme toggle have aria-labels (good)
- Search clear button missing aria-label
- Sidebar links missing `aria-current` for active section
- **Fix:** Add appropriate ARIA attributes

### MED-6: No Focus Styles for Keyboard Navigation

- **Detail:** Interactive elements (links, buttons) have no visible `:focus` outline
- **Fix:** Add `:focus-visible { outline: 2px solid var(--accent); }` to CSS

### MED-7: Color-Only Status Indicators

- Status badges (ONLINE, COMPLETE, etc.) use only color to convey status
- Color-blind users cannot distinguish states
- **Fix:** Add icons or text labels alongside color indicators

### MED-8: Dark Mode Contrast Ratios

- `--text-secondary: #a0a0a0` on `--bg: #1a1a2e` may not meet WCAG AA (4.5:1 ratio)
- `--border: #2a2a4a` may be too subtle
- **Fix:** Test with contrast checker and adjust values

### MED-9: Search Box Layout Shift on Focus

- Search input expands from 180px to 260px on focus, causing adjacent elements to shift
- **Fix:** Use absolute positioning or reserve fixed width

### MED-10: Stat Grid May Overflow on Small Phones

- `minmax(180px, 1fr)` may still be too wide for screens under 360px
- **Fix:** Change to `minmax(140px, 1fr)` or stack single column below 360px

---

## Low Issues (10)

### LOW-1: "Cautious" Typo in Chart Label
- Chart "gmvGoNoGo" uses "Cautious" instead of "Cautious"
- **File:** `site/index.html` line 2407

### LOW-2: License Text Truncation in LLM Section
- Llama 3 license text overflows table cell without proper truncation
- **Fix:** Truncate with ellipsis or show in modal

### LOW-3: Missing Reading Progress Indicator
- No visual progress bar to show reading position in the long report
- **Fix:** Add sticky progress bar below header

### LOW-4: Missing Breadcrumb Navigation
- No breadcrumbs for deep content navigation
- **Fix:** Add breadcrumb trail showing current section path

### LOW-5: Inconsistent Table of Contents Naming
- "1A-Extra" vs "1A" and "1B" — inconsistent hierarchy naming
- **Fix:** Standardize naming convention

### LOW-6: Print Styles Could Be Improved
- Basic print styles; sidebar and header should be hidden on print
- **Fix:** Add `@media print` rules

### LOW-7: No Error Handling in Chart Rendering
- Charts render without try-catch; if Chart.js fails to load, silent failure
- **Fix:** Add error boundaries or fallback content

### LOW-8: Sticky Table Header Missing z-index
- `position: sticky; top: 0` without `z-index` may cause overlapping
- **Fix:** Add `z-index: 10`

### LOW-9: No Loading States for Charts
- Charts appear instantly on desktop but may show empty canvases on slow connections
- **Fix:** Add loading skeletons or spinners

### LOW-10: Monolithic HTML File
- Single 105KB HTML file contains all CSS, HTML, and JS
- **Fix:** Consider splitting into separate files for maintainability

---

## Deployment Analysis

### Current Pipeline
```
Push to main → GitHub Actions → peaceiris/actions-gh-pages@v4 → gh-pages branch → GitHub Pages
```

### Issues Found
| Issue | Severity |
|-------|----------|
| Widget JS files return 404 on live site | High |
| `gh-pages` branch may contain full source tree | Medium |
| No frontend build/bundling step | Low |
| No asset versioning or cache headers | Low |

### Deployment Files
- **Workflow:** `.github/workflows/deploy.yml` — properly configured with `publish_dir: ./site`
- **Site files in `site/`:** `index.html`, `data.json`, `chat-widget.js`, `risk-widget.js`, `knowledge-graph-widget.js`, `.nojekyll`
- **All files present locally** — deployment issue is likely stale gh-pages branch state

---

## Codebase Health

### Test Coverage
| Area | Files | Tests | Status |
|------|-------|-------|--------|
| Collectors | 6 | 1 | Needs improvement |
| Risk Scorer | 1 | 1 | Adequate |
| Text Processing | 1 | 1 | Adequate |
| Deduplication | 1 | 1 | Adequate |
| API Server | 1 | 0 | No tests |
| Integration | — | 0 | Missing |
| Frontend JS | 3 | 0 | No tests |

### Recommendations
1. Add API endpoint tests (FastAPI TestClient)
2. Add integration tests for data pipeline
3. Add frontend JS unit tests
4. Implement data validation layer before database insertion

---

## Summary

| Category | Count |
|----------|-------|
| Critical | 3 |
| High | 4 |
| Medium | 10 |
| Low | 10 |
| **Total** | **27** |

### Top 5 Fixes (Priority Order)
1. Remove duplicate Northvolt entry from Manufacturing-Specific Failures table
2. Populate Part 3 Cross-Reference table with specific, actionable opportunities
3. Clean up broken HTML entities in news section (remove encoded entity lines)
4. Assign proper sector classifications to 16 "Software & Hardware" entries
5. Redeploy to GitHub Pages to include missing widget JS files

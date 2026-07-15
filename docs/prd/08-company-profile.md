# Company Profile — Opportunity Intelligence Platform

> Detailed company profile page with tabs for Overview, Timeline, Funding, Founders, Investors, News, AI Analysis, and Knowledge Graph.

---

## Table of Contents

1. [Profile Overview](#profile-overview)
2. [Header Section](#header-section)
3. [Tab Navigation](#tab-navigation)
4. [Tab Content](#tab-content)
5. [Async Loading](#async-loading)
6. [Actions](#actions)
7. [Sharing & Export](#sharing--export)
8. [API Data Mapping](#api-data-mapping)

---

## Profile Overview

### Purpose

The company profile provides comprehensive information about a single startup, including:
- Basic company information and metrics
- Funding history and investors
- Team and founders
- News and developments
- Real-time signals
- AI-generated analysis

### Route

`/company/[id]`

Where `[id]` is the company's UUID or slug.

### Entry Points

| Source | Action |
|--------|--------|
| Search results | Click company card |
| Watchlist | Click company name |
| Dashboard signals | Click signal company link |
| AI Analysis | Navigate from report |

---

## Header Section

### Company Header

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  [🔙 Back]                                                                │
│                                                                             │
│  ┌───────┐                                                                 │
│  │ Logo  │  Company Name                          [♡] [📤] [⋯]            │
│  │ 128px │                                                                 │
│  └───────┘  Description text that explains what the company does.         │
│             This can span two lines max, truncated with ellipsis.          │
│                                                                             │
│  ┌────────┐  ┌──────────┐  ┌────────┐  ┌────────┐  ┌─────────────┐      │
│  │ ⚡ 82  │  │ Series A │  │ $12M   │  │ SF, CA │  │ AI/ML       │      │
│  │  Score │  │ Stage    │  │ Raised │  │ Loc.   │  │ Sector      │      │
│  └────────┘  └──────────┘  └────────┘  └────────┘  └─────────────┘      │
│                                                                             │
│  Founded: 2021  •  45 employees  •  [View Website ↗]                       │
│                                                                             │
│  ─────────────────────────────────────────────────────────────────────────  │
│  [Overview] [Timeline] [Funding] [Founders] [Investors] [News] [AI] [Graph]│
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Header Metrics

| Metric | Value | Source |
|--------|-------|--------|
| Opportunity Score | 0-100 (color-coded) | AI calculated |
| Funding Stage | Pre-seed, Seed, A, B, C+, etc. | Database |
| Last Funding | Amount + date | Crunchbase equivalent |
| Location | City, Country | Database |
| Sector | Primary sector | Database |
| Founded | Year | Database |
| Employees | Count or range | Database |

### Opportunity Score Badge

| Score Range | Color | Display |
|-------------|-------|---------|
| 80-100 | Green | "High Potential" |
| 60-79 | Blue | "Strong" |
| 40-59 | Yellow | "Moderate" |
| 0-39 | Red | "Low" |

---

## Tab Navigation

### Tab Bar

```
┌────────────────────────────────────────────────────────────────────┐
│ [Overview] [Timeline] [Funding] [Founders] [Investors] [News] [AI][Graph]│
└────────────────────────────────────────────────────────────────────┘
```

### Tab Specifications

| Tab | Route State | Default | Lazy Load |
|-----|-------------|---------|-----------|
| Overview | `/company/[id]` | Yes | No |
| Timeline | `/company/[id]?tab=timeline` | No | Yes |
| Funding | `/company/[id]?tab=funding` | No | Yes |
| Founders | `/company/[id]?tab=founders` | No | Yes |
| Investors | `/company/[id]?tab=investors` | No | Yes |
| News | `/company/[id]?tab=news` | No | Yes |
| AI Analysis | `/company/[id]?tab=ai` | No | Yes |
| Graph | `/company/[id]?tab=graph` | No | Yes |

### Tab Behaviors
- Click: Switch tab immediately
- URL sync: Tab state reflected in URL
- Browser back: Return to previous tab
- Scroll: Sticky header with tabs when scrolling past

---

## Tab Content

### 1. Overview Tab (Default)

**Sections:**

```
┌─────────────────────────────────────────────────────────────────────┐
│  OVERVIEW                                                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ Key Metrics                                      [⚡ 82]         │ │
│  │                                                                  │ │
│  │  Market     │  Team     │  Traction  │  Competition          │ │
│  │  Size        │  Quality  │  Growth    │  Defensibility        │ │
│  │  High ●●●●○  │  Strong   │  +40% MoM  │  Moderate             │ │
│  │              │           │            │                       │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ About                                                                  │ │
│  │                                                                          │ │
│  │ Long-form company description. Can include markdown formatting...        │ │
│  │                                                                          │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌───────────────────────┐  ┌───────────────────────────────────────┐ │
│  │ Recent Activity       │  │ Key People                           │ │
│  │                       │  │                                       │ │
│  │ • Series A announced  │  │ 👤 Jane Smith (CEO)                  │ │
│  │ • 3 new hires         │  │ 👤 John Doe (CTO)                   │ │
│  │ • Product launch     │  │                                       │ │
│  └───────────────────────┘  └───────────────────────────────────────┘ │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ Contact Information                                              │ │
│  │                                                                    │ │
│  │ 🌐 https://company.com    📧 contact@company.com                  │ │
│  │ 📍 123 Main St, SF, CA    📱 +1 (555) 123-4567                    │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### 2. Timeline Tab

**Timeline Format:**

```
┌─────────────────────────────────────────────────────────────────────┐
│  TIMELINE                                           Filter: [All ▼] │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ●───────────────────────────────────────────────────────────────  │
│  │                                                                      │
│  │  Jan 2024        Series A Funding                                   │
│  │                   $12M raised from Sequoia, a16z                    │
│  │                   [Read More]                                       │
│                                                                     │
│  │  Nov 2023        Product Launch                                     │
│  │                   Launched AI-powered analytics platform            │
│  │                   [View Product]                                   │
│                                                                     │
│  │  Jul 2022        Seed Round                                          │
│  │                   $2M from Y Combinator                             │
│  │                   [Read More]                                       │
│                                                                     │
│  │  Mar 2021        Company Founded                                     │
│  │                   Founded by Jane Smith and John Doe               │
│  │                                                                     │
│  ●───────────────────────────────────────────────────────────────  │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

**Event Types:**
| Type | Icon | Color |
|------|------|-------|
| Funding | 💰 | Green |
| Leadership | 👤 | Blue |
| Product | 🚀 | Purple |
| Milestone | 🏆 | Gold |
| News | 📰 | Gray |
| Partnership | 🤝 | Teal |

### 3. Funding Tab

**Funding Table:**

```
┌─────────────────────────────────────────────────────────────────────┐
│  FUNDING HISTORY                                                     │
├─────────────────────────────────────────────────────────────────────┐
│                                                                       │
│  Total Raised: $14M       │  Last Round: Series A       │  Investors │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ Round    │ Amount   │ Date      │ Lead Investor │ Valuation  │  │
│  ├────────────────────────────────────────────────────────────────┤  │
│  │ Series A │ $12M     │ Jan 2024  │ Sequoia       │ $60M       │  │
│  │ Seed      │ $2M       │ Jul 2022  │ Y Combinator  │ -          │  │
│  │ Pre-seed  │ $500K    │ Mar 2021  │ Angels        │ -          │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  Funding Visualization (Chart)                                   │  │
│  │                                                                  │  │
│  │  $$ │                                    ●─── Series A          │  │
│  │     │                    ●───────────────                       │  │
│  │  $  │     ●─────────────                                         │  │
│  │     │ ●────                                                     │  │
│  │     └──────────────────────────────────────►                   │  │
│  │        Pre-seed    Seed      Series A                           │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### 4. Founders Tab

**Founder Cards:**

```
┌─────────────────────────────────────────────────────────────────────┐
│  FOUNDERS (2)                                                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌────────────────────────────────┐  ┌────────────────────────────┐ │
│  │ [Photo]                        │  │ [Photo]                     │ │
│  │                                │  │                             │ │
│  │ Jane Smith                    │  │ John Doe                    │ │
│  │ CEO & Co-founder              │  │ CTO & Co-founder            │ │
│  │                                │  │                             │ │
│  │ Stanford CS '15               │  │ MIT CS '14                  │ │
│  │ Ex-Google (5 years)           │  │ Ex-Meta (4 years)          │ │
│  │ Previous: ABC Startup (CEO)   │  │ Previous: XYZ Corp (Eng)    │ │
│  │                                │  │                             │ │
│  │ [LinkedIn] [Twitter]          │  │ [LinkedIn] [Twitter]        │ │
│  │                                │  │                             │ │
│  │ Companies: NovaTech (curr)   │  │ Companies: NovaTech (curr)  │ │
│  │           ABC Inc (2018-21)   │  │         XYZ Corp (2016-20)   │ │
│  └────────────────────────────────┘  └────────────────────────────┘ │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### 5. Investors Tab

**Investor Section:**

```
┌─────────────────────────────────────────────────────────────────────┐
│  INVESTORS (4)                                                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Lead Investors                                                       │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ 🏢 Sequoia Capital                                              │ │
│  │    Stage: Seed, Series A/B                                      │ │
│  │    Portfolio: 234 companies                                    │ │
│  │    [View Profile]                                              │ │
│  └───────────────────────────────────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ 🏢 Andreessen Horowitz                                          │ │
│  │    Stage: Series A+                                             │ │
│  │    Portfolio: 189 companies                                     │ │
│  │    [View Profile]                                              │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  Other Investors: AngelList, Founder Collective, First Round        │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### 6. News Tab

**News Feed:**

```
┌─────────────────────────────────────────────────────────────────────┐
│  NEWS & ARTICLES                                    Filter: [All ▼] │
├─────────────────────────────────────────────────────────────────────┐
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐     │
│  │ 📰 NovaTech Raises $12M Series A                            │     │
│  │     TechCrunch • Jan 15, 2024          [External ↗]          │     │
│  │                                                              │     │
│  │     AI analytics startup NovaTech has closed a $12M...      │     │
│  │     [Read More]                                             │     │
│  └─────────────────────────────────────────────────────────────┘     │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐     │
│  │ 📰 NovaTech Launches Enterprise Platform                     │     │
│  │     VentureBeat • Nov 10, 2023           [External ↗]        │     │
│  │                                                              │     │
│  │     NovaTech today announced the launch of its...           │     │
│  │     [Read More]                                             │     │
│  └─────────────────────────────────────────────────────────────┘     │
│                                                                       │
│  [Load More]                                                         │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### 7. AI Analysis Tab

**See [09-ai-analysis.md](./09-ai-analysis.md) for full specification.**

**Quick Reference:**
- Request new analysis
- View existing analysis
- Scores breakdown
- Recommendations
- Risk factors

### 8. Graph Tab

**Knowledge Graph Visualization:**

```
┌─────────────────────────────────────────────────────────────────────┐
│  KNOWLEDGE GRAPH                            [Zoom] [Center] [Export] │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│                      ┌─────────────────┐                             │
│                      │   NovaTech      │  ← Center node             │
│                      │   (Company)     │                             │
│                      └────────┬────────┘                             │
│                               │                                       │
│        ┌──────────────────────┼──────────────────────┐              │
│        │                      │                      │              │
│        ▼                      ▼                      ▼              │
│  ┌──────────┐          ┌───────────┐          ┌──────────┐          │
│  │ Jane     │          │ Sequoia   │          │ AI/ML    │          │
│  │ Smith    │          │ Capital   │          │ Sector   │          │
│  └──────────┘          └───────────┘          └──────────┘          │
│        │                      │                      │              │
│        │                      │                      │              │
│        ▼                      ▼                      ▼              │
│  ┌──────────┐          ┌────────────┐          ┌──────────┐          │
│  │ Stanford │          │ Y Combinator│          │ SaaS     │          │
│  │          │          │            │          │          │          │
│  └──────────┘          └────────────┘          └──────────┘          │
│                                                                       │
│  Legend: [●] Company [◯] Person [■] Investor [◆] Other               │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

**Features:**
- Interactive pan/zoom
- Click node to expand
- Hover for details tooltip
- Filter by relationship type
- Export as image

---

## Async Loading

### Loading Strategy

| Tab | Load Behavior |
|-----|--------------|
| Overview | Pre-loaded with page |
| Timeline | Lazy load on tab click |
| Funding | Lazy load on tab click |
| Founders | Lazy load on tab click |
| Investors | Lazy load on tab click |
| News | Lazy load on tab click |
| AI | Lazy load on tab click |
| Graph | Lazy load on tab click |

### Loading States

**Skeleton:**
```
┌─────────────────────────────────────────────────────────────────────┐
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ ████████████████████████████                                   │ │
│  │ ████████████  █████████████  ██████  ██████████████             │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌─────────────────────────┐  ┌────────────────────────────────────┐ │
│  │ ████████████████████    │  │ ██████████████████████████████   │ │
│  │ ████████████            │  │ ████████████████████████████    │ │
│  │ ███████████████         │  │ ████████████████████            │ │
│  └─────────────────────────┘  └────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

**Tab Loading:**
```
┌─────────────────────────────────────────────────────────────────────┐
│  [Loading...] [Loading...] [Loading ●] [Loading...] [Loading...]   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Actions

### Action Buttons

| Action | Icon | Behavior |
|--------|------|----------|
| Watchlist | ♡/♥ | Toggle with optimistic update |
| Share | 📤 | Open share modal |
| More | ⋯ | Dropdown menu |

### Watchlist Behavior

```
Click ♡ → Immediate toggle → Toast: "Added to Watchlist"
                     ↓
         Optimistic UI update
                     ↓
         Background API call
                     ↓
         Success: No action needed
         Error: Revert + error toast
```

### Share Modal

```
┌────────────────────────────────────────┐
│  Share Company                          │
├────────────────────────────────────────┤
│                                        │
│  Link: https://app.example.com/        │
│        company/abc123       [📋 Copy] │
│                                        │
│  Email: [__________] [Send]            │
│                                        │
│  ────────────────────────────────────  │
│                                        │
│  [💼 LinkedIn] [🐦 Twitter] [📎 Copy]  │
│                                        │
│                              [Close]   │
└────────────────────────────────────────┘
```

### More Menu

| Option | Action |
|--------|--------|
| Export Data | Download company data JSON/CSV |
| Report Issue | Submit data correction |
| View Original | Go to source website |
| Set Alert | Configure company alerts |

---

## Sharing & Export

### URL Structure

```
/company/nova-tech-ai-12345
```

### Meta Tags (SEO)

```html
<title>NovaTech AI - Opportunity Intelligence Platform</title>
<meta name="description" content="NovaTech AI: AI-powered customer analytics. Series A, $12M raised. Score: 82.">
<meta property="og:title" content="NovaTech AI - Series A - AI/ML - San Francisco">
<meta property="og:description" content="View detailed analysis, funding history, and AI-powered insights.">
```

---

## API Data Mapping

### Key Endpoints

| Data | Endpoint | Method |
|------|----------|--------|
| Company Details | `/api/v2/companies/[id]` | GET |
| Timeline | `/api/v2/companies/[id]/timeline` | GET |
| Funding | `/api/v2/companies/[id]/funding` | GET |
| Founders | `/api/v2/companies/[id]/founders` | GET |
| Investors | `/api/v2/companies/[id]/investors` | GET |
| News | `/api/v2/companies/[id]/news` | GET |
| Analysis | `/api/v2/companies/[id]/analyses/latest` | GET |
| Graph | `/api/v2/companies/[id]/graph` | GET |

### Response Example: Company Details

```json
{
  "data": {
    "id": "uuid",
    "name": "NovaTech AI",
    "slug": "nova-tech-ai",
    "logo_url": "https://...",
    "description": "AI-powered customer analytics platform...",
    "sector": {
      "slug": "ai-ml",
      "name": "AI & Machine Learning"
    },
    "location": {
      "city": "San Francisco",
      "state": "CA",
      "country": "US",
      "coordinates": { "lat": 37.7749, "lng": -122.4194 }
    },
    "stage": "series-a",
    "founded_year": 2021,
    "employee_count": 45,
    "website": "https://novatech.ai",
    "opportunity_score": 82,
    "last_funding": {
      "amount": 12000000,
      "round": "series-a",
      "date": "2024-01-15",
      "lead_investors": ["Sequoia", "a16z"]
    },
    "metrics": {
      "market_size": "High",
      "team_quality": "Strong",
      "traction": "+40% MoM",
      "competition": "Moderate"
    },
    "is_watched": false
  }
}
```

### Caching Strategy

| Data | Cache | TTL |
|------|-------|-----|
| Company details | Redis | 5 min |
| Funding history | Redis | 1 hour |
| News | Redis | 15 min |
| Graph | Redis | 1 hour |

---

## States

### Not Found

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                       │
│  😕 Company not found                                                │
│                                                                       │
│  The company you're looking for doesn't exist or has been removed.    │
│                                                                       │
│  [Go to Search]  [Go to Dashboard]                                   │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### Error State

```
┌─────────────────────────────────────────────────────────────────────┐
│  ⚠️ Failed to load company details                                  │
│                                                                       │
│  Please try again or contact support if the problem persists.         │
│                                                                       │
│  [Retry]                                                             │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Responsive Behavior

### Tablet

- Full-width tabs with horizontal scroll
- 2-column layout for some sections
- Simplified header

### Mobile

```
┌───────────────────────────────────┐
│ [←]                    [♡] [⋯] │
├───────────────────────────────────┤
│  [Logo]                           │
│  Company Name                     │
│  Description...                  │
├───────────────────────────────────┤
│  ⚡ 82  │  Series A  │  $12M    │
│  Score  │  Stage     │  Raised   │
├───────────────────────────────────┤
│  ┌─Tabs (horizontally scrollable)┐
│  │ Overview | Timeline | .. | AI │
│  └──────────────────────────────┘
│                                  │
│  [Tab Content]                   │
│                                  │
└───────────────────────────────────┘
```

---

## Cross-References

| Document | Topic |
|----------|-------|
| [09-ai-analysis.md](./09-ai-analysis.md) | AI analysis flow |
| [07-search.md](./07-search.md) | From search results |
| [17-rest-api-mapping.md](./17-rest-api-mapping.md) | API reference |
| [16-backend-flows.md](./16-backend-flows.md) | Data flow |

---

## Version

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | July 2, 2026 | Initial company profile spec |

---

*Part of the Opportunity Intelligence Platform PRD*
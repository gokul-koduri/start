# Analytics — Opportunity Intelligence Platform

> Chart types, interactive behaviors, data sources, and visualization specifications.

---

## Table of Contents

1. [Analytics Overview](#analytics-overview)
2. [Chart Types](#chart-types)
3. [Chart Library](#chart-library)
4. [Interactive Behaviors](#interactive-behaviors)

---

## Analytics Overview

### Purpose

Analytics features provide:
- Market trend visualization
- Portfolio performance tracking
- Sector distribution charts
- Funding activity graphs

### Locations

| Location | Charts |
|----------|--------|
| Dashboard | Market trends, sector distribution |
| Company Profile | Funding history chart |
| Reports | Custom charts based on report type |
| Analytics page | Full analytics dashboard |

---

## Chart Types

### Line Chart

**Use Case:** Funding activity over time, score trends

```
┌────────────────────────────────────────────────────────────────┐
│  $M │                                          ●─── Series A  │
│     │                      ●────────────●                      │
│  $  │        ●────●───●                        ●─── Seed     │
│     │ ●──●                                            ●─── Pre │
│     └──────────────────────────────────────────────────────►  │
│           2020     2021     2022     2023     2024              │
└────────────────────────────────────────────────────────────────┘
```

**Properties:**
| Property | Value |
|----------|-------|
| X-axis | Time (days/months/years) |
| Y-axis | Value (amount, count, percentage) |
| Lines | Multiple series supported |
| Points | Visible on hover |
| Zoom | Click + drag to zoom |

---

### Bar Chart

**Use Case:** Sector comparison, funding by stage

```
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│     AI/ML  ████████████████████████████████████████ 15420     │
│     SaaS   ████████████████████████████████████████████ 18230│
│     Fintech████████████████████████████████████  13450        │
│     Health███████████████████████████████  9830               │
│     Other███████████████████████████████████████ 15670        │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

**Properties:**
| Property | Value |
|----------|-------|
| Orientation | Vertical or horizontal |
| Grouping | Single, stacked, grouped |
| Labels | Above bars |
| Hover | Tooltip with exact value |

---

### Donut Chart

**Use Case:** Sector distribution, portfolio allocation

```
┌─────────────────────────────┐
│                             │
│       ┌───────────┐         │
│      /             \        │
│     │    35%       │        │
│     │   AI/ML      │        │
│      \             /        │
│       └───────────┘         │
│                             │
│  ● AI/ML (35%)              │
│  ● SaaS (28%)               │
│  ● Fintech (18%)            │
│  ● Other (19%)              │
│                             │
└─────────────────────────────┘
```

**Properties:**
| Property | Value |
|----------|-------|
| Segments | Color-coded |
| Center | Total or percentage |
| Hover | Expand segment |
| Click | Filter related data |

---

### Treemap

**Use Case:** Company sector heatmap on dashboard

```
┌──────────────────────────────────────────────────────────────────┐
│ ┌─────────────────────┬────────────────┬────────────────────┐    │
│ │                     │                │                    │    │
│ │       AI/ML         │    SaaS         │      Fintech       │    │
│ │                    │                │                    │    │
│ │   ┌───────┬─────┐   │                │ ┌──────────────┐   │    │
│ │   │Series │Seed │   ├────────────────┤ │   Series A   │   │    │
│ │   │  A    │     │   │                │ │              │   │    │
│ │   └───────┴─────┘   │    ┌──────┐    │ └──────────────┘   │    │
│ │                     │    │Seed  │    │                    │    │
│ └─────────────────────┴────┴──────┴────────────────────┴────┘    │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

### Scatter Plot

**Use Case:** Portfolio vs market, funding vs score correlation

```
┌────────────────────────────────────────────────────────────────┐
│  Score │                                                        │
│    90  │              ●                                        │
│    80  │                   ●     ●                             │
│    70  │        ●      ●           ●    ●                      │
│    60  │             ●                    ●                   │
│    50  │                                                ○     │
│        └──────────────────────────────────────────────────►   │
│           $0        $10M        $50M        $100M+             │
│                          Funding Raised                          │
│                                                                │
│  ● Portfolio Companies    ○ Market Average                     │
└────────────────────────────────────────────────────────────────┘
```

---

## Chart Library

### Chart.js Usage

```javascript
// Line chart example
new Chart(ctx, {
  type: 'line',
  data: {
    labels: ['Jan', 'Feb', 'Mar'],
    datasets: [{
      label: 'Funding ($M)',
      data: [5, 12, 25],
      borderColor: '#3b82f6',
      tension: 0.4
    }]
  },
  options: {
    responsive: true,
    plugins: {
      legend: { display: true },
      tooltip: { enabled: true }
    }
  }
});
```

### Recharts (if used)

```jsx
<ResponsiveContainer width="100%" height={300}>
  <AreaChart data={data}>
    <XAxis dataKey="month" />
    <YAxis />
    <Tooltip />
    <Area
      type="monotone"
      dataKey="funding"
      stroke="#3b82f6"
      fill="#3b82f620"
    />
  </AreaChart>
</ResponsiveContainer>
```

---

## Interactive Behaviors

### Hover Tooltip

| Chart | Hover Behavior |
|-------|----------------|
| Line | Show value at point |
| Bar | Show exact value |
| Donut | Highlight segment + show %
| Scatter | Show company details |
| Treemap | Show sector details |

### Click Interactions

| Action | Result |
|--------|--------|
| Click line chart point | Navigate to company |
| Click bar segment | Filter by segment |
| Click donut slice | Filter by category |
| Click scatter point | Open company profile |

### Filter Controls

```
┌────────────────────────────────────────────────────────────────┐
│  Filters:  [7D ▼]  [All Sectors ▼]  [All Stages ▼]  [Clear]   │
└────────────────────────────────────────────────────────────────┘
```

### Zoom/Pan

| Chart | Action |
|-------|--------|
| Line | Click + drag or scroll |
| Scatter | Pinch or scroll |
| Map | Drag to pan, scroll to zoom |

---

## Data Sources

| Chart | Endpoint | Refresh |
|-------|----------|---------|
| Funding trend | `/api/v2/market/trends` | 5 min |
| Sector distribution | `/api/v2/market/sectors` | 5 min |
| Company funding | `/api/v2/companies/{id}/funding` | 1 hour |
| Portfolio | `/api/v2/portfolio/summary` | 5 min |

---

## Cross-References

| Document | Topic |
|----------|-------|
| [06-dashboard.md](./06-dashboard.md) | Dashboard charts |
| [20-design-system.md](./20-design-system.md) | Design tokens |

---

## Version

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | July 2, 2026 | Initial analytics spec |

---

*Part of the Opportunity Intelligence Platform PRD*
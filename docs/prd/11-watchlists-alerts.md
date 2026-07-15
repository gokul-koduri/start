# Watchlists & Alerts — Opportunity Intelligence Platform

> User watchlists management, alert configuration, and notification delivery.

---

## Table of Contents

1. [Watchlists Overview](#watchlists-overview)
2. [Watchlist Management](#watchlist-management)
3. [Company Tracking](#company-tracking)
4. [Alert Configuration](#alert-configuration)
5. [Notification Channels](#notification-channels)
6. [Real-Time Updates](#real-time-updates)
7. [API Endpoints](#api-endpoints)

---

## Watchlists Overview

### Purpose

Watchlists enable users to:
- Track specific companies of interest
- Organize companies by theme (portfolio, competition, targets)
- Receive timely alerts about tracked companies
- Share watchlists with team members

### Routes

| Route | Description |
|-------|-------------|
| `/watchlists` | All watchlists with summary |
| `/watchlists/[id]` | Single watchlist detail |

---

## Watchlist Management

### Watchlists List (Desktop)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Watchlists                                    [+ New Watchlist]             │
├─────────────────────────────────────────────────────────────────────────────┤
│  [Search watchlists...]                              Sort: [Recent ▼]         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  👁 My Portfolio                                          12 companies │   │
│  │     Last updated: 2 hours ago                                       │   │
│  │     3 new signals today                                            │   │
│  │     [View]                                                         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  💼 Series A Targets                                      8 companies  │   │
│  │     Last updated: 1 day ago                                       │   │
│  │     1 new signal this week                                        │   │
│  │     [View]                                                         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  👀 Competitors                                           5 companies  │   │
│  │     Last updated: 3 days ago                                       │   │
│  │     No new signals                                                 │   │
│  │     [View]                                                         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Create Watchlist Modal

```
┌─────────────────────────────────────────────────────────────────────┐
│  Create Watchlist                                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Watchlist Name                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ [My New Watchlist                                 ]           │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  Description (optional)                                              │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ [                                                 ]           │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  📌 You can add companies after creating the watchlist.              │
│                                                                       │
│  [Cancel]                                     [Create Watchlist]      │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### Watchlist Card States

| State | Visual |
|-------|--------|
| Default | Standard card |
| Hover | Elevated shadow |
| Empty | "0 companies" badge |
| New signals | Green dot, signal count |
| Shared | Share icon |

---

## Company Tracking

### Watchlist Detail Page

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ← Back                                              [Edit] [Share] [⋯]   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  My Portfolio                                             [+ Add Company]   │
│  12 companies • 3 signals today                                          │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ [🔍 Search within watchlist...]                              [⚙]  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Sort: [Last signal ▼]    Filter: [All ▼]                                │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────┬────────────────────────────────────────────┬───────────────┐   │
│  │ Company │ Last Signal                                │ Score │ Added │   │
│  ├─────────┼────────────────────────────────────────────┼───────────────┤   │
│  │ [Logo]  │ NEW: NovaTech raised Series A - $12M       │ ⚡82 │ 2d ago│   │
│  │ NovaTech│ [View Company]                              │       │       │   │
│  ├─────────┼────────────────────────────────────────────┼───────────────┤   │
│  │ [Logo]  │ NEWS: CloudFlow launched new product       │ ⚡78 │ 1w ago│   │
│  │ CloudFlow│ [View Company]                             │       │       │   │
│  ├─────────┼────────────────────────────────────────────┼───────────────┤   │
│  │ [Logo]  │ No recent signals                          │ ⚡75 │ 3w ago│   │
│  │ DataPro │ [View Company]                              │       │       │   │
│  └─────────┴────────────────────────────────────────────┴───────────────┘   │
│                                                                             │
│  [Load More]                                                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Add Company to Watchlist

**Trigger:** "Add Company" button or company profile action

**Quick Add Modal:**

```
┌─────────────────────────────────────────────────────────────────────┐
│  Add to Watchlist                                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Search companies                                                    │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ 🔍 [Search...                                             ] │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  Recent:                                                             │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ 🏢 NovaTech AI                             [Add]            │   │
│  │    AI/ML • San Francisco                                     │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ 🏢 CloudFlow Systems                          [Add]            │   │
│  │    SaaS • New York                                           │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  Or select a watchlist:                                              │
│  [My Portfolio ▼]                                                   │
│                                                                       │
│  [Cancel]                                                         [Add] │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### Remove Company

| Action | Flow |
|--------|------|
| Click remove | Show confirm dialog |
| Confirm | Remove with toast |

---

## Alert Configuration

### Alert Types

| Type | Trigger | Description |
|------|---------|-------------|
| `score_change` | Score changes by threshold | Alert when score crosses threshold |
| `funding` | Company raises funding | New funding round announced |
| `news` | News article published | Notable news coverage |
| `milestone` | Company reaches milestone | Achievements, partnerships |
| `founder_change` | Team changes | Leadership or board changes |

### Alert Rule Configuration

```
┌─────────────────────────────────────────────────────────────────────┐
│  Alert Settings: My Portfolio                             [Save]    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Generic Alert Preferences                                           │
│  ───────────────────────────────────────────────────────────────     │
│  ☑ Enable alerts for this watchlist                                 │
│                                                                       │
│  ☑ Funding announcements        Sensitivity: [●●●○○ ]              │
│  ☑ News coverage                 Sensitivity: [●●●○○ ]              │
│  ☑ Score changes (>             [10] points)                        │
│  ☑ Team changes                  Sensitivity: [●●○○○ ]              │
│  ☑ Milestone achievements        Sensitivity: [●●●○○ ]              │
│                                                                       │
│  Notification Method                                                 │
│  ───────────────────────────────────────────────────────────────     │
│  ● Email (alerts@example.com)                                        │
│  ○ In-app only                                                        │
│  ○ Slack (if configured)                                             │
│  ○ Webhook (if configured)                                          │
│                                                                       │
│  Frequency                                                           │
│  ───────────────────────────────────────────────────────────────     │
│  ○ Real-time (immediate)                                             │
│  ● Daily digest (batched)                                            │
│  ○ Weekly summary                                                    │
│                                                                       │
│  Quiet Hours                                                         │
│  ───────────────────────────────────────────────────────────────     │
│  ☑ Enable quiet hours                                               │
│  From: [9:00 PM ▼]    To: [9:00 AM ▼]    Timezone: [PST (UTC-8)]   │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### Per-Company Alerts

Override watchlist defaults for specific companies:

```
┌─────────────────────────────────────────────────────────────────────┐
│  Alert Settings: NovaTech AI                                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Use watchlist defaults                         [Customize]          │
│                                                                       │
│  When customized:                                                    │
│  ☑ Funding announcements (watchlist: enabled)                      │
│  ☑ News coverage (watchlist: enabled)                               │
│  ☑ Score changes (watchlist: enabled)                              │
│  ☑ Team changes (watchlist: disabled)  ← Override                 │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Notification Channels

### Channel Options

| Channel | Setup | Use Cases |
|---------|-------|----------|
| Email | Default | All alerts |
| In-app | Always | Quick reference |
| Slack | OAuth integration | Team notifications |
| Webhook | URL configuration | Custom integrations |
| SMS | Phone verification | Urgent only (Enterprise) |

### Slack Integration

**Setup Flow:**

1. Click "Connect Slack" in notification settings
2. OAuth authorization
3. Select channel
4. Configure format (compact/detailed)

**Slack Message Format:**

```
┌────────────────────────────────────────────────────┐
│ 🔵 *NovaTech AI* — New Signal                    │
│                                                   │
│ 💰 *Series A Funding: $12M*                       │
│                                                   │
│ NovaTech AI has raised $12M in Series A funding   │
│ led by Sequoia Capital.                           │
│                                                   │
│ *Score:* 82 (+5 this week)                       │
│                                                   │
│ [View Company] [View Analysis]  _2 hours ago_    │
└────────────────────────────────────────────────────┘
```

### Webhook Configuration

```
┌─────────────────────────────────────────────────────────────────────┐
│  Webhook Settings                                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Webhook URL                                                          │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ [https://api.example.com/alerts                        ]   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  Events to send                                                       │
│  ☑ All events                                                        │
│  ○ Custom selection                                                  │
│  ☑ Funding  ☑ News  ☑ Score changes  ☑ All others               │
│                                                                       │
│  Payload Format                                                       │
│  ○ JSON (recommended)                                                │
│  ○ Form-encoded                                                       │
│                                                                       │
│  [Test Webhook]                                 [Save]               │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### Webhook Payload

```json
{
  "event": "funding",
  "timestamp": "2026-07-02T14:34:00Z",
  "company": {
    "id": "uuid",
    "name": "NovaTech AI",
    "logo_url": "https://..."
  },
  "data": {
    "amount": 12000000,
    "round": "series-a",
    "investors": ["Sequoia", "a16z"]
  },
  "watchlist": {
    "id": "uuid",
    "name": "My Portfolio"
  }
}
```

---

## Real-Time Updates

### WebSocket Subscription

**Endpoint:** `/ws/alerts`

**Subscribe:**
```json
{
  "action": "subscribe",
  "watchlists": ["uuid1", "uuid2"]
}
```

**Alert Notification:**
```json
{
  "type": "alert",
  "data": {
    "id": "signal-uuid",
    "watchlist_id": "uuid",
    "company": { "id": "...", "name": "NovaTech AI" },
    "alert_type": "funding",
    "title": "Series A Funding",
    "body": "$12M raised from Sequoia",
    "priority": "normal",
    "timestamp": "ISO8601"
  }
}
```

### In-App Notification Center

Access via bell icon in header:

```
┌─────────────────────────────────────────────────────────────────────┐
│  Notifications                                    [Mark all read]    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ○ Recent    ○ This Week    ○ All                                  │
│                                                                       │
│  Today                                                              │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ 🔵 NovaTech AI — Series A Funding                           │   │
│  │     $12M raised from Sequoia                                │   │
│  │     2 hours ago                         [View] [Dismiss]     │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ 🔵 CloudFlow — New Product Launch (Read)                    │   │
│  │     Launched enterprise feature                             │   │
│  │     5 hours ago                         [View] [Dismiss]    │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  Yesterday                                                          │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ ⚪ DataPro — Score Updated                                  │   │
│  │     Score changed from 68 to 75                             │   │
│  │     1 day ago                            [View] [Dismiss]   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### Alert States

| State | Visual |
|-------|--------|
| Unread | Bold, blue dot |
| Read | Normal weight |
| Dismissed | Removed from list |
| Snoozed | Hidden until time |

---

## API Endpoints

### Watchlists

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v2/watchlists` | List all watchlists |
| POST | `/api/v2/watchlists` | Create watchlist |
| GET | `/api/v2/watchlists/{id}` | Get watchlist |
| PUT | `/api/v2/watchlists/{id}` | Update watchlist |
| DELETE | `/api/v2/watchlists/{id}` | Delete watchlist |

### Watchlist Companies

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v2/watchlists/{id}/companies` | List companies |
| POST | `/api/v2/watchlists/{id}/companies` | Add company |
| DELETE | `/api/v2/watchlists/{id}/companies/{companyId}` | Remove |

### Alerts

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v2/watchlists/{id}/alerts` | Get alert settings |
| PUT | `/api/v2/watchlists/{id}/alerts` | Update alert settings |
| GET | `/api/v2/alerts` | List all alerts |
| PUT | `/api/v2/alerts/{alertId}` | Update single alert |
| DELETE | `/api/v2/alerts/{alertId}` | Delete alert |

### Notifications

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v2/notifications` | List notifications |
| PUT | `/api/v2/notifications/read` | Mark as read |
| DELETE | `/api/v2/notifications/read-all` | Mark all read |

---

## Response Examples

### Watchlist Response

```json
{
  "data": {
    "id": "uuid",
    "name": "My Portfolio",
    "description": "Companies I've invested in",
    "company_count": 12,
    "alert_enabled": true,
    "alert_settings": {
      "funding": { "enabled": true, "sensitivity": 3 },
      "news": { "enabled": true, "sensitivity": 3 },
      "score_change": { "enabled": true, "threshold": 10 },
      "team_changes": { "enabled": true, "sensitivity": 2 }
    },
    "notification_method": "email",
    "notification_frequency": "daily",
    "created_at": "ISO8601",
    "updated_at": "ISO8601"
  }
}
```

---

## Cross-References

| Document | Topic |
|----------|-------|
| [07-search.md](./07-search.md) | Adding companies via search |
| [18-state-management.md](./18-state-management.md) | State management |
| [17-rest-api-mapping.md](./17-rest-api-mapping.md) | API reference |

---

## Version

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | July 2, 2026 | Initial watchlists spec |

---

*Part of the Opportunity Intelligence Platform PRD*
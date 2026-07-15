# Information Architecture — Opportunity Intelligence Platform

> Navigation hierarchy, URL structure, breadcrumb patterns, and deep linking rules.

---

## Table of Contents

1. [Navigation Hierarchy](#navigation-hierarchy)
2. [URL Structure](#url-structure)
3. [Breadcrumb Patterns](#breadcrumb-patterns)
4. [Deep Linking Rules](#deep-linking-rules)
5. [Navigation Components](#navigation-components)

---

## Navigation Hierarchy

### Site Structure

```
├── Public
│   ├── Landing (/)
│   ├── About (/about)
│   ├── Pricing (/pricing)
│   ├── Features (/features)
│   ├── Auth
│   │   ├── Login (/auth/login)
│   │   ├── Signup (/auth/signup)
│   │   └── Forgot Password (/auth/forgot-password)
│   └── Blog (/blog)
│
├── Authenticated
│   ├── Dashboard (/dashboard)
│   ├── Search (/search)
│   ├── Company
│   │   └── [slug] (/company/[id])
│   │       └── Analysis (/company/[id]/analysis)
│   ├── Watchlists
│   │   ├── List (/watchlists)
│   │   └── [id] (/watchlists/[id])
│   ├── Reports
│   │   ├── List (/reports)
│   │   └── [id] (/reports/[id])
│   ├── Settings (/settings)
│   │   ├── Profile (/settings/profile)
│   │   ├── Security (/settings/security)
│   │   ├── Notifications (/settings/notifications)
│   │   ├── Billing (/settings/billing)
│   │   └── API Keys (/settings/api-keys)
│   └── Search Saved (/search/saved)
│
└── Admin
    ├── Admin Dashboard (/admin)
    ├── Users (/admin/users)
    ├── AI Health (/admin/ai-health)
    ├── System Health (/admin/system)
    ├── Feature Flags (/admin/flags)
    └── Jobs (/admin/jobs)
```

### Navigation Tree Diagram

```mermaid
graph TD
    LA[Landing /] --> AUTH[Auth Group]
    LA --> PUB[Public Pages]

    AUTH --> LOGIN[/auth/login]
    AUTH --> SIGNUP[/auth/signup]

    PUB --> ABOUT[/about]
    PUB --> PRICING[/pricing]
    PUB --> FEATURES[/features]

    DASH[Dashboard] --> SEARCH[/search]
    DASH --> WATCHLISTS[/watchlists]
    DASH --> REPORTS[/reports]
    DASH --> SETTINGS[/settings]

    SEARCH --> COMPANY[/company/:id]
    COMPANY --> ANALYSIS[/company/:id/analysis]

    WATCHLISTS --> WATCHLIST_ITEM[/watchlists/:id]
    REPORTS --> REPORT_ITEM[/reports/:id]

    SETTINGS --> PROF[/settings/profile]
    SETTINGS --> SEC[/settings/security]
    SETTINGS --> BILL[/settings/billing]

    ADMIN[Admin] --> ADMIN_USERS[/admin/users]
    ADMIN --> ADMIN_HEALTH[/admin/system]
    ADMIN --> ADMIN_JOBS[/admin/jobs]
```

---

## URL Structure

### Conventions

| Pattern | Example | Description |
|---------|---------|-------------|
| Kebab-case | `/company-profile` | Static pages |
| Route params | `/company/[id]` | Dynamic resources |
| Actions | `/export`, `/share` | Modals/query actions |
| Nested | `/watchlists/[id]/alerts` | Related resources |

### Complete URL Map

| Route | Page | Auth | Description |
|-------|------|------|-------------|
| `/` | Landing | Public | Marketing page |
| `/about` | About | Public | Company info |
| `/pricing` | Pricing | Public | Plans and pricing |
| `/features` | Features | Public | Feature details |
| `/auth/login` | Login | Public | User login |
| `/auth/signup` | Signup | Public | User registration |
| `/auth/forgot-password` | Forgot Password | Public | Password reset request |
| `/auth/reset-password` | Reset Password | Public | Password reset form |
| `/auth/verify-email` | Verify Email | Public | Email verification |
| `/dashboard` | Dashboard | Required | Main dashboard |
| `/search` | Search | Required | Company search |
| `/search/saved` | Saved Searches | Required | Saved search list |
| `/company/[id]` | Company Profile | Required | Single company view |
| `/watchlists` | Watchlists | Required | Watchlist management |
| `/watchlists/[id]` | Watchlist Detail | Required | Single watchlist |
| `/reports` | Reports | Required | Report list |
| `/reports/[id]` | Report Detail | Required | Single report |
| `/settings` | Settings | Required | Settings hub |
| `/settings/profile` | Profile Settings | Required | User profile |
| `/settings/security` | Security Settings | Required | Password, 2FA |
| `/settings/notifications` | Notification Settings | Required | Alerts config |
| `/settings/billing` | Billing Settings | Required | Subscription info |
| `/settings/api-keys` | API Keys | Required | API key management |
| `/admin` | Admin Dashboard | Admin | System overview |
| `/admin/users` | User Management | Admin | User list |
| `/admin/system` | System Health | Admin | Infrastructure status |
| `/admin/jobs` | Job Queue | Admin | Background jobs |

---

## Breadcrumb Patterns

### Standard Breadcrumb

```
┌─────────────────────────────────────────────────────────────────────┐
│  Home  ›  Dashboard  ›  Company Name                               │
└─────────────────────────────────────────────────────────────────────┘
```

| Context | Breadcrumb |
|---------|------------|
| Landing | Home |
| Dashboard | Home |
| Search | Home  ›  Search |
| Company | Home  ›  Search  ›  Company Name |
| Company (from signal) | Home  ›  Dashboard  ›  Company Name |
| Watchlists | Home  ›  Watchlists |
| Settings | Home  ›  Settings  ›  Profile |

### Implementation

```typescript
const BREADCRUMB_TRAILS = {
  '/dashboard': ['Home'],
  '/search': ['Home', 'Search'],
  '/company/[id]': ['Home', 'Search', 'Company'],
  '/watchlists': ['Home', 'Watchlists'],
  '/watchlists/[id]': ['Home', 'Watchlists', 'Watchlist Name'],
  '/settings/profile': ['Home', 'Settings', 'Profile'],
};
```

### Breadcrumb Component

| Property | Value |
|----------|-------|
| Separator | `›` |
| Current page | Not clickable, bold |
| Previous pages | Clickable links |
| Overflow | Collapsed with `...` for > 4 items |
| Truncation | Mid-truncation for long names |

---

## Deep Linking Rules

### Links to Company

**Valid patterns:**
```
/company/nova-tech-ai-12345
/company/NovaTech-AI
```

**From search:**
```
/search?q=AI+startups
/search?sector=ai-ml
```

**From dashboard signal:**
```
/dashboard?signal=abc123 → /company/[id]
```

### Links to Reports

```
/reports/report-uuid
```

### Links to Specific Analysis

```
/company/nova-tech-ai-12345?tab=ai
/company/nova-tech-ai-12345?tab=ai&analysis=analysis-uuid
```

### External Deep Links

**Format:**
```
https://app.example.com/invite?token=xxx
https://app.example.com/verify-email?token=xxx
https://app.example.com/reset-password?token=xxx
```

### Link Validation

| Type | Validation |
|------|------------|
| Company ID | UUID or valid slug |
| Job ID | UUID |
| Token | Valid JWT with correct type |
| Expired | Show "Link expired" page with recovery |

---

## Navigation Components

### Header Navigation

**Public Header:**
```
┌────────────────────────────────────────────────────────────────────┐
│  Logo   About    Pricing    Features    Blog       [Log In] [Join] │
└────────────────────────────────────────────────────────────────────┘
```

**Authenticated Header:**
```
┌────────────────────────────────────────────────────────────────────┐
│  Logo   [Dashboard]  [Search]  [Watchlists]  [Reports]   🔔 [User] │
└────────────────────────────────────────────────────────────────────┘
```

### Sidebar Navigation

**Settings Sidebar:**
```
┌──────────────────────────────────┐
│  ⚙️ Settings                     │
├──────────────────────────────────┤
│  👤 Profile                     │  ← Active
│  🔒 Security                   │
│  🔔 Notifications              │
│  💳 Billing                     │
│  🔑 API Keys                   │
│  🌙 Theme                       │
│  🛡️ Privacy & GDPR              │
│  🗑️ Delete Account             │
└──────────────────────────────────┘
```

### Mobile Navigation

**Bottom Tab Bar:**
```
┌────────────────────────────────────────────────────────────────────┐
│                                                                       │
│                    [Main Content Area]                              │
│                                                                       │
├────────────────────────────────────────────────────────────────────┤
│   🏠      🔍       👁       📊       ⚙️                            │
│   Home    Search   Watchlist Reports  Settings                        │
└────────────────────────────────────────────────────────────────────┘
```

### User Menu Dropdown

```
┌─────────────────────────────────┐
│  [Avatar] Jane Smith            │
│  jane@company.com               │
├─────────────────────────────────┤
│  👤  My Profile                 │
│  ⚙️  Settings                   │
├─────────────────────────────────┤
│  🔗  Invite Team Member         │
│  💬  Feedback                   │
│  ❓  Help & Support             │
│  📄  Documentation              │
├─────────────────────────────────┤
│  🚪  Log Out                    │
└─────────────────────────────────┘
```

### Notification Bell

```
┌─────────────────────────────────┐
│  🔔 (3)                         │
├─────────────────────────────────┤
│  New Signal Alert               │
│  NovaTech AI raised Series A    │
│  2 hours ago                    │
├─────────────────────────────────┤
│  Analysis Complete              │
│  Your analysis is ready        │
│  5 hours ago                    │
├─────────────────────────────────┤
│  Weekly Digest                  │
│  12 new opportunities          │
│  1 day ago                      │
├─────────────────────────────────┤
│              [View All Alerts]  │
└─────────────────────────────────┘
```

---

## Cross-References

| Document | Topic |
|----------|-------|
| [01-user-journey.md](./01-user-journey.md) | User flow context |
| [03-landing-page.md](./03-landing-page.md) | Landing page spec |
| [20-design-system.md](./20-design-system.md) | Component styling |

---

## Version

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | July 2, 2026 | Initial IA spec |

---

*Part of the Opportunity Intelligence Platform PRD*
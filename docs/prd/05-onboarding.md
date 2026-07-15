# Onboarding — Opportunity Intelligence Platform

> First-time user experience with multi-step wizard, role selection, interests, and alerts configuration.

---

## Table of Contents

1. [Onboarding Overview](#onboarding-overview)
2. [Wizard Structure](#wizard-structure)
3. [Step Specifications](#step-specifications)
4. [Progress & Navigation](#progress--navigation)
5. [Skip Logic](#skip-logic)
6. [Completion Flow](#completion-flow)
7. [API Integration](#api-integration)

---

## Onboarding Overview

### Purpose

Onboarding personalizes the platform experience by:
- Identifying user's role and use case
- Setting initial interests and preferences
- Configuring alert preferences
- Gathering data for recommendations

### Route

`/onboarding`

### Entry Points

| Source | Behavior |
|--------|----------|
| Post-signup | Automatic redirect |
| Dashboard incomplete | Banner + redirect |
| Manual | Settings > Complete Setup |

### Exit Points

| Condition | Destination |
|-----------|-------------|
| Complete | `/dashboard` |
| Skip all | `/dashboard` (defaults applied) |
| Logout | Redirect to landing |

---

## Wizard Structure

### 4-Step Flow

```
Step 1: Role Selection     Step 2: Interests       Step 3: Alerts      Step 4: Import
┌───────────────────┐    ┌──────────────────┐    ┌──────────────┐    ┌──────────────┐
│                   │    │                  │    │              │    │              │
│  Who are you?    │    │  What interests  │    │  How should  │    │  Import      │
│                   │    │  you?           │    │  we notify   │    │  data?       │
│  [ ] Investor    │ ──▶│  you?           │───▶│  you?        │───▶│  (optional)  │
│  [ ] Founder    │    │                  │    │              │    │              │
│  [ ] Accelerator │    │  [AI] [SaaS]    │    │  [Email]     │    │  [CSV]       │
│  [ ] Researcher │    │  [Fintech]      │    │  [Daily]     │    │  [Paste]     │
│  [ ] Other      │    │                  │    │              │    │              │
│                   │    │                  │    │              │    │              │
└───────────────────┘    └──────────────────┘    └──────────────┘    └──────────────┘
```

### Progress Indicator

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                       │
│     ●─────────────────○─────────────────○─────────────────○         │
│                                                                       │
│     Role             Interests       Alerts          Import           │
│   Step 1 of 4                                                  [Skip] │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### Progress Bar (Top)

```
┌─────────────────────────────────────────────────────────────────────┐
│  [████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 25%  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Step Specifications

### Step 1: Role Selection

**Question:** "What's your primary role?"

#### Options

| Role | Description | Icon |
|------|-------------|------|
| Investor | I'm looking for investment opportunities | 💰 |
| Founder | I'm building or growing a startup | 🚀 |
| Accelerator | I manage a startup program | 🎓 |
| Researcher | I study startups and markets | 📊 |
| Other | Different use case | ⚙️ |

#### UI

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                       │
│     What's your primary role?                                         │
│                                                                       │
│     ┌─────────────────────────────────────────────────────────────┐ │
│     │  💰 Investor                                              │ │
│     │      Looking for investment opportunities                  │ │
│     └─────────────────────────────────────────────────────────────┘ │
│     ┌─────────────────────────────────────────────────────────────┐ │
│     │  🚀 Founder                                              │ │
│     │      Building or growing a startup                         │ │
│     └─────────────────────────────────────────────────────────────┘ │
│     ┌─────────────────────────────────────────────────────────────┐ │
│     │  🎓 Accelerator                                           │ │
│     │      Managing a startup program                            │ │
│     └─────────────────────────────────────────────────────────────┘ │
│     ┌─────────────────────────────────────────────────────────────┐ │
│     │  📊 Researcher                                           │ │
│     │      Studying startups and markets                        │ │
│     └─────────────────────────────────────────────────────────────┘ │
│     ┌─────────────────────────────────────────────────────────────┐ │
│     │  ⚙️ Other                                                 │ │
│     │      Different use case                                   │ │
│     └─────────────────────────────────────────────────────────────┘ │
│                                                                       │
│                                    [Continue →]                      │
│                                                                       │
│                                         [Skip this step]             │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

#### Selection Behavior

| Action | Behavior |
|--------|----------|
| Click option | Radio-style selection, highlight |
| Click again | Deselect |
| Enter key | Select focused option |
| Continue | Move to next step |

---

### Step 2: Interests

**Question:** "What sectors and stages interest you?"

#### Sectors

| Category | Sectors |
|----------|---------|
| Technology | AI/ML, SaaS, Cloud, Cybersecurity, DevTools |
| Finance | Fintech, Insurtech, Payments, Crypto |
| Health | HealthTech, BioTech, MedTech, Digital Health |
| Consumer | E-commerce, Marketplaces, Social, Gaming |
| Enterprise | HR Tech, CRM, Supply Chain, Legal Tech |
| Other | CleanTech, Space Tech, Food Tech, Real Estate |

#### UI

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                       │
│     What areas interest you?                                         │
│     Select the sectors and funding stages you'd like to focus on.   │
│                                                                       │
│     Sectors (select all that apply)                                 │
│     ──────────────────────────────────────────────────────────────── │
│     [AI/ML      ] [SaaS] [Fintech] [HealthTech] [E-commerce]        │
│     [Cybersecurity] [Crypto] [BioTech] [HR Tech] [EdTech]            │
│     [CleanTech] [Robotics] [IoT] [AR/VR] [Marketplaces]             │
│                                                                       │
│     Funding Stages (select all that apply)                          │
│     ──────────────────────────────────────────────────────────────── │
│     [ ] Pre-seed    [✓] Seed    [✓] Series A    [ ] Series B+       │
│                                                                       │
│     Geographic Focus                                                │
│     ──────────────────────────────────────────────────────────────── │
│     [All Regions ▼]                                                  │
│     Could be multi-select with search                               │
│                                                                       │
│                                    [Continue →]                      │
│                                                                       │
│                                         [Skip this step]             │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

#### Interests Persistence

Selected interests affect:
- Dashboard recommendations
- Email digest content
- Signal filtering
- Search suggestions

---

### Step 3: Alerts

**Question:** "How would you like to be notified?"

#### Alert Preferences

| Setting | Options | Default |
|---------|---------|---------|
| Notification method | Email, In-app, Both | Email |
| Alert frequency | Real-time, Daily digest, Weekly | Daily digest |
| Alert types | Funding, News, Milestones, All | All |

#### UI

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                       │
│     How should we notify you?                                         │
│                                                                       │
│     Notification Method                                              │
│     ──────────────────────────────────────────────────────────────── │
│     (•) Email        [alerts@example.com]                           │
│     ( ) In-app only                                              │
│     ( ) Both                                                       │
│                                                                       │
│     Alert Frequency                                                │
│     ──────────────────────────────────────────────────────────────── │
│     ( ) Real-time      Receive alerts as they happen               │
│     (•) Daily digest   One summary email each morning               │
│     ( ) Weekly         One summary email each week                  │
│                                                                       │
│     Alert Types                                                    │
│     ──────────────────────────────────────────────────────────────── │
│     [✓] Funding announcements                                      │
│     [✓] News and press coverage                                    │
│     [✓] Team and leadership changes                                │
│     [✓] Product milestones                                         │
│                                                                       │
│                                    [Continue →]                      │
│                                                                       │
│                                         [Skip this step]             │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

### Step 4: Import Data (Optional)

**Question:** "Do you have existing companies to track?"

#### Import Options

| Option | Description |
|--------|-------------|
| Upload CSV | Drag & drop or browse for CSV file |
| Paste list | Paste company names/URLs, one per line |
| Skip | Continue without importing |

#### CSV Format

```csv
name,domain,sector
NovaTech AI,novatech.ai,ai-ml
CloudFlow,cloudflow.io,saas
```

#### Import UI

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                       │
│     Import existing data?                                            │
│     You can import companies you already track to get started        │
│     faster.                                                           │
│                                                                       │
│     ┌─────────────────────────────────────────────────────────────┐ │
│     │                                                              │ │
│     │         📄 Upload CSV                                        │ │
│     │                                                              │ │
│     │    Drag and drop or [browse to upload]                      │ │
│     │                                                              │ │
│     │    Supported format: .csv                                    │ │
│     │                                                              │ │
│     └─────────────────────────────────────────────────────────────┘ │
│                                                                       │
│     OR                                                               │
│                                                                       │
│     ┌─────────────────────────────────────────────────────────────┐ │
│     │  Paste company names or URLs, one per line                  │ │
│     │                                                              │ │
│     │  [                                                        ] │ │
│     │  [                                                        ] │ │
│     │  [                                                        ] │ │
│     │                                                              │ │
│     └─────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  Found 5 companies from pasted list                                  │
│                                                                       │
│                                    [Continue →]                      │
│                                                                       │
│                                         [Skip this step]             │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Progress & Navigation

### Progress Indicator

| Element | Behavior |
|---------|----------|
| Steps dots | Numbered circles, current filled |
| Progress line | Animates between steps |
| Step labels | Shown on desktop, hidden on mobile |
| Percentage | Calculated: (step - 1) / total * 100 |

### Navigation Buttons

| Button | Behavior |
|--------|----------|
| Continue/Next | Validate step, advance |
| Back | Return to previous step |
| Skip | Skip current step (if allowed) |
| Save & Exit | Persist progress, redirect |

### Keyboard Navigation

| Key | Action |
|-----|--------|
| Tab | Move focus between fields |
| Enter | Submit current step |
| Escape | Pause/discard |
| Left Arrow | Previous step (if valid) |
| Right Arrow | Next step (if valid) |

---

## Skip Logic

### Allowed Skips

| Step | Can Skip | Default If Skipped |
|------|----------|-------------------|
| 1. Role | Yes | "other" |
| 2. Interests | Yes | All sectors, all stages |
| 3. Alerts | Yes | Email, daily, all types |
| 4. Import | Yes | No companies imported |

### Skip Indicator

```
                                    [Skip this step]
```

Displayed below Continue button for optional steps.

### Skip Confirmation

Not required - skipping sets sensible defaults silently.

---

## Completion Flow

### Final Step Completion

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                       │
│     🎉 You're all set!                                                │
│                                                                       │
│     Your preferences have been saved. Here's what we'll do:          │
│                                                                       │
│     • Show AI/ML and SaaS companies from US in your dashboard       │
│     • Send you a daily digest of relevant opportunities             │
│     • Notify you of funding rounds and news                         │
│                                                                       │
│     ┌─────────────────────────────────────────────────────────────┐ │
│     │                                                              │ │
│     │                    [Go to Dashboard →]                      │ │
│     │                                                              │ │
│     └─────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  You can update your preferences anytime in Settings.                 │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### Post-Completion Redirect

After 3 seconds on completion screen (if no click), auto-redirect to `/dashboard`.

---

## API Integration

### Save Preferences

**Endpoint:** `PUT /api/v2/users/me/preferences`

**Request:**
```json
{
  "onboarding_complete": true,
  "role": "investor",
  "interests": {
    "sectors": ["ai-ml", "saas", "fintech"],
    "stages": ["seed", "series-a"],
    "regions": ["US", "UK"]
  },
  "notifications": {
    "method": "email",
    "frequency": "daily",
    "types": ["funding", "news", "milestones"]
  }
}
```

**Response:**
```json
{
  "data": {
    "preferences_id": "uuid",
    "onboarding_complete": true,
    "saved_at": "ISO8601"
  }
}
```

### Import Companies

**Endpoint:** `POST /api/v2/companies/import`

**Request:**
```json
{
  "source": "csv",
  "companies": [
    { "name": "NovaTech AI", "domain": "novatech.ai" }
  ]
}
```

**Response:**
```json
{
  "data": {
    "imported": 4,
    "not_found": 1,
    "matched": [
      { "name": "NovaTech AI", "id": "uuid", "status": "added_to_watchlist" }
    ],
    "not_found_list": ["NonExistent Corp"]
  }
}
```

### Progress Persistence

On each step completion, save partial progress:
```json
{
  "onboarding_progress": {
    "step1_complete": true,
    "step2_complete": false,
    "step3_complete": false,
    "step4_complete": false
  }
}
```

This allows resuming if user leaves mid-onboarding.

---

## States

### Loading

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                       │
│     [Loading spinner] Saving your preferences...                      │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### Error

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                       │
│     ⚠️ Unable to save your preferences. Please try again.           │
│                                                                       │
│     [Try Again]                                      [Continue Anyway]│
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### Returning User (Incomplete)

```
┌─────────────────────────────────────────────────────────────────────┐
│  ⚠️ You've started setup but haven't finished.                       │
│     Complete your preferences to personalize your experience.       │
│                                                                       │
│     [Continue Setup]                              [Dismiss]           │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Responsive Behavior

### Mobile Layout

Single-column, larger touch targets (48px minimum):
```
┌───────────────────────────┐
│  ●──────○──────○──────○   │
│  25%           [Skip all] │
├───────────────────────────┤
│                           │
│  What's your role?        │
│                           │
│  [  Investor         ▼  ] │
│  [  Founder             ] │
│  [  Accelerator         ] │
│                           │
│                           │
│   [Continue →]            │
│                           │
└───────────────────────────┘
```

---

## Cross-References

| Document | Topic |
|----------|-------|
| [01-user-journey.md](./01-user-journey.md) | User flow context |
| [04-authentication.md](./04-authentication.md) | Auth spec |
| [11-watchlists-alerts.md](./11-watchlists-alerts.md) | Alerts config |
| [17-rest-api-mapping.md](./17-rest-api-mapping.md) | API reference |

---

## Version

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | July 2, 2026 | Initial onboarding spec |

---

*Part of the Opportunity Intelligence Platform PRD*
# Landing Page — Opportunity Intelligence Platform

> Public marketing page specifications including hero, benefits, features, demo, pricing, testimonials, and FAQ.

---

## Table of Contents

1. [Landing Overview](#landing-overview)
2. [Hero Section](#hero-section)
3. [Benefits Grid](#benefits-grid)
4. [Features Section](#features-section)
5. [Interactive Demo](#interactive-demo)
6. [Pricing Section](#pricing-section)
7. [Testimonials](#testimonials)
8. [FAQ Section](#faq-section)
9. [Footer](#footer)
10. [Components](#components)

---

## Landing Overview

### Purpose

The landing page is the public-facing entry point for:
- Converting visitors to signups
- Showcasing platform value
- Providing feature overview
- Displaying pricing information

### Route

`/`

### Design

| Property | Value |
|----------|-------|
| Theme | Dark mode primary (matches app) |
| Max content width | 1200px |
| Section padding | 96px vertical (desktop), 48px (mobile) |
| Background | Gradient from `--color-bg-primary` to subtle accents |

### Page Structure

```
[Header - Sticky]
[Hero Section]
[Social Proof Bar]
[Benefits Grid]
[Features Section]
[Interactive Demo]
[Pricing Section]
[Testimonials]
[FAQ]
[CTA Banner]
[Footer]
```

---

## Hero Section

### Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│                                                                             │
│        Discover Startup Opportunities                                       │
│        Before Your Competition                                              │
│                                                                             │
│        AI-powered analysis to surface high-potential startups,             │
│        track market signals, and make data-driven investment                 │
│        decisions faster than ever.                                          │
│                                                                             │
│        ┌─────────────────────────────────┐  ┌──────────────────┐           │
│        │  Enter your work email          │  │  Start Free      │           │
│        └─────────────────────────────────┘  └──────────────────┘           │
│                                                                             │
│        Trusted by 2,000+ investors and analysts                            │
│                                                                             │
│        ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐                   │
│        │  Logo1  │  │  Logo2  │  │  Logo3  │  │  Logo4  │                   │
│        └─────────┘  └─────────┘  └─────────┘  └─────────┘                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Hero Elements

| Element | Specification |
|---------|---------------|
| Headline | h1, 56px (desktop), 36px (mobile), bold |
| Subheadline | p, 20px, secondary color, max-width 600px |
| CTA Primary | "Start Free Trial" - filled button |
| CTA Secondary | "See Demo" - outline button |
| Social proof | Logos of client companies, grayscale |

### States

**CTA Hover:** Background lightens 10%
**Demo click:** Opens modal with interactive demo

---

## Social Proof Bar

### Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Used by teams at:                                                          │
│                                                                             │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐          │
│  │ Sequoia │  │  a16z   │  │ YC      │  │ Accel   │  │ SoftBank│          │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Properties

| Property | Value |
|----------|-------|
| Background | `--color-bg-secondary` |
| Logos | Grayscale, 60% opacity, hover 100% |
| Animation | Subtle scroll animation on scroll-in |
| Spacing | 48px padding, 32px gaps |

---

## Benefits Grid

### Layout (2x2 on desktop, 1 column mobile)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Why Leading Investors Choose Our Platform                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────┐  ┌─────────────────────────────┐          │
│  │                              │  │                              │          │
│  │  🚀                         │  │  🎯                          │          │
│  │                              │  │                              │          │
│  │  10x Faster Discovery       │  │  AI-Powered Scores           │          │
│  │                              │  │                              │          │
│  │  Find opportunities in      │  │  Data-driven opportunity    │          │
│  │  minutes, not days. Our     │  │  scores with transparent    │          │
│  │  semantic search covers     │  │  factor breakdowns help     │          │
│  │  millions of companies.     │  │  you understand why.        │          │
│  │                              │  │                              │          │
│  └─────────────────────────────┘  └─────────────────────────────┘          │
│                                                                             │
│  ┌─────────────────────────────┐  ┌─────────────────────────────┐          │
│  │                              │  │                              │          │
│  │  📡                         │  │  👥                          │          │
│  │                              │  │                              │          │
│  │  Real-Time Signals           │  │  Team Collaboration         │          │
│  │                              │  │                              │          │
│  │  Be first to know about     │  │  Share findings, manage     │          │
│  │  funding rounds, team        │  │  watchlists, and coordinate │          │
│  │  changes, and milestones.    │  │  due diligence across team. │          │
│  │                              │  │                              │          │
│  └─────────────────────────────┘  └─────────────────────────────┘          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Card Specifications

| Property | Value |
|----------|-------|
| Background | `--color-bg-secondary` |
| Border | 1px `--color-border` |
| Border radius | 16px |
| Padding | 32px |
| Icon size | 48px |
| Title | h3, 24px, bold |
| Description | 16px, secondary color |

---

## Features Section

### Layout (Tab-based)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Everything You Need for Startup Discovery                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  [Search] [Analysis] [Signals] [Reports]                                     │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│       Screenshot/Mockup                    Feature Description              │
│       ┌─────────────────┐                                                  │
│       │                 │                 Advanced Search                   │
│       │    [Image]      │                 ─────────────────                 │
│       │                 │                 Semantic search powered by        │
│       │                 │                 AI understands intent, not just    │
│       │                 │                 keywords.                          │
│       │                 │                                                  │
│       └─────────────────┘                 • Natural language queries        │
│                                          • Sector and stage filtering        │
│                                          • Saved searches with alerts        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Feature Tabs

| Tab | Description |
|-----|-------------|
| Search | Semantic company discovery |
| Analysis | AI-powered company analysis |
| Signals | Real-time market monitoring |
| Reports | Export and sharing tools |

### Tab Content States

| State | Behavior |
|-------|----------|
| Default | First tab selected |
| Click | Switch content + URL update |
| Keyboard | Arrow keys navigate tabs |
| Mobile | Swipe gesture support |

---

## Interactive Demo

### Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  See It In Action                                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                         │ │
│  │  Simulated dashboard showing:                                           │ │
│  │  • Live signal feed                                                    │ │
│  │  • Search in action                                                    │ │
│  │  • AI analysis preview                                                 │ │
│  │                                                                         │ │
│  │  [▶ Play Demo]                                                         │ │
│  │                                                                         │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  [Schedule Live Demo]  [Try Free for 14 Days]                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Demo Player

| Property | Value |
|----------|-------|
| Video/Animation | Looped screen recording or interactive |
| Controls | Play/pause, replay, mute |
| Duration | 60-90 seconds |
| CTA below | Secondary actions |

---

## Pricing Section

### Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Simple, Transparent Pricing                                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐        │
│  │                  │  │    ★ Popular     │  │                      │        │
│  │     Starter      │  │     Pro          │  │     Enterprise      │        │
│  │                  │  │                  │  │                      │        │
│  │     $0/mo        │  │     $99/mo       │  │     Custom          │        │
│  │                  │  │                  │  │                      │        │
│  │  For individual  │  │  For serious     │  │  For teams and      │        │
│  │  investors       │  │  investors       │  │  organizations      │        │
│  │                  │  │                  │  │                      │        │
│  ├──────────────────┤  ├──────────────────┤  ├──────────────────────┤        │
│  │ • 50 searches   │  │ • Unlimited      │  │ • Everything in Pro │        │
│  │ • 5 analyses/mo  │  │   searches       │  │ • Unlimited AI      │        │
│  │ • 1 watchlist   │  │ • 100 analyses/mo │  │   analyses          │        │
│  │ • Email alerts  │  │ • 10 watchlists   │  │ • Unlimited teams   │        │
│  │                  │  │ • All alerts     │  │ • API access        │        │
│  │                  │  │ • Reports        │  │ • SSO/SAML          │        │
│  │                  │  │                  │  │ • Dedicated support │        │
│  │  [Get Started]   │  │  [Start Free]     │  │  [Contact Sales]     │        │
│  │                  │  │                  │  │                      │        │
│  └──────────────────┘  └──────────────────┘  └──────────────────────┘        │
│                                                                             │
│  All plans include a 14-day free trial. No credit card required.            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Pricing Card States

| State | Visual |
|-------|--------|
| Default | Standard styling |
| Hover | Subtle lift, border glow |
| Popular | Accent border, "Popular" badge |
| CTA Hover | Button color change |

---

## Testimonials

### Carousel

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Trusted by Industry Leaders                                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                                                                       │ │
│  │  "This platform has completely changed how we source deals.          │ │
│  │  The AI analysis saves our team countless hours of research."         │ │
│  │                                                                       │ │
│  │  ┌──────┐  Sarah Chen                                                 │ │
│  │  │ IMG  │  Partner, Sequoia Capital                                    │ │
│  │  └──────┘                                                             │ │
│  │                                                                       │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│       ○  ●  ○  ○                                            [Prev] [Next] │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Carousel Controls

| Control | Behavior |
|---------|----------|
| Auto-rotate | Every 5 seconds |
| Dots | Click to jump to slide |
| Prev/Next | Arrow buttons |
| Pause | On hover |
| Swipe | On mobile |

---

## FAQ Section

### Accordion

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Frequently Asked Questions                                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  How accurate are the AI-generated scores?                    [+]  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  How does the semantic search work?                            [+]  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  What data sources do you use?                                 [+]  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Can I export data from the platform?                           [+]  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Do you offer API access?                                        [+]  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Accordion Behavior

| Action | Behavior |
|---------|----------|
| Click header | Toggle expand/collapse |
| Click + | Expand |
| Click - | Collapse |
| Animation | Height transition, 200ms |

---

## Footer

### Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Logo      Product        Company       Resources       Legal     Social   │
│  ──────    ───────        ───────       ─────────       ─────     ──────  │
│             Features       About         Blog            Terms     Twitter  │
│             Pricing        Careers       Documentation   Privacy   LinkedIn │
│             Changelog      Press         API Reference    Cookies   GitHub   │
│             Roadmap        Contact       Community                              │
│                                                                             │
│  © 2026 Platform Name. All rights reserved.                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Components

### Landing Page Component Inventory

| Component | States | Location |
|-----------|--------|----------|
| Navigation | Default, Sticky, Mobile | Header |
| Hero CTA Button | Default, Hover, Loading | Hero |
| Benefit Card | Default, Hover | Benefits Grid |
| Feature Tab | Default, Active, Hover | Features |
| Pricing Card | Default, Popular, Hover | Pricing |
| Testimonial Slide | Active, Inactive | Testimonials |
| FAQ Item | Collapsed, Expanded | FAQ |
| Footer Link | Default, Hover | Footer |

---

## Cross-References

| Document | Topic |
|----------|-------|
| [01-user-journey.md](./01-user-journey.md) | User flow entry |
| [13-settings.md](./13-settings.md) | Settings spec |
| [20-design-system.md](./20-design-system.md) | Design tokens |

---

## Version

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | July 2, 2026 | Initial landing page spec |

---

*Part of the Opportunity Intelligence Platform PRD*
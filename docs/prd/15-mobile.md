# Mobile Experience — Opportunity Intelligence Platform

> Responsive specifications, touch targets, mobile patterns, and breakpoint behaviors.

---

## Table of Contents

1. [Mobile Overview](#mobile-overview)
2. [Touch Targets](#touch-targets)
3. [Responsive Breakpoints](#responsive-breakpoints)
4. [Mobile Patterns](#mobile-patterns)

---

## Mobile Overview

### Approach

The platform is **responsive** (not a separate mobile app):
- Web app adapts to all screen sizes
- No native mobile apps in Phase 1
- Touch-optimized interactions

### Supported Devices

| Device | Support Level |
|--------|---------------|
| iPhone 12+ | Full support |
| Android phones | Full support |
| Tablets | Full support |
| Small phones | Graceful degradation |

---

## Touch Targets

### Minimum Size

| Element | Minimum | Recommended |
|---------|---------|-------------|
| Buttons | 44x44px | 48x48px |
| Links | 44x44px | 48x44px |
| Checkboxes | 44x44px | 48x48px |
| Tap areas | 44x44px | 48x48px |

### Spacing Between

- Minimum 8px between touch targets
- Recommended 12px for frequently used elements

---

## Responsive Breakpoints

### Breakpoint Map

| Name | Width | Layout |
|------|-------|--------|
| Mobile | <640px | Single column, bottom nav |
| Tablet | 640-1024px | 2 columns, top nav |
| Desktop | 1024-1440px | Full layout |
| Large | 1440px+ | Extended layout |

### Container Widths

| Breakpoint | Max Width |
|------------|-----------|
| Mobile | 100% |
| Tablet | 720px |
| Desktop | 1200px |
| Large | 1440px |

---

## Mobile Patterns

### Bottom Navigation (Mobile)

```
┌───────────────────────────────────┐
│                                   │
│        [Page Content]             │
│                                   │
│                                   │
├───────────────────────────────────┤
│   🏠      🔍      👁      📊     │
│   Home    Search  Watch  Settings  │
└───────────────────────────────────┘
```

### Swipe Gestures

| Action | Gesture |
|--------|---------|
| Open menu | Swipe from left |
| View details | Swipe card right |
| Dismiss | Swipe left |
| Refresh | Pull down |

### Mobile Search

```
┌───────────────────────────────────┐
│  [←]  🔍 Search companies...     │
│ ──────────────────────────────────── │
│  Sectors    Stage    Location      │
│ ──────────────────────────────────── │
│                                   │
│  [Company Card - full width]      │
│                                   │
│  [Company Card - full width]      │
│                                   │
│  [Company Card - full width]      │
│                                   │
└───────────────────────────────────┘
```

---

## Version

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | July 2, 2026 | Initial mobile spec |

---

*Part of the Opportunity Intelligence Platform PRD*
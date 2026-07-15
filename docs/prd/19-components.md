# Component Library — Opportunity Intelligence Platform

> Reusable UI components with states, props, and accessibility.

---

## Table of Contents

1. [Components Overview](#components-overview)
2. [Button](#button)
3. [Card](#card)
4. [Input](#input)
5. [Modal](#modal)
6. [Table](#table)

---

## Components Overview

### Button

| State | Appearance |
|-------|------------|
| Default | Primary blue |
| Hover | Darker blue |
| Active | Even darker |
| Disabled | Gray, no pointer |

**Props:**
```typescript
interface ButtonProps {
  variant: 'primary' | 'secondary' | 'outline' | 'ghost';
  size: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  loading?: boolean;
  children: ReactNode;
}
```

### Card

| State | Appearance |
|-------|------------|
| Default | Dark bg, border |
| Hover | Elevated shadow |

---

## Version

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | July 2, 2026 | Initial components |

---

*Part of the Opportunity Intelligence Platform PRD*
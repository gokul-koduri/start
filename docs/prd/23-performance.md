# Performance — Opportunity Intelligence Platform

> Performance budgets, optimizations, and measurement targets.

---

## Table of Contents

1. [Performance Targets](#performance-targets)
2. [Optimization Strategies](#optimization-strategies)
3. [Monitoring](#monitoring)

---

## Performance Targets

### Core Web Vitals

| Metric | Target | Measurement |
|--------|--------|-------------|
| FCP | < 1.5s | P95 |
| LCP | < 2.5s | P95 |
| CLS | < 0.1 | P95 |
| TTFB | < 200ms | P95 |

### API Performance

| Endpoint Type | Target |
|---------------|--------|
| Simple read | < 100ms |
| Search | < 500ms |
| AI Analysis | < 90s |

---

## Optimization Strategies

### Code Splitting

```javascript
const CompanyProfile = dynamic(() => import('./pages/company/[id]'));
```

### Image Optimization

- Next.js Image component
- WebP format
- Lazy loading

---

## Monitoring

### APM Integration

- Error tracking
- Performance monitoring
- Real user monitoring

---

## Version

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | July 2, 2026 | Initial performance spec |

---

*Part of the Opportunity Intelligence Platform PRD*
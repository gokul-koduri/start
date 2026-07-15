# Product Requirements Document — Opportunity Intelligence Platform

> Comprehensive UX specification, PRD, and technical documentation for the AI-powered startup opportunity intelligence platform.

## Quick Navigation

| Section | Priority | File |
|---------|----------|------|
| [Overview](./00-overview.md) | P0 | Executive summary and platform goals |
| [User Journey](./01-user-journey.md) | P0 | Complete user flow from visitor to logout |
| [Dashboard](./06-dashboard.md) | P0 | Main dashboard widgets and KPIs |
| [Search](./07-search.md) | P0 | Company search with semantic filtering |
| [Company Profile](./08-company-profile.md) | P0 | Detailed company view with AI analysis |
| [AI Analysis UX](./09-ai-analysis.md) | P0 | Async AI workflows and job management |
| [Authentication](./04-authentication.md) | P1 | Signup, login, password management |
| [Onboarding](./05-onboarding.md) | P1 | First-time user experience |
| [Information Architecture](./02-information-architecture.md) | P1 | Navigation hierarchy and URL structure |
| [Landing Page](./03-landing-page.md) | P1 | Public marketing pages |
| [Reports](./10-reports.md) | P1 | Report generation and export |
| [Watchlists & Alerts](./11-watchlists-alerts.md) | P1 | Personal watchlists and notifications |
| [Backend Flows](./16-backend-flows.md) | P1 | System integration diagrams |
| [REST API Mapping](./17-rest-api-mapping.md) | P1 | Complete API action mapping |
| [Analytics](./12-analytics.md) | P2 | Charts and data visualization |
| [Settings](./13-settings.md) | P2 | User preferences and configuration |
| [Admin Portal](./14-admin-portal.md) | P2 | Admin dashboard and monitoring |
| [Mobile Experience](./15-mobile.md) | P2 | Responsive design specifications |
| [State Management](./18-state-management.md) | P2 | Frontend state architecture |
| [Component Library](./19-components.md) | P2 | Reusable UI components |
| [Design System](./20-design-system.md) | P2 | Typography, colors, spacing |
| [Error Handling](./21-error-handling.md) | P2 | Error states and recovery |
| [Security](./22-security.md) | P2 | Auth, RBAC, GDPR compliance |
| [Performance](./23-performance.md) | P2 | Optimization specifications |
| [End-to-End Flows](./24-end-to-end-flows.md) | P2 | Complete workflow specifications |

---

## Document Structure

### Core Sections (P0)
The P0 sections define the critical user flows that must be fully functional:

- **User Journey**: 13-stage flow from discovery to logout
- **Dashboard**: Real-time KPIs, live signal feed, sector heatmap
- **Search**: Semantic search with Elasticsearch + Qdrant
- **Company Profile**: Comprehensive company view with graphs
- **AI Analysis**: Async job processing with SSE streaming

### Important Features (P1)
P1 sections cover essential features that enhance user experience:

- Authentication flows (signup, login, password reset)
- Onboarding wizard
- Information architecture
- Report generation and export
- Watchlists and alert system

### Supporting Specifications (P2)
P2 sections provide technical reference:

- Analytics charts and visualizations
- Settings and preferences
- Admin portal capabilities
- Mobile responsive design
- State management patterns
- Component library
- Design system tokens
- Error handling strategies
- Security specifications
- Performance budgets
- End-to-end workflow diagrams

---

## Related Documentation

| Document | Location | Purpose |
|----------|----------|---------|
| REST API Specification | [../api/REST_API_SPEC.md](../api/REST_API_SPEC.md) | Complete API endpoint reference |
| Architecture Plan | [../engineering/architecture-plan.md](../engineering/architecture-plan.md) | System architecture |
| User Stories | [../user-stories/stories.md](../user-stories/stories.md) | User requirements |
| Design System | [./20-design-system.md](./20-design-system.md) | Visual design tokens |

---

## Cross-Reference Quick Links

### User Flow References
- Landing → Signup: [03-landing-page.md#call-to-action](./03-landing-page.md#call-to-action)
- Signup → Login: [04-authentication.md#post-signup](./04-authentication.md#post-signup-flow)
- Login → Onboarding: [04-authentication.md#post-login](./04-authentication.md#post-login-flow)
- Onboarding → Dashboard: [05-onboarding.md#completion](./05-onboarding.md#completion)
- Dashboard → Search: [06-dashboard.md#quick-search](./06-dashboard.md#quick-search)
- Search → Company: [07-search.md#result-click](./07-search.md#result-click)
- Company → AI Analysis: [08-company-profile.md#ai-analysis-tab](./08-company-profile.md#ai-analysis-tab)

### Technical References
- API Endpoints: [17-rest-api-mapping.md](./17-rest-api-mapping.md)
- Component Props: [19-components.md](./19-components.md)
- Design Tokens: [20-design-system.md](./20-design-system.md)
- Error Codes: [21-error-handling.md#error-codes](./21-error-handling.md#error-codes)
- Security: [22-security.md](./22-security.md)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | July 2, 2026 | Initial comprehensive PRD |

---

*Last updated: July 2, 2026*
*Document Version: 1.0.0*
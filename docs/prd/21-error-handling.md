# Error Handling — Opportunity Intelligence Platform

> Error taxonomy, user-friendly messages, states, and recovery strategies.

---

## Table of Contents

1. [Error Taxonomy](#error-taxonomy)
2. [HTTP Errors](#http-errors)
3. [Frontend Errors](#frontend-errors)

---

## Error Taxonomy

### Error Types

| Type | Code | User Message |
|------|------|--------------|
| Validation | 400 | "Please check your input" |
| Unauthorized | 401 | "Please log in" |
| Forbidden | 403 | "Access denied" |
| Not Found | 404 | "Resource not found" |
| Rate Limit | 429 | "Too many requests" |
| Server | 500 | "Something went wrong" |

---

## HTTP Errors

### 404 Error Page

```
┌─────────────────────────────────────────────┐
│                                             │
│  404                                       │
│  Page not found                            │
│                                             │
│  [Go to Dashboard]  [Go to Search]        │
│                                             │
└─────────────────────────────────────────────┘
```

---

## Frontend Errors

### Toast Notifications

| Type | Color | Use |
|------|-------|-----|
| Error | Red | Error messages |
| Success | Green | Success messages |
| Warning | Yellow | Warnings |
| Info | Blue | Information |

---

## Version

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | July 2, 2026 | Initial error handling |

---

*Part of the Opportunity Intelligence Platform PRD*
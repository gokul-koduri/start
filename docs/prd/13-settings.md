# Settings — Opportunity Intelligence Platform

> User settings and preferences including profile, security, billing, notifications, and privacy.

---

## Table of Contents

1. [Settings Overview](#settings-overview)
2. [Profile Settings](#profile-settings)
3. [Security Settings](#security-settings)
4. [Notification Settings](#notification-settings)
5. [Billing Settings](#billing-settings)
6. [API Keys](#api-keys)
7. [Privacy & GDPR](#privacy--gdpr)
8. [Delete Account](#delete-account)

---

## Settings Overview

### Settings Hub

**Route:** `/settings`

### Sidebar Navigation

| Section | Route | Description |
|---------|-------|-------------|
| Profile | `/settings/profile` | Personal information |
| Security | `/settings/security` | Password, 2FA |
| Notifications | `/settings/notifications` | Alert preferences |
| Billing | `/settings/billing` | Subscription, invoices |
| API Keys | `/settings/api-keys` | Developer access |
| Theme | - | Display preferences |
| Privacy | `/settings/privacy` | Data export, GDPR |
| Danger Zone | - | Delete account |

---

## Profile Settings

### Profile Form

```
┌─────────────────────────────────────────────────────────────────────┐
│  Profile Settings                                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Profile Picture                                                     │
│  ┌───────┐  ┌─────────────────────────────┐                          │
│  │ Image │  │ [Upload New]  [Remove]     │                          │
│  │       │  │ JPG, PNG or GIF. Max 5MB.   │                          │
│  └───────┘  └─────────────────────────────┘                          │
│                                                                       │
│  Full Name                                                           │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ [Jane Smith                                              ] │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  Email Address                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ [jane@company.com]                                          │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  ⚠️ Email not verified. Check your inbox                        │
│  [Resend verification email]                                       │
│                                                                       │
│  Job Title                                                           │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ [Partner                                                        ] │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  Company / Organization                                              │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ [Sequoia Capital                                              ] │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  Timezone                                                           │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ [Pacific Time (US & Canada) (UTC-8)                    ▼]   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│                           [Save Changes]                             │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Security Settings

### Security Tab

```
┌─────────────────────────────────────────────────────────────────────┐
│  Security Settings                                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Password                                                            │
│  ──────────────────────────────────────────────────────────────     │
│  Last changed: March 15, 2026                                       │
│                                                                       │
│  [Change Password]                                                   │
│                                                                       │
│  ──────────────────────────────────────────────────────────────     │
│                                                                       │
│  Two-Factor Authentication                                           │
│  ──────────────────────────────────────────────────────────────     │
│  Status: Not enabled                                                │
│                                                                       │
│  Add an extra layer of security to your account.                     │
│                                                                       │
│  [Enable 2FA]                                                        │
│                                                                       │
│  ──────────────────────────────────────────────────────────────     │
│                                                                       │
│  Active Sessions                                                     │
│  ──────────────────────────────────────────────────────────────     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ 💻 Chrome on Mac          Current session          Active   │   │
│  │    San Francisco, CA      2 hours ago                        │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ 📱 Safari on iPhone      Jul 1, 2026              Active    │   │
│  │    San Francisco, CA                                   [Revoke] │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  [Sign out all other sessions]                                       │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### Change Password Modal

```
┌─────────────────────────────────────────────────────────────────────┐
│  Change Password                                                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Current Password                                                    │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ [                                                         ] │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  New Password                                                        │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ [                                                         ] │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  Requirements: 8+ characters, uppercase, number, symbol              │
│                                                                       │
│  Confirm New Password                                                │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ [                                                         ] │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  [Cancel]                                    [Update Password]      │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Notification Settings

### Notifications Tab

```
┌─────────────────────────────────────────────────────────────────────┐
│  Notification Preferences                                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Email Notifications                                                 │
│  ──────────────────────────────────────────────────────────────     │
│                                                                       │
│  General                                                            │
│  [✓] Product updates and announcements                              │
│  [✓] Security alerts                                                │
│  [✓] Billing notifications                                          │
│                                                                       │
│  Investment Alerts                                                  │
│  [✓] Signals for watched companies                                  │
│  [✓] Score changes                                                  │
│  [✓] Funding announcements                                          │
│  [ ] Weekly digest                                                   │
│  [ ] Monthly newsletter                                              │
│                                                                       │
│  Frequency: [Daily digest at 8:00 AM ▼]                             │
│                                                                       │
│  Delivery Email: jane@company.com                                   │
│  [Change]                                                            │
│                                                                       │
│  ──────────────────────────────────────────────────────────────     │
│                                                                       │
│  In-App Notifications                                                │
│  ──────────────────────────────────────────────────────────────     │
│                                                                       │
│  [✓] New signals for my watchlists                                  │
│  [✓] Analysis complete                                              │
│  [✓] Report ready                                                    │
│  [ ] Team activity                                                  │
│                                                                       │
│                           [Save Preferences]                        │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Billing Settings

### Billing Tab

```
┌─────────────────────────────────────────────────────────────────────┐
│  Subscription & Billing                                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Current Plan: Pro                                                   │
│  ──────────────────────────────────────────────────────────────     │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Pro Plan                          [$99/month]               │   │
│  │  Billed monthly                                                 │   │
│  │  Next billing date: August 2, 2026                           │   │
│  │                                                                 │   │
│  │  ✓ Unlimited searches                                         │   │
│  │  ✓ 100 AI analyses/month                                      │   │
│  │  ✓ 10 watchlists                                              │   │
│  │  ✓ All alert types                                            │   │
│  │  ✓ Report generation                                          │   │
│  │                                                                 │   │
│  │  [Upgrade to Enterprise]      [Cancel Subscription]          │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  Payment Method                                                      │
│  ──────────────────────────────────────────────────────────────     │
│  Visa ending in 4242                                                 │
│  Expires 12/2027                                                     │
│  [Update payment method]                                             │
│                                                                       │
│  Billing History                                                     │
│  ──────────────────────────────────────────────────────────────     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  July 2, 2026          Pro Plan             $99.00    [PDF] │   │
│  │  June 2, 2026          Pro Plan             $99.00    [PDF] │   │
│  │  May 2, 2026           Pro Plan             $99.00    [PDF] │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  [View all billing history]                                          │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## API Keys

### API Keys Tab

```
┌─────────────────────────────────────────────────────────────────────┐
│  API Keys                                                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Generate API keys to access the platform programmatically.          │
│  [Documentation ↗]                                                   │
│                                                                       │
│  Your API Keys                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  prod_abc123...                    Created Jul 1, 2026       │   │
│  │  Full Access                        Last used: 2 hours ago   │   │
│  │                                      [Regenerate] [Delete]  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  test_xyz789...                    Created Jun 15, 2026     │   │
│  │  Read Only                        Last used: 5 days ago     │   │
│  │                                      [Regenerate] [Delete]  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  [Generate New Key]                                                   │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### Create API Key Modal

```
┌─────────────────────────────────────────────────────────────────────┐
│  Generate API Key                                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Key Name                                                            │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ [My Analytics Integration                                  ] │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  Permissions                                                         │
│  (○) Full Access                                                     │
│  (•) Read Only                                                       │
│  ( ) Custom permissions                                              │
│      [✓] Companies (read)                                            │
│      [✓] Analyses (read)                                            │
│      [ ] Analyses (write)                                           │
│      [ ] Reports (write)                                             │
│                                                                       │
│  Expires                                                             │
│  [Never ▼]                                                           │
│                                                                       │
│  ⚠️ Save this key securely. It won't be shown again.               │
│                                                                       │
│  [Cancel]                                    [Generate Key]         │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Privacy & GDPR

### Privacy Tab

```
┌─────────────────────────────────────────────────────────────────────┐
│  Privacy & Data                                                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Data Export                                                         │
│  ──────────────────────────────────────────────────────────────     │
│  Download a copy of all your data in JSON format.                   │
│                                                                       │
│  [Request Data Export]                                               │
│  You will receive an email when ready (usually within 24 hours).   │
│                                                                       │
│  ──────────────────────────────────────────────────────────────     │
│                                                                       │
│  Activity History                                                    │
│  ──────────────────────────────────────────────────────────────     │
│  View and manage your activity history.                             │
│                                                                       │
│  [Manage Activity History]                                           │
│                                                                       │
│  ──────────────────────────────────────────────────────────────     │
│                                                                       │
│  Connected Accounts                                                  │
│  ──────────────────────────────────────────────────────────────     │
│  Google (connected Jan 15, 2026)              [Disconnect]          │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Delete Account

### Danger Zone

```
┌─────────────────────────────────────────────────────────────────────┐
│  ⚠️ Danger Zone                                                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Delete Account                                                      │
│  ──────────────────────────────────────────────────────────────     │
│  Once you delete your account, there is no going back.              │
│  This will:                                                          │
│  • Permanently delete all your data                                 │
│  • Remove you from all watchlists                                   │
│  • Cancel your subscription                                         │
│  • Delete all generated reports                                      │
│                                                                       │
│  [Delete Account]                                                    │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### Delete Account Confirmation

```
┌─────────────────────────────────────────────────────────────────────┐
│  Delete Account?                                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Type DELETE to confirm                                              │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ [DELETE                                                    ] │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  To verify, type "DELETE" above.                                     │
│                                                                       │
│  [Cancel]                             [Permanently Delete Account]   │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Cross-References

| Document | Topic |
|----------|-------|
| [04-authentication.md](./04-authentication.md) | Security details |
| [22-security.md](./22-security.md) | Security policies |
| [21-error-handling.md](./21-error-handling.md) | Error states |

---

## Version

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | July 2, 2026 | Initial settings spec |

---

*Part of the Opportunity Intelligence Platform PRD*
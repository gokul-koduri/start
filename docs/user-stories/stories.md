# User Stories

## Format

Every user story follows:
```
As a [persona]
I want [goal]
So that [benefit]
```

With:
- Acceptance Criteria (Given/When/Then)
- Test Cases
- Priority (P0/P1/P2/P3)
- Story Points (1-13)

---

## Story US-001: Score a Startup

**As an** investor
**I want to** see a composite opportunity score for any startup
**So that** I can quickly identify high-potential revival opportunities

### Acceptance Criteria
- Given a startup name, the system returns a score between 0-100
- The score is based on at least 3 signal sources
- Score attribution is included (which signals contributed)
- Score computation takes <2 seconds

### Test Cases
1. Score returns valid range (0-100)
2. Score with no signals returns 0
3. Score with high signals returns >70
4. Score handles special characters in name
5. Score handles empty name gracefully

**Priority**: P0 | **Story Points**: 5

---

## Story US-002: Chat with AI About Failures

**As an** analyst
**I want to** ask questions about startup failure patterns
**So that** I can understand risks before investing

### Acceptance Criteria
- Chat responds in <10 seconds
- Responses reference actual data in the database
- Chat maintains context within a session
- Rate limited to 5 messages/minute for free users

**Priority**: P0 | **Story Points**: 3

---

## Story US-003: Search Startups and Signals

**As a** researcher
**I want to** search across all startups, news, and signals
**So that** I can find relevant information quickly

### Acceptance Criteria
- Search returns results in <500ms
- Supports semantic + keyword search
- Results are paginated (20 per page)
- Empty results show helpful suggestions

**Priority**: P0 | **Story Points**: 3

---

## Story US-004: Register and Login

**As a** user
**I want to** create an account and log in
**So that** I can save my watchlists and preferences

### Acceptance Criteria
- Registration requires email + password (8+ chars)
- Passwords are bcrypt hashed (12 rounds)
- JWT token returned on login (24hr expiry)
- Failed logins rate limited (5 per 15 min)

**Priority**: P1 | **Story Points**: 5

---

## Story US-005: Track Startups on Watchlist

**As an** investor
**I want to** add startups to my watchlist
**So that** I get notified when scores change significantly

### Acceptance Criteria
- Can add/remove startups from watchlist
- Can set alert threshold per item
- Get notified when score changes by threshold
- Watchlist persists across sessions

**Priority**: P1 | **Story Points**: 3

---

*See USE_CASES.md for 10 complete use cases with dollar-value outcomes.*

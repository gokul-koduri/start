# 🔄 Feedback-Driven Development — Listen, Learn, Adjust, Show

> "Your first user is your most honest teacher.
>  Ship. Listen. Adjust. Repeat."

---

## The Brutal Truth

```
FEEDBACK AUDIT (June 5, 2026):

  COLLECTION MECHANISMS:
  ❌ No feedback API endpoint
  ❌ No feedback table in database
  ❌ No user rating on scores (no thumbs up/down)
  ❌ No search query logging (searches are stateless)
  ❌ No chat history persistence (in-memory only)
  ❌ No analytics tracking (no Google Analytics)
  ❌ No error tracking (no Sentry)
  ❌ No user survey form
  ❌ No feature request board
  ❌ No NPS score system

  PROGRESS VISIBILITY:
  ✅ PROGRESS.yaml (internal, not user-visible)
  ✅ README badges
  ❌ No public progress page
  ❌ No changelog visible to users
  ❌ No public roadmap

  FEEDBACK → AGENTS:
  ❌ No pipeline from user behavior → agent priorities
  ❌ Orchestrator reads static config, not live data
  ❌ No demand-driven agent scheduling

  CURRENT STATE:
  699 tests, 76 tables, 34 endpoints —
  and ZERO ways to hear from a single user.

  THIS DOCUMENT FIXES ALL OF THAT.
```

---

## Part 1: Feedback Collection — Build the Ears

---

### 1.1 What Feedback We Need

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  FEEDBACK TYPE         WHAT IT TELLS US          COLLECTION METHOD   │
│  ────────────────────────────────────────────────────────────────    │
│                                                                      │
│  Search queries        What users want to find     Query log table   │
│  Chat questions        What users want to know     Chat log table    │
│  Score feedback        Is our scoring accurate?    Thumbs up/down    │
│  Feature requests      What to build next          Feedback form     │
│  Bug reports           What's broken               Error tracker     │
│  Page analytics        Where users go, how long    Plausible/Umami   │
│  Return visits         Is the product sticky?      Analytics         │
│  Signup interest       Will users pay?             Waitlist counter  │
│                                                                      │
│  PRIORITY ORDER:                                                     │
│  1. Search queries → cheapest signal, most data                     │
│  2. Chat questions → deepest signal, most insight                   │
│  3. Score feedback → validates core product                         │
│  4. Analytics → measures overall engagement                         │
│  5. Feature requests → shapes roadmap                              │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 1.2 Feedback Database Schema

```sql
-- ADD TO db/schema.py (4 new tables)

-- 1. Search Query Log — what users search for
CREATE TABLE IF NOT EXISTS query_log (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    query           VARCHAR(500) NOT NULL,
    search_mode     VARCHAR(20) DEFAULT 'hybrid',
    results_count   INT DEFAULT 0,
    response_ms     INT DEFAULT 0,
    source          VARCHAR(50) DEFAULT 'web',    -- web, api, chat
    ip_hash         VARCHAR(64) DEFAULT NULL,      -- SHA256 of IP (privacy)
    user_agent      VARCHAR(200) DEFAULT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_query_created (query(100), created_at),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. Chat Conversation Log — what users ask
CREATE TABLE IF NOT EXISTS chat_log (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    session_id      VARCHAR(36) DEFAULT NULL,      -- UUID per conversation
    user_message    TEXT NOT NULL,
    ai_response     TEXT,
    model_used      VARCHAR(50) DEFAULT 'llama3:8b',
    response_ms     INT DEFAULT 0,
    sources_used    TEXT,                           -- JSON: which tables queried
    ip_hash         VARCHAR(64) DEFAULT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_session (session_id),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. Score Feedback — is our scoring useful?
CREATE TABLE IF NOT EXISTS score_feedback (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    entity_name     VARCHAR(200) NOT NULL,
    score_given     FLOAT,                          -- Our score
    rating          TINYINT NOT NULL,               -- 1=bad, 2=poor, 3=ok, 4=good, 5=great
    user_score      INT DEFAULT NULL,               -- What user would score it
    comment         TEXT DEFAULT NULL,
    ip_hash         VARCHAR(64) DEFAULT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_entity (entity_name),
    INDEX idx_rating (rating),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. Feature Requests — what to build next
CREATE TABLE IF NOT EXISTS feature_requests (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    feature         VARCHAR(500) NOT NULL,
    category        VARCHAR(50) DEFAULT 'general',  -- search, score, chat, alerts, etc.
    source          VARCHAR(50) DEFAULT 'feedback',  -- feedback, email, twitter, hn
    upvotes         INT DEFAULT 1,
    status          VARCHAR(20) DEFAULT 'open',      -- open, planned, building, done, wontdo
    ip_hash         VARCHAR(64) DEFAULT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_upvotes (upvotes DESC),
    INDEX idx_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 1.3 Feedback API Endpoints

```python
# ADD TO api_server.py (5 new endpoints)

# ─── FEEDBACK ENDPOINTS ───────────────────────────────────────────

@app.post("/api/feedback/score")
def submit_score_feedback(request_body: dict):
    """Submit feedback on a startup score.

    Request body:
        {"entity_name": "Fisker", "rating": 4, "user_score": 55, "comment": "Pretty accurate"}
    """
    entity_name = request_body.get("entity_name", "")
    rating = request_body.get("rating", 0)
    user_score = request_body.get("user_score")
    comment = request_body.get("comment", "")
    ip_hash = _hash_ip(request)  # Privacy: hash the IP

    if not entity_name or rating not in (1, 2, 3, 4, 5):
        raise HTTPException(400, "entity_name and rating (1-5) required")

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Get our score for this entity
            cursor.execute(
                "SELECT composite_score FROM opportunity_scores "
                "WHERE entity_name = %s ORDER BY scored_at DESC LIMIT 1",
                (entity_name,)
            )
            row = cursor.fetchone()
            score_given = row["composite_score"] if row else None

            cursor.execute(
                "INSERT INTO score_feedback "
                "(entity_name, score_given, rating, user_score, comment, ip_hash) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (entity_name, score_given, rating, user_score, comment, ip_hash)
            )
        conn.commit()
        return {"status": "recorded", "entity_name": entity_name}
    finally:
        conn.close()


@app.post("/api/feedback/feature")
def submit_feature_request(request_body: dict):
    """Submit a feature request.

    Request body:
        {"feature": "Add Slack alerts for score changes", "category": "alerts"}
    """
    feature = request_body.get("feature", "").strip()
    category = request_body.get("category", "general")
    ip_hash = _hash_ip(request)

    if not feature or len(feature) < 5:
        raise HTTPException(400, "feature description required (min 5 chars)")

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Check if similar feature already requested → upvote it
            cursor.execute(
                "SELECT id, upvotes FROM feature_requests "
                "WHERE feature LIKE %s AND status = 'open' LIMIT 1",
                (f"%{feature[:50]}%",)
            )
            existing = cursor.fetchone()

            if existing:
                cursor.execute(
                    "UPDATE feature_requests SET upvotes = upvotes + 1 WHERE id = %s",
                    (existing["id"],)
                )
                return {"status": "upvoted", "id": existing["id"],
                        "upvotes": existing["upvotes"] + 1}
            else:
                cursor.execute(
                    "INSERT INTO feature_requests (feature, category, ip_hash) "
                    "VALUES (%s, %s, %s)",
                    (feature, category, ip_hash)
                )
                return {"status": "created", "id": cursor.lastrowid}
        conn.commit()
    finally:
        conn.close()


@app.get("/api/feedback/feature-requests")
def list_feature_requests(status: str = "open", limit: int = 20):
    """List feature requests, sorted by upvotes."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, feature, category, upvotes, status, created_at "
                "FROM feature_requests WHERE status = %s "
                "ORDER BY upvotes DESC LIMIT %s",
                (status, limit)
            )
            return {"requests": cursor.fetchall()}
    finally:
        conn.close()


@app.get("/api/feedback/score-stats")
def score_feedback_stats():
    """Aggregate score feedback — how accurate are our scores?"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT
                    COUNT(*) as total_feedback,
                    AVG(rating) as avg_rating,
                    SUM(rating >= 4) as positive,
                    SUM(rating <= 2) as negative,
                    AVG(ABS(score_given - user_score)) as avg_score_diff
                FROM score_feedback
                WHERE created_at > DATE_SUB(NOW(), INTERVAL 30 DAY)
            """)
            stats = cursor.fetchone()
            return {
                "total_feedback": stats["total_feedback"] or 0,
                "avg_rating": round(stats["avg_rating"] or 0, 2),
                "positive_pct": round(
                    (stats["positive"] or 0) / max(stats["total_feedback"], 1) * 100, 1
                ),
                "negative_pct": round(
                    (stats["negative"] or 0) / max(stats["total_feedback"], 1) * 100, 1
                ),
                "avg_score_diff": round(stats["avg_score_diff"] or 0, 1)
            }
    finally:
        conn.close()


@app.get("/api/feedback/dashboard")
def feedback_dashboard():
    """Feedback dashboard data — what users are telling us."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Top searches (last 7 days)
            cursor.execute("""
                SELECT query, COUNT(*) as count, AVG(results_count) as avg_results
                FROM query_log
                WHERE created_at > DATE_SUB(NOW(), INTERVAL 7 DAY)
                GROUP BY query ORDER BY count DESC LIMIT 20
            """)
            top_searches = cursor.fetchall()

            # Top chat questions (last 7 days)
            cursor.execute("""
                SELECT user_message, COUNT(*) as count
                FROM chat_log
                WHERE created_at > DATE_SUB(NOW(), INTERVAL 7 DAY)
                GROUP BY user_message ORDER BY count DESC LIMIT 20
            """)
            top_questions = cursor.fetchall()

            # Score accuracy
            cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    AVG(rating) as avg_rating,
                    AVG(ABS(score_given - user_score)) as avg_diff
                FROM score_feedback
            """)
            score_stats = cursor.fetchone()

            # Feature requests
            cursor.execute("""
                SELECT feature, category, upvotes, status
                FROM feature_requests
                WHERE status IN ('open', 'planned')
                ORDER BY upvotes DESC LIMIT 10
            """)
            features = cursor.fetchall()

            # Daily active users (by unique ip_hash)
            cursor.execute("""
                SELECT DATE(created_at) as date,
                       COUNT(DISTINCT ip_hash) as unique_users,
                       COUNT(*) as total_queries
                FROM query_log
                WHERE created_at > DATE_SUB(NOW(), INTERVAL 14 DAY)
                GROUP BY DATE(created_at) ORDER BY date
            """)
            daily_users = cursor.fetchall()

            return {
                "top_searches": top_searches,
                "top_questions": top_questions,
                "score_stats": score_stats,
                "feature_requests": features,
                "daily_users": daily_users
            }
    finally:
        conn.close()


def _hash_ip(request):
    """Hash IP for privacy — we never store raw IPs."""
    import hashlib
    ip = request.client.host if request.client else "unknown"
    return hashlib.sha256(f"oip-{ip}".encode()).hexdigest()[:32]
```

### 1.4 Instrument Existing Endpoints (Log Every Query)

```python
# MODIFY existing endpoints in api_server.py to log queries

# Add to unified_search():
@app.get("/api/search")
def unified_search(q: str = Query(...), ...):
    start_time = time.time()
    # ... existing search logic ...
    response_ms = int((time.time() - start_time) * 1000)

    # LOG THE QUERY (async, non-blocking)
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO query_log (query, search_mode, results_count, "
                "response_ms, ip_hash, user_agent) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (q, mode, len(results), response_ms,
                 _hash_ip(request),
                 request.headers.get("user-agent", "")[:200])
            )
        conn.commit()
        conn.close()
    except Exception:
        pass  # Never let logging break search

    return results


# Add to chat():
@app.post("/api/chat")
async def chat(request_body: dict):
    start_time = time.time()
    session_id = request_body.get("session_id", str(uuid.uuid4()))
    user_message = request_body.get("query", request_body.get("message", ""))
    # ... existing chat logic ...
    response_ms = int((time.time() - start_time) * 1000)

    # LOG THE CONVERSATION
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO chat_log (session_id, user_message, ai_response, "
                "model_used, response_ms, ip_hash) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (session_id, user_message, response[:2000],
                 "llama3:8b", response_ms, _hash_ip(request))
            )
        conn.commit()
        conn.close()
    except Exception:
        pass  # Never let logging break chat

    return {"response": response, "session_id": session_id}
```

### 1.5 Dashboard Feedback Widget (Frontend)

```html
<!-- ADD TO site/index.html — Score feedback after each result -->

<div id="scoreFeedback" style="display:none;">
  <p style="font-size:14px;color:#666;margin-top:8px;">
    Was this score helpful?
    <button onclick="rateScore(5)" style="background:#22c55e;color:white;
      border:none;border-radius:4px;padding:4px 8px;cursor:pointer;font-size:16px;">
      👍</button>
    <button onclick="rateScore(2)" style="background:#ef4444;color:white;
      border:none;border-radius:4px;padding:4px 8px;cursor:pointer;font-size:16px;">
      👎</button>
    <button onclick="showFeatureForm()" style="background:#3b82f6;color:white;
      border:none;border-radius:4px;padding:4px 8px;cursor:pointer;font-size:13px;">
      💡 Request Feature</button>
  </p>
</div>

<!-- Feature request form (modal) -->
<div id="featureModal" style="display:none;position:fixed;top:0;left:0;width:100%;
  height:100%;background:rgba(0,0,0,0.5);z-index:9999;">
  <div style="background:white;max-width:500px;margin:100px auto;padding:24px;
    border-radius:8px;">
    <h3>💡 What should we build next?</h3>
    <textarea id="featureText" rows="3" style="width:100%;padding:8px;
      border:1px solid #ccc;border-radius:4px;"
      placeholder="e.g., 'Alert me when a startup score changes'"></textarea>
    <select id="featureCategory" style="width:100%;padding:8px;margin-top:8px;
      border:1px solid #ccc;border-radius:4px;">
      <option value="general">General</option>
      <option value="search">Search</option>
      <option value="score">Scoring</option>
      <option value="chat">AI Chat</option>
      <option value="alerts">Alerts</option>
      <option value="data">Data</option>
      <option value="dashboard">Dashboard</option>
    </select>
    <div style="margin-top:12px;text-align:right;">
      <button onclick="submitFeature()" style="background:#3b82f6;color:white;
        border:none;padding:8px 16px;border-radius:4px;cursor:pointer;">
        Submit</button>
      <button onclick="document.getElementById('featureModal').style.display='none'"
        style="background:#ccc;border:none;padding:8px 16px;border-radius:4px;
        cursor:pointer;margin-left:8px;">Cancel</button>
    </div>
  </div>
</div>

<script>
async function rateScore(rating) {
  const entity = document.getElementById('searchResultName')?.textContent || '';
  await fetch('/api/feedback/score', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({entity_name: entity, rating: rating})
  });
  document.getElementById('scoreFeedback').innerHTML =
    '<p style="color:#22c55e;font-size:14px;">✅ Thanks for your feedback!</p>';
}

function showFeatureForm() {
  document.getElementById('featureModal').style.display = 'block';
}

async function submitFeature() {
  const feature = document.getElementById('featureText').value;
  const category = document.getElementById('featureCategory').value;
  await fetch('/api/feedback/feature', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({feature: feature, category: category})
  });
  document.getElementById('featureModal').style.display = 'none';
  document.getElementById('featureText').value = '';
  alert('Thank you! We\'ll prioritize this based on demand.');
}
</script>
```

---

## Part 2: Adjusting Priority Based on Real Needs

---

### 2.1 The Feedback → Priority Pipeline

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  HOW USER FEEDBACK CHANGES PRIORITIES:                               │
│                                                                      │
│  USER BEHAVIOR          →  WHAT WE LEARN     →  WHAT WE ADJUST      │
│  ──────────────────────────────────────────────────────────────      │
│                                                                      │
│  500 people search       "EV startups" is        →  Build EV-      │
│  for EV startups         the #1 topic             specific scoring  │
│                                                                      │
│  200 people ask          Users want             →  Build failure    │
│  "Why did X fail?"       failure analysis         prediction agent  │
│                                                                      │
│  50 feature requests     Alerts are the       →  Move alerts from  │
│  for alerts              #1 request              P1 to P0           │
│                                                                      │
│  Score feedback          Score is wrong        →  Fix scoring       │
│  avg rating = 2.1/5      for most startups       algorithm first    │
│                                                                      │
│  80% of users search     Score is the       →  Polish score UX,    │
│  and leave immediately   only thing used      add more data sources │
│                                                                      │
│  Users search their      Founders are a     →  Add founder-        │
│  own company name        user persona          specific features   │
│                                                                      │
│  Nobody uses chat        Chat is not a      →  Deprioritize chat   │
│  (< 5% of visitors)      priority              improvements        │
│                                                                      │
│  Users ask "how much?"   Users will pay!    →  Build Pro tier      │
│  (50+ occurrences)        Revenue validated     immediately         │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.2 The Weekly Priority Review Process

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  EVERY MONDAY: FEEDBACK REVIEW (30 minutes)                         │
│                                                                      │
│  STEP 1: PULL THE DATA (5 min)                                      │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  curl http://localhost:8000/api/feedback/dashboard             │  │
│  │                                                                │  │
│  │  Review:                                                       │  │
│  │  • Top 20 searches (what do users want?)                       │  │
│  │  • Top 20 chat questions (what do users ask?)                  │  │
│  │  • Score accuracy stats (is our core product working?)         │  │
│  │  • Feature requests by upvotes (what to build?)                │  │
│  │  • Daily active users (is engagement growing?)                 │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  STEP 2: SCORE EACH SIGNAL (10 min)                                 │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                                                                │  │
│  │  Signal              Volume   Impact   Score   Action          │  │
│  │  ─────────────────────────────────────────────────────────     │  │
│  │  "EV startup" search  200/mo   HIGH     9/10   Build EV focus │  │
│  │  "alerts" request      50/mo   HIGH     8/10   Move to P0     │  │
│  │  Score rating avg 2.1  30 fb   CRITICAL 10/10  Fix scoring    │  │
│  │  "how much" in chat    20/mo   HIGH     8/10   Build Pro tier │  │
│  │  "export CSV" request  15/mo   MEDIUM   6/10   Plan for V1    │  │
│  │  Nobody uses chat      LOW     MEDIUM   4/10   Deprioritize   │  │
│  │                                                                │  │
│  │  Score = Volume (0-3) + Impact (0-3) + Alignment (0-3)        │  │
│  │  + Urgency (0-1)                                               │  │
│  │                                                                │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  STEP 3: REORDER THE BACKLOG (10 min)                               │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                                                                │  │
│  │  BEFORE (assumed priorities):                                  │  │
│  │  P0: Scheduler, Alert Consumer, Score Push                   │  │
│  │  P1: Auth, Watchlists, PDF Export                             │  │
│  │  P2: CRM, Mobile, HuggingFace MCP                            │  │
│  │                                                                │  │
│  │  AFTER (based on feedback):                                    │  │
│  │  P0: Fix scoring accuracy (rating 2.1/5 = broken!)            │  │
│  │  P0: Build alerts (50 requests = strong demand)               │  │
│  │  P1: Scheduler, Score Push                                    │  │
│  │  P1: Pro tier (20 "how much?" questions = revenue)            │  │
│  │  P2: Auth, Watchlists, PDF Export                             │  │
│  │  P3: CRM, Mobile, HuggingFace MCP                            │  │
│  │                                                                │  │
│  │  NOTE: Scoring accuracy jumped from P2 to P0 because          │  │
│  │        real users told us it's broken. That's the power        │  │
│  │        of feedback-driven development.                         │  │
│  │                                                                │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  STEP 4: UPDATE THE PLAN (5 min)                                    │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  • Update GOALS_AND_PRIORITIES.md with new priority order      │  │
│  │  • Update PROGRESS.yaml with feedback metrics                  │  │
│  │  • Post the change to GitHub Discussions                       │  │
│  │  • Add new feature requests to the backlog                     │  │
│  │  • Close completed feature requests                            │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.3 The Priority Adjustment Rules

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  RULE 1: SCORE ACCURACY IS ALWAYS P0                                │
│  If avg score rating < 3.0/5 → stop everything, fix scoring.       │
│  A broken score means a broken product.                              │
│                                                                      │
│  RULE 2: FEATURE WITH 50+ REQUESTS BECOMES P0                       │
│  If a feature gets 50+ unique requests → build it next.             │
│  This is the market telling you what it wants.                       │
│                                                                      │
│  RULE 3: FEATURE WITH 0 REQUESTS GETS DEPRIORITIZED                 │
│  If a planned feature has 0 user mentions in 30 days → move to P3. │
│  No demand = don't build.                                            │
│                                                                      │
│  RULE 4: REVENUE SIGNALS GET PRIORITY                                │
│  If 20+ users ask "how much?" or "is there a paid version?" →      │
│  build the Pro tier immediately. Revenue validates everything.      │
│                                                                      │
│  RULE 5: CHAT QUERY PATTERNS REVEAL USER PERSONAS                   │
│  Cluster the top 100 chat questions. Each cluster = a persona.      │
│  Build features for the largest cluster first.                      │
│                                                                      │
│  RULE 6: WEEKLY REVIEW, NO EXCEPTIONS                               │
│  Every Monday, review feedback dashboard.                            │
│  Adjust priorities. Update the plan. Share with community.          │
│  This is not optional. This IS the development process.             │
│                                                                      │
│  RULE 7: NEVER IGNORE NEGATIVE FEEDBACK                             │
│  Negative feedback (thumbs down, low rating) is the most            │
│  valuable signal. It tells you exactly what's broken.               │
│  Fix it before building anything new.                                │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Part 3: Show Progress Regularly

---

### 3.1 The Progress Dashboard (Public)

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  PUBLIC PROGRESS PAGE: /progress                                     │
│  (Add to site/progress.html or site/index.html section)             │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │                                                              │    │
│  │  🚀 OPPORTUNITY INTELLIGENCE PLATFORM                       │    │
│  │                                                              │    │
│  │  BUILD PROGRESS                                              │    │
│  │  ████████████████████████████████░░░░░░  83% Complete       │    │
│  │                                                              │    │
│  │  ✅ Phase 1: Foundation          8/8 sessions               │    │
│  │  ✅ Phase 2: Intelligence       10/10 sessions               │    │
│  │  ✅ Phase 3: Scale              12/12 sessions               │    │
│  │  ✅ Phase 4: Deep Collection    15/15 sessions               │    │
│  │  ✅ Phase 5: Advanced Intel     18/18 sessions               │    │
│  │  🔄 Phase 6: Operations          0/16 sessions               │    │
│  │                                                              │    │
│  │  STATS                                                       │    │
│  │  ┌─────────┬─────────┬──────────┬─────────┬──────────┐      │    │
│  │  │ 55      │ 26      │ 76       │ 699     │ 34       │      │    │
│  │  │ agents  │ sources │ tables   │ tests   │ endpoints│      │    │
│  │  └─────────┴─────────┴──────────┴─────────┴──────────┘      │    │
│  │                                                              │    │
│  │  WHAT WE'RE WORKING ON THIS WEEK                             │    │
│  │  ┌────────────────────────────────────────────────────────┐  │    │
│  │  │ 🔄 Building: Collector Scheduler (24/7 data collection)│  │    │
│  │  │ 🔄 Building: Alert System (Slack + Email notifications)│  │    │
│  │  │ ✅ Done: Score a Startup endpoint                       │  │    │
│  │  │ ✅ Done: AI Chat endpoint                               │  │    │
│  │  │ ✅ Done: Failure Pattern Browser                        │  │    │
│  │  └────────────────────────────────────────────────────────┘  │    │
│  │                                                              │    │
│  │  WHAT'S COMING NEXT                                          │    │
│  │  ┌────────────────────────────────────────────────────────┐  │    │
│  │  │ Week 3: Auth system + API keys                         │  │    │
│  │  │ Week 4: Watchlists + Opportunity Feed                  │  │    │
│  │  │ Week 5: Pro tier ($49/mo)                              │  │    │
│  │  │ Week 6: CRM integration                                │  │    │
│  │  └────────────────────────────────────────────────────────┘  │    │
│  │                                                              │    │
│  │  COMMUNITY FEEDBACK                                          │    │
│  │  ┌────────────────────────────────────────────────────────┐  │    │
│  │  │ #1 Request: "Alert me when scores change"  (50 votes)  │  │    │
│  │  │ #2 Request: "Export data to CSV"           (32 votes)  │  │    │
│  │  │ #3 Request: "Mobile-friendly dashboard"    (28 votes)  │  │    │
│  │  │ [Submit your request] 💡                                 │  │    │
│  │  └────────────────────────────────────────────────────────┘  │    │
│  │                                                              │    │
│  │  Last updated: June 10, 2026                                 │    │
│  │                                                              │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.2 The Changelog (CHANGELOG.md)

```markdown
# Changelog

All notable changes to the Opportunity Intelligence Platform.

## [Unreleased]
### Added
- Score feedback API (POST /api/feedback/score)
- Feature request API (POST /api/feedback/feature)
- Query logging (search and chat queries recorded)
- Feedback dashboard API (GET /api/feedback/dashboard)

### Changed
- Score calculation now shows confidence level
- Search results include response time in header

## [0.1.0-mvp] - 2026-06-12
### Added
- Instant startup scoring (0-100) with factor attribution
- AI chat for startup intelligence questions
- Failure pattern browser (50+ startups)
- Knowledge graph visualization
- Docker Compose deployment (11 services)
- 34 API endpoints
- 699 tests (98.3% pass rate)

## [0.0.1-dev] - 2026-05-25
### Added
- Initial project structure
- MySQL schema (76 tables)
- FastAPI server
- Ollama integration
- First 5 collectors
```

### 3.3 The Progress API (Automated)

```python
# ADD TO api_server.py

@app.get("/api/progress")
def project_progress():
    """Public API — project progress for status page."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Count entities
            cursor.execute("SELECT COUNT(*) as c FROM failed_startups")
            failed = cursor.fetchone()["c"]
            cursor.execute("SELECT COUNT(*) as c FROM opportunity_scores")
            scored = cursor.fetchone()["c"]
            cursor.execute("SELECT COUNT(*) as c FROM raw_signals")
            signals = cursor.fetchone()["c"]

            # Recent activity
            cursor.execute("""
                SELECT DATE(created_at) as date, COUNT(*) as count
                FROM raw_signals
                WHERE created_at > DATE_SUB(NOW(), INTERVAL 7 DAY)
                GROUP BY DATE(created_at) ORDER BY date DESC LIMIT 7
            """)
            recent_signals = cursor.fetchall()

            # Feedback summary
            cursor.execute("""
                SELECT COUNT(*) as total_queries FROM query_log
                WHERE created_at > DATE_SUB(NOW(), INTERVAL 24 HOUR)
            """)
            queries_today = cursor.fetchone()["total_queries"]

            cursor.execute("""
                SELECT COUNT(DISTINCT ip_hash) as c FROM query_log
                WHERE created_at > DATE_SUB(NOW(), INTERVAL 24 HOUR)
            """)
            users_today = cursor.fetchone()["c"]

            return {
                "data": {
                    "failed_startups": failed,
                    "scored_entities": scored,
                    "total_signals": signals,
                    "recent_signals": recent_signals,
                },
                "engagement": {
                    "queries_today": queries_today,
                    "users_today": users_today,
                },
                "development": {
                    "phases_complete": 5,
                    "phases_total": 6,
                    "completion_pct": 83,
                    "agents": 55,
                    "collectors": 26,
                    "tests": 699,
                    "endpoints": 34,
                },
                "version": "0.1.0-dev",
                "last_updated": datetime.now().isoformat(),
            }
    finally:
        conn.close()
```

### 3.4 Weekly Progress Report Template

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  WEEKLY PROGRESS REPORT — Week of [DATE]                            │
│                                                                      │
│  📊 METRICS                                                          │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │  Metric              This Week   Last Week   Change          │    │
│  │  ────────────────────────────────────────────────────────    │    │
│  │  Unique visitors         523         312       +67%          │    │
│  │  Search queries        1,847       1,102       +67%          │    │
│  │  Chat questions          412         203      +103%          │    │
│  │  Score feedback          89          45        +98%          │    │
│  │  Avg score rating       3.8         3.2       +0.6          │    │
│  │  Feature requests        23          12        +92%          │    │
│  │  Return users (7-day)   12%          8%       +4pts         │    │
│  └──────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  🔨 WHAT WE BUILT THIS WEEK                                         │
│  • Added score feedback (thumbs up/down on every score)             │
│  • Added feature request form (💡 button on dashboard)              │
│  • Added query logging (search + chat)                               │
│  • Fixed 12 failing tests (test_semantic_search.py)                 │
│  • Added database backup (mysqldump + S3)                           │
│                                                                      │
│  📈 TOP SEARCHES THIS WEEK                                          │
│  1. "Tesla" (142 queries)                                           │
│  2. "Rivian" (98 queries)                                           │
│  3. "AI startups" (87 queries)                                      │
│  4. "EV companies" (76 queries)                                     │
│  5. "Byju's" (65 queries)                                           │
│                                                                      │
│  💬 TOP CHAT QUESTIONS                                               │
│  1. "Why did Fisker fail?" (34 times)                               │
│  2. "Top AI startup failures?" (28 times)                           │
│  3. "Should I invest in Rivian?" (23 times)                         │
│  4. "How accurate are the scores?" (19 times)                       │
│  5. "Can I get alerts?" (17 times)                                  │
│                                                                      │
│  🗳️ TOP FEATURE REQUESTS                                            │
│  1. 🔔 Alert on score changes (50 votes) → BUILDING NEXT           │
│  2. 📊 Export to CSV (32 votes) → PLANNED                           │
│  3. 📱 Mobile-friendly (28 votes) → PLANNED                         │
│  4. 🔍 Filter by sector (21 votes) → BUILDING                      │
│  5. 💰 Pro tier (19 votes) → PLANNED                                │
│                                                                      │
│  🎯 NEXT WEEK'S PRIORITIES (adjusted by feedback)                   │
│  P0: Build alert system (top feature request, 50 votes)            │
│  P0: Improve score accuracy (avg rating 3.8, target 4.0+)          │
│  P1: Add sector filter (21 votes, easy to build)                   │
│  P1: Set up Plausible analytics                                     │
│                                                                      │
│  📢 SHARE WITH COMMUNITY                                             │
│  Post this report to:                                               │
│  • GitHub Discussions (weekly update)                                │
│  • Twitter/X thread (#BuildInPublic)                                │
│  • Reddit r/startups (monthly summary)                              │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Part 4: Feedback Done Often — The Feedback Cycle

---

### 4.1 The Build-Measure-Learn Loop

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│              ┌──────────┐                                            │
│              │  BUILD   │                                            │
│              │ (2 weeks)│                                            │
│              └────┬─────┘                                            │
│                   │                                                  │
│                   ▼                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                          │
│  │  LEARN   │◄─┤  MEASURE │◄─┤  SHIP    │                          │
│  │ (adjust  │  │ (1 week) │  │ (deploy) │                          │
│  │ priority)│  │          │  │          │                          │
│  └────┬─────┘  └──────────┘  └──────────┘                          │
│       │                                                             │
│       │  "Users searched EV 200 times → build EV features"         │
│       │  "Score rating 2.1/5 → fix scoring before anything"        │
│       │  "50 alert requests → build alerts next"                    │
│       │                                                             │
│       └─────────────────────────────────────────────────────────►   │
│              (loop back to BUILD with adjusted priorities)           │
│                                                                      │
│  CYCLE TIME:                                                         │
│  MVP:     Build 2 weeks → Measure 2 weeks → Learn → Adjust         │
│  V1+:     Build 1 week  → Measure 1 week  → Learn → Adjust         │
│  Mature:  Build 3 days  → Measure 3 days  → Learn → Adjust         │
│                                                                      │
│  KEY PRINCIPLE:                                                      │
│  Never build for more than 2 weeks without measuring user feedback. │
│  If you're building for a month without shipping, you're guessing.  │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 4.2 Feedback Frequency by Channel

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  CHANNEL              FREQUENCY        WHO REVIEWS      ACTION TIME │
│  ────────────────────────────────────────────────────────────────    │
│                                                                      │
│  Search query log      Real-time       Weekly review     1 week     │
│  (what users search)   (stored in DB)                                │
│                                                                      │
│  Chat query log        Real-time       Weekly review     1 week     │
│  (what users ask)      (stored in DB)                                │
│                                                                      │
│  Score feedback        Real-time       Daily check       1-3 days   │
│  (thumbs up/down)      (stored in DB)                                │
│                                                                      │
│  Feature requests      Real-time       Weekly review     1-2 weeks  │
│  (user submissions)    (stored in DB)                                │
│                                                                      │
│  Bug reports           On occurrence   Same day         1-7 days    │
│  (error tracker)       (auto-logged)                                 │
│                                                                      │
│  Analytics             Daily           Weekly review     1 week     │
│  (page views, etc.)    (Plausible)                                   │
│                                                                      │
│  Social mentions       Daily           Weekly review     1 week     │
│  (HN, Reddit, Twitter) (manual)                                      │
│                                                                      │
│  Email feedback        As received    Same day          1-3 days    │
│  (direct emails)       (manual)                                      │
│                                                                      │
│  Weekly report         Weekly          Public            N/A         │
│  (posted to GitHub)    (Monday)        (transparency)                │
│                                                                      │
│  MONTHLY: Deep analysis of all feedback, persona clustering,        │
│           priority re-ranking, roadmap update.                       │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Part 5: Share Feedback with Agents to Work

---

### 5.1 Feedback-Driven Agent Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  CURRENT: Agents work on static pipeline config                     │
│                                                                      │
│  USER ──► API ──► [no feedback captured] ──► agents (static config) │
│                                                                      │
│  PROPOSED: Agents work on demand-driven priorities                  │
│                                                                      │
│  USER ──► API ──► query_log + chat_log + feedback                   │
│              │                                                       │
│              ▼                                                       │
│         ┌──────────────┐                                             │
│         │  FEEDBACK     │                                            │
│         │  ANALYZER     │  (new agent: FeedbackAnalyzerAgent)        │
│         │              │                                             │
│         │  Reads:      │                                             │
│         │  • query_log │                                             │
│         │  • chat_log  │                                             │
│         │  • score_feed.│                                            │
│         │  • feature_req│                                            │
│         │              │                                             │
│         │  Outputs:    │                                             │
│         │  • priority  │  → Orchestrator reads this                  │
│         │    queue     │  → Agents scheduled by demand                │
│         │  • insights  │  → Shared with community                    │
│         │  • alerts    │  → Triggers urgent fixes                    │
│         └──────┬───────┘                                             │
│                │                                                      │
│                ▼                                                      │
│  ┌──────────────────────────────────────────────────┐                │
│  │  ORCHESTRATOR (modified)                          │                │
│  │                                                   │                │
│  │  Current: reads static config/pipelines           │                │
│  │  Proposed: reads feedback_analyzer output first    │                │
│  │                                                   │                │
│  │  IF feedback says "scoring is broken":            │                │
│  │    → run scoring validation agent first            │                │
│  │    → re-score all entities                         │                │
│  │                                                   │                │
│  │  IF feedback says "EV searches are #1":           │                │
│  │    → run EV-specific collectors more often         │                │
│  │    → prioritize EV entities for scoring            │                │
│  │                                                   │                │
│  │  IF feedback says "alerts requested 50 times":    │                │
│  │    → add alert agents to the pipeline              │                │
│  │                                                   │                │
│  └──────────────────────────────────────────────────┘                │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 5.2 FeedbackAnalyzerAgent (New Agent)

```python
# agents/feedback_analyzer_agent.py (NEW)

"""Feedback Analyzer Agent — turns user behavior into agent priorities.

Reads query_log, chat_log, score_feedback, and feature_requests.
Produces a priority report that the Orchestrator uses to schedule work.
"""

class FeedbackAnalyzerAgent(BaseAgent):
    """Analyze user feedback and generate priority recommendations."""

    def run(self, **kwargs) -> dict:
        conn = get_connection()
        report = {
            "top_searches": self._top_searches(conn),
            "top_questions": self._top_questions(conn),
            "score_accuracy": self._score_accuracy(conn),
            "feature_demand": self._feature_demand(conn),
            "urgent_issues": self._urgent_issues(conn),
            "recommended_actions": [],
        }

        # Generate recommended actions based on feedback
        report["recommended_actions"] = self._generate_actions(report)

        conn.close()
        return report

    def _top_searches(self, conn) -> list[dict]:
        """What are users searching for most?"""
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT LOWER(query) as query, COUNT(*) as count,
                       AVG(results_count) as avg_results
                FROM query_log
                WHERE created_at > DATE_SUB(NOW(), INTERVAL 7 DAY)
                GROUP BY LOWER(query)
                ORDER BY count DESC LIMIT 20
            """)
            searches = cursor.fetchall()

        # Identify underserved searches (high volume, low results)
        for s in searches:
            if s["avg_results"] < 3:
                s["underserved"] = True  # Users want this, we don't have data
        return searches

    def _top_questions(self, conn) -> list[dict]:
        """What are users asking about most?"""
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT user_message, COUNT(*) as count
                FROM chat_log
                WHERE created_at > DATE_SUB(NOW(), INTERVAL 7 DAY)
                GROUP BY user_message
                ORDER BY count DESC LIMIT 20
            """)
            return cursor.fetchall()

    def _score_accuracy(self, conn) -> dict:
        """How accurate are our scores according to users?"""
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) as total,
                       AVG(rating) as avg_rating,
                       SUM(rating >= 4) as positive,
                       SUM(rating <= 2) as negative,
                       AVG(ABS(score_given - user_score)) as avg_diff
                FROM score_feedback
                WHERE created_at > DATE_SUB(NOW(), INTERVAL 30 DAY)
            """)
            return cursor.fetchone()

    def _feature_demand(self, conn) -> list[dict]:
        """What features do users want most?"""
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT feature, category, upvotes, status
                FROM feature_requests
                WHERE status = 'open'
                ORDER BY upvotes DESC LIMIT 10
            """)
            return cursor.fetchall()

    def _urgent_issues(self, conn) -> list[str]:
        """Any issues that need immediate attention?"""
        issues = []
        with conn.cursor() as cursor:
            # Score accuracy dropping?
            cursor.execute("""
                SELECT AVG(rating) as avg FROM score_feedback
                WHERE created_at > DATE_SUB(NOW(), INTERVAL 7 DAY)
            """)
            avg = cursor.fetchone()["avg"]
            if avg and avg < 3.0:
                issues.append(
                    f"CRITICAL: Score rating is {avg:.1f}/5 — users think scores are wrong"
                )

            # Searches returning no results?
            cursor.execute("""
                SELECT COUNT(*) as c FROM query_log
                WHERE results_count = 0
                AND created_at > DATE_SUB(NOW(), INTERVAL 24 HOUR)
            """)
            empty = cursor.fetchone()["c"]
            if empty > 50:
                issues.append(
                    f"HIGH: {empty} searches returned 0 results — data gap"
                )

            # Chat failures?
            cursor.execute("""
                SELECT COUNT(*) as c FROM chat_log
                WHERE ai_response IS NULL
                AND created_at > DATE_SUB(NOW(), INTERVAL 24 HOUR)
            """)
            failed = cursor.fetchone()["c"]
            if failed > 10:
                issues.append(
                    f"HIGH: {failed} chat queries failed — Ollama may be down"
                )

        return issues

    def _generate_actions(self, report: dict) -> list[dict]:
        """Convert feedback into concrete actions."""
        actions = []

        # Action: fix score accuracy
        score = report.get("score_accuracy", {})
        if score.get("avg_rating") and score["avg_rating"] < 3.5:
            actions.append({
                "priority": "P0",
                "action": "fix_scoring",
                "reason": f"Score rating is {score['avg_rating']:.1f}/5",
                "agent": "opportunity_scorer",
            })

        # Action: add data for underserved searches
        for search in report.get("top_searches", []):
            if search.get("underserved"):
                actions.append({
                    "priority": "P1",
                    "action": "add_data_source",
                    "reason": f"'{search['query']}' has {search['avg_results']:.0f} results but {search['count']} searches",
                    "query": search["query"],
                })

        # Action: build top feature requests
        for feature in report.get("feature_demand", [])[:3]:
            if feature["upvotes"] >= 20:
                actions.append({
                    "priority": "P1",
                    "action": "build_feature",
                    "reason": f"{feature['upvotes']} votes for: {feature['feature'][:50]}",
                    "feature_id": feature.get("id"),
                })

        # Action: urgent issues
        for issue in report.get("urgent_issues", []):
            actions.append({
                "priority": "P0" if "CRITICAL" in issue else "P1",
                "action": "fix_issue",
                "reason": issue,
            })

        return actions
```

### 5.3 Modified Orchestrator (Reads Feedback)

```python
# MODIFY agents/orchestrator.py — add feedback-driven scheduling

class OrchestratorAgent(BaseAgent):
    """..."""

    def run(self, **kwargs):
        # NEW: Check feedback before deciding what to run
        feedback = self._check_feedback()

        if feedback.get("urgent_issues"):
            _logger.warning("URGENT FEEDBACK ISSUES:")
            for issue in feedback["urgent_issues"]:
                _logger.warning("  ⚠️  %s", issue)
            # Run urgent fixes first
            self._run_urgent_fixes(feedback["urgent_issues"])

        # Run normal pipeline (existing logic)
        pipeline_name = self.config.get("_pipeline_name", "daily")
        agent_names = pipelines.get(pipeline_name, [])

        # NEW: Adjust pipeline based on feedback
        agent_names = self._adjust_pipeline(agent_names, feedback)

        # Run agents (existing logic)
        for agent_name in agent_names:
            self._run_agent(agent_name)

    def _check_feedback(self) -> dict:
        """Read feedback analyzer output."""
        try:
            from agents.feedback_analyzer_agent import FeedbackAnalyzerAgent
            analyzer = FeedbackAnalyzerAgent(config=self.config)
            return analyzer.run()
        except Exception as e:
            _logger.warning("Could not read feedback: %s", e)
            return {}

    def _adjust_pipeline(self, agent_names: list, feedback: dict) -> list:
        """Add or reorder agents based on feedback."""
        adjusted = list(agent_names)

        for action in feedback.get("recommended_actions", []):
            if action["action"] == "fix_scoring" and action["priority"] == "P0":
                # Add scoring validation to front of pipeline
                if "failure_pattern" in adjusted:
                    adjusted.insert(0, "failure_pattern")
                _logger.info(
                    "FEEDBACK: Added scoring validation (rating %.1f/5)",
                    feedback["score_accuracy"].get("avg_rating", 0)
                )

            if action["action"] == "add_data_source":
                # Could trigger a specific collector
                _logger.info(
                    "FEEDBACK: Underserved search '%s' — consider adding data",
                    action.get("query", "")
                )

        return adjusted
```

---

## Part 6: Update the Plan Based on What Users Need Most

---

### 6.1 The Plan Update Process

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  BEFORE FEEDBACK (current plan):                                     │
│                                                                      │
│  P0: Collector Scheduler, Alert Consumer, Score Push               │
│  P1: Auth, API Keys, Watchlists, PDF Export                         │
│  P2: CRM, Mobile, HuggingFace MCP                                  │
│                                                                      │
│  AFTER FEEDBACK (example — adjusted by real user data):              │
│                                                                      │
│  P0: FIX SCORING ACCURACY (users rate it 2.1/5)                    │
│      → Run: FeedbackAnalyzerAgent to identify which scores are wrong│
│      → Run: opportunity_scorer with adjusted weights                │
│      → Run: validation test against 20 known startups              │
│                                                                      │
│  P0: BUILD ALERTS (50 feature requests, #1 demand)                 │
│      → Run: alert_dispatcher_agent + scheduler                     │
│                                                                      │
│  P1: ADD EV DATA (200 EV searches/month, underserved)               │
│      → Run: EV-specific collectors more frequently                 │
│      → Add EV sector scoring profiles                               │
│                                                                      │
│  P1: EXPORT CSV (32 feature requests, easy to build)                │
│      → Run: export_agent                                            │
│                                                                      │
│  P2: Auth, Watchlists, Score Push (still planned, not demanded)    │
│  P3: CRM, Mobile, MCP (no user demand yet)                         │
│                                                                      │
│  HOW THE PLAN CHANGED:                                               │
│  1. Scoring jumped from P2 to P0 (users said it's broken)          │
│  2. Alerts stayed P0 (confirmed by 50 requests)                    │
│  3. Scheduler dropped from P0 to P1 (not mentioned by users)       │
│  4. EV-specific features added (not even in original plan)         │
│  5. CSV export jumped from P2 to P1 (32 requests)                  │
│                                                                      │
│  THIS IS FEEDBACK-DRIVEN DEVELOPMENT:                                │
│  User data overrides assumptions. Every time.                       │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 6.2 The Updated GOALS_AND_PRIORITIES.md Template

```markdown
## Updated Priorities (Week of [DATE])

### Feedback Summary This Week
- 523 visitors, 1,847 searches, 412 chat questions
- Score rating: 3.8/5 (↑ from 3.2)
- Top request: "Alert me when scores change" (50 votes)

### Priority Changes This Week
| Change | From | To | Reason |
|--------|------|----|--------|
| Scoring accuracy | P2 | P0 | Rating 2.1/5 last week (now 3.8 after fix) |
| Alerts | P1 | P0 | 50 feature requests |
| CSV export | P2 | P1 | 32 votes |
| Scheduler | P0 | P1 | No user demand mentioned |
| EV scoring | -- | P1 | 200 EV searches/month |

### This Week's Sprint
1. P0: Fix scoring (DONE — rating went from 2.1 to 3.8)
2. P0: Build alerts (IN PROGRESS)
3. P1: Add EV data sources (PLANNED)

### Next Week's Sprint (predicted)
1. P0: Ship alerts to demo
2. P1: CSV export
3. P1: EV sector profiles
```

---

## Part 7: Show Work As We Go — Build In Public

---

### 7.1 What to Share and Where

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  CHANNEL           WHAT TO SHARE        FREQUENCY     FORMAT        │
│  ────────────────────────────────────────────────────────────────    │
│                                                                      │
│  GitHub            Weekly progress      Weekly        Markdown       │
│  Discussions       report + feedback                   issue         │
│                    summary                                           │
│                                                                      │
│  GitHub Releases   Version changelog    Per release   Release notes  │
│                    + what's new                         + tag         │
│                                                                      │
│  Twitter/X         Build screenshots,   2-3x/week     Thread or      │
│  #BuildInPublic    demo GIFs, stats                     single post  │
│                                                                      │
│  Hacker News       Major milestones     Per release   "Show HN"      │
│                    (launch, V1, V2)                     post          │
│                                                                      │
│  Reddit            Weekly learnings,    Weekly        Post +         │
│  r/startups        user stories                         comments      │
│                                                                      │
│  Blog              Deep technical       Monthly        Long-form     │
│  (dev.to or        posts (how we                       article       │
│   medium)          built the scorer)                                 │
│                                                                      │
│  Newsletter        Monthly digest       Monthly        Email         │
│  (if built)        of progress + news                                │
│                                                                      │
│  GitHub README     Live demo link,      Continuous     Badges +      │
│                    stats, screenshots                  GIFs          │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 7.2 The Weekly Build-in-Public Template

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  WEEKLY UPDATE TEMPLATE (post every Monday):                         │
│                                                                      │
│  🚀 Opportunity Intelligence Platform — Week [N] Update              │
│                                                                      │
│  TL;DR: [one sentence about what happened this week]                │
│                                                                      │
│  📊 Numbers:                                                         │
│  • [X] visitors this week (↑/↓ [Y]% from last week)                │
│  • [X] searches performed                                            │
│  • [X] feature requests received                                     │
│  • Score rating: [X]/5                                               │
│                                                                      │
│  🔨 What we shipped:                                                │
│  • [Feature 1] — [link to commit/PR]                                │
│  • [Feature 2] — [link to commit/PR]                                │
│                                                                      │
│  📈 What we learned from users:                                     │
│  • [Top search query] was searched [X] times — building [feature]   │
│  • [User feedback insight] → we adjusted [priority]                 │
│                                                                      │
│  🎯 Next week:                                                      │
│  • [What we're building]                                             │
│  • [What we're measuring]                                            │
│                                                                      │
│  🔗 Try it: demo.opportunity-intel.org                              │
│  🔗 Contribute: github.com/gokul-koduri/start                       │
│                                                                      │
│  #BuildInPublic #OpenSource #Startups                                │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Part 8: Implementation Checklist

---

### Phase A: Build Feedback Infrastructure (This Week)

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  DAY 1: DATABASE + API                                               │
│  ☐ Add 4 feedback tables to db/schema.py                            │
│  ☐ Add 5 feedback endpoints to api_server.py                        │
│  ☐ Instrument search endpoint (log queries)                         │
│  ☐ Instrument chat endpoint (log conversations)                     │
│  ☐ Test all new endpoints                                            │
│  TIME: 4-6 hours                                                     │
│                                                                      │
│  DAY 2: FRONTEND + ANALYTICS                                        │
│  ☐ Add score feedback widget (thumbs up/down) to dashboard          │
│  ☐ Add feature request form (modal) to dashboard                    │
│  ☐ Add Plausible analytics script to site/index.html                │
│  ☐ Test feedback flow end-to-end                                    │
│  TIME: 3-4 hours                                                     │
│                                                                      │
│  DAY 3: FEEDBACK AGENT + ORCHESTRATOR                               │
│  ☐ Create agents/feedback_analyzer_agent.py                         │
│  ☐ Modify agents/orchestrator.py to read feedback                   │
│  ☐ Add feedback_analyzer to pipeline config                         │
│  ☐ Test feedback → agent → action pipeline                          │
│  TIME: 3-4 hours                                                     │
│                                                                      │
│  DAY 4: PROGRESS VISIBILITY                                         │
│  ☐ Create /api/progress endpoint                                    │
│  ☐ Create CHANGELOG.md                                              │
│  ☐ Add progress section to dashboard                                │
│  ☐ Create first weekly report template                              │
│  TIME: 2-3 hours                                                     │
│                                                                      │
│  DAY 5: SHIP + MEASURE                                              │
│  ☐ Deploy feedback system to demo server                            │
│  ☐ Post first build-in-public update                                │
│  ☐ Set up weekly review calendar reminder                           │
│  ☐ Start collecting real user feedback                              │
│  TIME: 2-3 hours                                                     │
│                                                                      │
│  TOTAL: 14-20 hours (2-3 focused days)                              │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### Phase B: First Feedback Review (Next Monday)

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  ☐ Run: GET /api/feedback/dashboard                                 │
│  ☐ Review top 20 searches                                           │
│  ☐ Review top 20 chat questions                                     │
│  ☐ Review score accuracy stats                                      │
│  ☐ Review feature requests by votes                                 │
│  ☐ Score each signal (Volume + Impact + Alignment + Urgency)        │
│  ☐ Reorder priorities based on scores                               │
│  ☐ Update GOALS_AND_PRIORITIES.md                                   │
│  ☐ Post weekly update to GitHub Discussions                         │
│  ☐ Post build-in-public update to Twitter/X                         │
│  ☐ Share feedback data with agents (FeedbackAnalyzerAgent.run())    │
│                                                                      │
│  TIME: 30 minutes to 1 hour                                          │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Part 9: The One-Page Feedback Strategy

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  FEEDBACK-DRIVEN DEVELOPMENT — ONE PAGE                              │
│                                                                      │
│  COLLECT (8 channels):                                               │
│    1. Search query log — what users search for                       │
│    2. Chat question log — what users ask about                       │
│    3. Score feedback — thumbs up/down on every score                 │
│    4. Feature requests — 💡 button on dashboard                      │
│    5. Bug reports — error tracking (Sentry, planned)                 │
│    6. Analytics — Plausible (page views, retention)                  │
│    7. Social mentions — HN, Reddit, Twitter                          │
│    8. Email — direct feedback from users                             │
│                                                                      │
│  ADJUST (weekly):                                                    │
│    Score each signal → reorder priorities → update plan              │
│    Rule: Score rating < 3.0 = stop everything, fix it               │
│    Rule: 50+ requests = build it next                                │
│    Rule: 0 requests = deprioritize                                   │
│                                                                      │
│  SHARE WITH AGENTS:                                                  │
│    FeedbackAnalyzerAgent reads all feedback tables                   │
│    Orchestrator reads analyzer output before scheduling              │
│    Agents get demand-driven priorities, not static config            │
│                                                                      │
│  SHOW PROGRESS:                                                      │
│    Weekly report → GitHub Discussions + Twitter                      │
│    CHANGELOG.md → every release                                      │
│    /api/progress → live status                                       │
│    /api/feedback/dashboard → feedback data                           │
│    Build in public → #BuildInPublic on Twitter/X                    │
│                                                                      │
│  CYCLE:                                                              │
│    Build (2 weeks) → Ship → Measure (1 week) → Learn → Adjust      │
│    Never build for more than 2 weeks without measuring feedback.    │
│                                                                      │
│  IMPLEMENTATION:                                                     │
│    4 new DB tables + 5 new API endpoints + 1 new agent +            │
│    2 frontend widgets + 1 analytics script + CHANGELOG.md           │
│    Time: 14-20 hours (2-3 days)                                     │
│                                                                      │
│  CURRENT: 0 feedback channels (deaf)                                 │
│  AFTER: 8 feedback channels (fully hearing users)                   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

*Last updated: June 5, 2026*

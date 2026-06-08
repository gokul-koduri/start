# Launch Checklist

## Pre-Launch Checklist

### Infrastructure
- [ ] VPS provisioned (recommended: 4 vCPU, 8GB RAM, 100GB SSD)
- [ ] DNS A record pointed to VPS IP
- [ ] `.env` configured with production secrets
- [ ] Docker Compose all services running: `docker compose ps`
- [ ] Caddy HTTPS certificate auto-provisioned
- [ ] Health check passing: `curl https://<domain>/api/health`

### Data Validation
- [ ] 50+ startups loaded: `SELECT COUNT(*) FROM failed_startups`
- [ ] Search returns results: `curl https://<domain>/api/search?q=Tesla`
- [ ] Failure patterns visible: `curl https://<domain>/api/startups?limit=5`
- [ ] Feedback system working: Submit thumbs up, check DB

### Analytics & Monitoring
- [ ] Plausible analytics tracking page views
- [ ] Health monitoring cron active
- [ ] Database backup cron running daily

## Launch Day Checklist

### Order of Operations

1. **Morning: Final checks (T-22)**
   - [ ] Run full test suite: `python -m pytest tests/ -v`
   - [ ] Verify demo URL is accessible
   - [ ] Test search, failure patterns, feedback
   - [ ] Take demo GIF/screenshot for posts

2. **Mid-morning: GitHub Discussions (T-20)**
   - [ ] Enable Discussions in repo Settings
   - [ ] Create categories (General, Q&A, Ideas, Show and Tell, Announcements)
   - [ ] Post welcome message
   - URL: `https://github.com/<username>/<repo>/discussions`

3. **Late morning: Hacker News (T-23)**
   - [ ] Post "Show HN" using `docs/launch/show-hn.md`
   - URL: `https://news.ycombinator.com/submit`
   - Title format: `Show HN: Opportunity Intelligence Platform – Open-source Crunchbase alternative`
   - Best time: Tuesday-Thursday, 8-10 AM ET
   - [ ] Monitor comments for first 2 hours
   - [ ] Respond to every comment

4. **Afternoon: Reddit (T-24)**
   - [ ] Post to r/startups using `docs/launch/reddit-startups.md`
   - [ ] Post to r/SideProject using `docs/launch/reddit-sideproject.md`
   - [ ] Consider: r/dataisbeautiful, r/Entrepreneur, r/MachineLearning
   - Best time: Weekday afternoon, avoid Monday/Friday
   - [ ] Engage with comments for 2+ hours

### Post-Launch Monitoring
- [ ] Check analytics dashboard for visitor count
- [ ] Monitor error logs: `docker compose logs api --tail 50`
- [ ] Watch GitHub Issues/Discussions for feedback
- [ ] Track HN upvotes and Reddit karma

## Key URLs to Prepare

| Resource | URL |
|---|---|
| Live Demo | `https://<domain>` |
| API Docs | `https://<domain>/docs` |
| GitHub Repo | `https://github.com/<username>/<repo>` |
| Discussions | `https://github.com/<username>/<repo>/discussions` |
| Dashboard | `https://<domain>:8501` |

## Metrics to Track (First Week)

| Metric | Target | How to Measure |
|---|---|---|
| Unique visitors | 500+ | Plausible analytics |
| API requests | 1000+ | Query log table |
| Feedback submissions | 20+ | Feedback table count |
| GitHub stars | 50+ | GitHub repo page |
| HN upvotes | 30+ | HN post |
| Reddit upvotes | 20+ | Reddit posts |

## Content Files

- `docs/launch/show-hn.md` — Hacker News "Show HN" post
- `docs/launch/reddit-startups.md` — r/startups post
- `docs/launch/reddit-sideproject.md` — r/SideProject post
- `docs/launch/github-discussions-setup.md` — Setup guide for Discussions

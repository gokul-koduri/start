# GitHub Discussions Setup Guide

## Enable GitHub Discussions

1. Go to your repository on GitHub
2. Click **Settings** tab
3. Scroll down to **Features** section
4. Check the **Discussions** checkbox
5. GitHub will create a Discussions tab on your repo

## Recommended Categories

Set up these discussion categories:

| Category | Format | Purpose |
|---|---|---|
| General | Open-ended | General questions, introductions |
| Q&A | Question/Answer | Technical questions with accepted answers |
| Ideas | Open-ended | Feature requests and suggestions |
| Show and Tell | Open-ended | Users sharing how they use the platform |
| Announcements | Announcement | Project updates (only maintainers can post) |

## Initial Discussion Templates

### Welcome Post (Announcement)

```
Title: Welcome to the Opportunity Intelligence Platform!

Body:
Welcome! This is the community hub for the Opportunity Intelligence Platform —
an open-source alternative to Crunchbase/PitchBook that studies why startups succeed
and how to learn from failures.

## Quick Links
- Live Demo: [your-demo-url]
- Documentation: /docs
- API Reference: /docs/api
- Contributing: CONTRIBUTING.md

## How to Get Started
1. Try the live demo
2. Check the API docs
3. Ask questions in Q&A
4. Share your use cases in Show and Tell

We study 163+ failed startups across manufacturing, EV, fintech, and more.
Our AI agents analyze failure patterns and identify revival opportunities.

What would you like to explore?
```

## Feedback Categories

Create labels for triage:
- `feedback: search` — Search-related feedback
- `feedback: chat` — AI Analyst feedback
- `feedback: data` — Data quality issues
- `feedback: feature` — Feature requests
- `feedback: bug` — Bug reports
- `area: dashboard` — Dashboard UI issues
- `area: api` — API issues
- `area: docs` — Documentation improvements

## Integration with Sprint Workflow

After enabling Discussions:
1. Add the Discussions URL to the README
2. Link to Discussions from the dashboard feedback button
3. Use GitHub Actions to auto-post weekly reports (Sprint 3 task T-046)
4. Reference discussions in commit messages when implementing community suggestions

# Cross-Module Market Correlation Analysis

_Generated: 2026-06-11 06:05 UTC_

This report analyzes data across all 7 analysis modules to find which signals reinforce each other.

## Executive Summary

Correlations ranked by strength:

| Rank | Correlation | Pearson r | Strength |
| --- | --- | --- | --- |
| 1 | Sector Failure Count vs Revival Opportunity Score | +0.000 (negligible positive) | ★ |
| 2 | Failure Reason Distribution vs BLS Survival Rates | +0.000 (negligible positive) | ★ |
| 3 | Geographic Failure Density vs Whale Investor Activity | +0.000 (negligible positive) | ★ |
| 4 | Average Funding Raised vs Year of Shutdown | +0.000 (negligible positive) | ★ |
| 5 | News Volume vs Failure Timing | +0.000 (negligible positive) | ★ |
| 6 | Reshoring Jobs vs Revival Industry Match | +0.000 (negligible positive) | ★ |
| 7 | Opportunity Score vs Whale Investor Backing | +0.000 (negligible positive) | ★ |

### Top Findings

**1. 1. Sector Failure Count vs Revival Opportunity Score**: Pearson r = +0.000 (negligible positive). Weak or no positive correlation — failures and revival scoring are largely independent signals.

**2. 2. Failure Reason Distribution vs BLS Survival Rates**: Pearson r (failures vs survival rate by year) = +0.000 (negligible positive). No strong relationship — failures are driven more by company-specific factors than macro survival rates.

**3. 3. Geographic Failure Density vs Whale Investor Activity**: Pearson r (failure density vs whale mentions) = +0.000 (negligible positive). Whale investor activity and failure density are NOT strongly linked at the regional level.

---

## 1. Sector Failure Count vs Revival Opportunity Score

**Question**: Do sectors with the most failures also have the highest revival scores?

**Finding**: Pearson r = +0.000 (negligible positive). Weak or no positive correlation — failures and revival scoring are largely independent signals.

| Industry | Revival Score | Failure Count |
| --- | --- | --- |

---

## 2. Failure Reason Distribution vs BLS Survival Rates

**Question**: Are failure categories concentrated in low-survival years?

**Finding**: Pearson r (failures vs survival rate by year) = +0.000 (negligible positive). No strong relationship — failures are driven more by company-specific factors than macro survival rates.

Failure category distribution:

| Failure Category | Count |
| --- | --- |

Average 5-year survival rate by year:

| Year | Avg 5yr Survival |
| --- | --- |

---

## 3. Geographic Failure Density vs Whale Investor Activity

**Question**: Do whale investors target regions with high failure density?

**Finding**: Pearson r (failure density vs whale mentions) = +0.000 (negligible positive). Whale investor activity and failure density are NOT strongly linked at the regional level.

| Region | Failure Count | Whale Mentions |
| --- | --- | --- |

---

## 4. Average Funding Raised vs Year of Shutdown

**Question**: Are recent failures better-funded than older ones (bubble inflating)?

**Finding**: Pearson r (year vs avg funding) = +0.000 (negligible positive). Flat — funding amounts haven't changed significantly across failure years.

| Year Shutdown | Avg Funding | # Failures |
| --- | --- | --- |

---

## 5. News Volume vs Failure Timing

**Question**: Does news coverage volume correlate with shutdown counts by year?

**Finding**: Pearson r (news volume vs failure count by year) = +0.000 (negligible positive). News volume and failure timing are NOT strongly correlated — coverage is driven by other factors.

Failures by year:

| Year | Failure Count |
| --- | --- |

News articles by year:

| Year | Article Count |
| --- | --- |

---

## 6. Reshoring Jobs vs Revival Industry Match

**Question**: Are industries scored as 'reviving' actually creating reshoring jobs?

**Finding**: Pearson r (jobs vs revival score) = +0.000 (negligible positive). Matched 0/0 reshoring industries to revival scores. No clear link between score and job count.

| Reshoring Industry | Jobs | Matched Revival | Score |
| --- | --- | --- | --- |

---

## 7. Opportunity Score vs Whale Investor Backing

**Question**: Do our highest-scored opportunities have whale backing?

**Finding**: 0/0 opportunities have whale backing. Avg score: 0.0 (backed) vs 0.0 (not backed), Δ=+0.0. Scores are similar regardless of backing — whale activity is independent of our scoring.

| Opportunity | Score | Risk | Whale Backed | Investors |
| --- | --- | --- | --- | --- |

---

## Methodology

- **Pearson correlation** is used for numeric pairs (e.g., funding vs year).
- r ≥ 0.7 = strong; r ≥ 0.4 = moderate; r ≥ 0.2 = weak; |r| < 0.2 = negligible.
- All data sourced from the live MySQL database populated by the 7 analysis agents.
- Sample sizes are small (163 startups, 31 BLS records, 6 revival industries) so treat correlations as exploratory.

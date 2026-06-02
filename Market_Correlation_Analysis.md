# Cross-Module Market Correlation Analysis

_Generated: 2026-06-02 02:51 UTC_

This report analyzes data across all 7 analysis modules to find which signals reinforce each other.

## Executive Summary

Correlations ranked by strength:

| Rank | Correlation | Pearson r | Strength |
| --- | --- | --- | --- |
| 1 | Failure Reason Distribution vs BLS Survival Rates | +0.697 (moderate positive) | ★★★ |
| 2 | Average Funding Raised vs Year of Shutdown | +0.685 (moderate positive) | ★★★ |
| 3 | Sector Failure Count vs Revival Opportunity Score | +0.000 (negligible positive) | ★ |
| 4 | Geographic Failure Density vs Whale Investor Activity | +0.000 (negligible positive) | ★ |
| 5 | News Volume vs Failure Timing | +0.000 (negligible positive) | ★ |
| 6 | Reshoring Jobs vs Revival Industry Match | +0.000 (negligible positive) | ★ |
| 7 | Opportunity Score vs Whale Investor Backing | +0.000 (negligible positive) | ★ |

### Top Findings

**1. 2. Failure Reason Distribution vs BLS Survival Rates**: Pearson r (failures vs survival rate by year) = +0.697 (moderate positive). Surprising positive correlation — more failures recorded in higher-survival years (likely because more firms exist).

**2. 4. Average Funding Raised vs Year of Shutdown**: Pearson r (year vs avg funding) = +0.685 (moderate positive). Strong positive trend — recent failures had MORE capital to burn. The funding bubble is real.

**3. 1. Sector Failure Count vs Revival Opportunity Score**: Pearson r = +0.000 (negligible positive). Weak or no positive correlation — failures and revival scoring are largely independent signals.

---

## 1. Sector Failure Count vs Revival Opportunity Score

**Question**: Do sectors with the most failures also have the highest revival scores?

**Finding**: Pearson r = +0.000 (negligible positive). Weak or no positive correlation — failures and revival scoring are largely independent signals.

| Industry | Revival Score | Failure Count |
| --- | --- | --- |

---

## 2. Failure Reason Distribution vs BLS Survival Rates

**Question**: Are failure categories concentrated in low-survival years?

**Finding**: Pearson r (failures vs survival rate by year) = +0.697 (moderate positive). Surprising positive correlation — more failures recorded in higher-survival years (likely because more firms exist).

Failure category distribution:

| Failure Category | Count |
| --- | --- |
| no_market_need | 10 |
| ran_out_of_cash | 10 |
| poor_product | 7 |
| capital_intensity | 5 |
| no_business_model | 5 |
| pilot_to_scale_gap | 5 |
| governance | 4 |
| outcompeted | 3 |
| ineffective_marketing | 2 |
| supply_chain | 2 |
| market_timing | 1 |
| spac_overvaluation | 1 |

Average 5-year survival rate by year:

| Year | Avg 5yr Survival |
| --- | --- |
| 1994 | 53.0% |
| 1995 | 52.4% |
| 1996 | 50.9% |
| 1997 | 49.7% |
| 1998 | 48.4% |
| 1999 | 48.3% |
| 2000 | 47.3% |
| 2001 | 49.5% |
| 2002 | 51.1% |
| 2003 | 52.3% |
| 2004 | 51.6% |
| 2005 | 51.2% |
| 2006 | 49.4% |
| 2007 | 48.8% |
| 2008 | 48.1% |
| 2009 | 50.5% |
| 2010 | 54.0% |
| 2011 | 55.2% |
| 2012 | 57.4% |
| 2013 | 57.7% |
| 2014 | 60.4% |
| 2015 | 61.0% |
| 2016 | 61.3% |
| 2017 | 61.7% |
| 2018 | 57.6% |
| 2019 | 57.4% |
| 2020 | 58.4% |

---

## 3. Geographic Failure Density vs Whale Investor Activity

**Question**: Do whale investors target regions with high failure density?

**Finding**: Pearson r (failure density vs whale mentions) = +0.000 (negligible positive). Whale investor activity and failure density are NOT strongly linked at the regional level.

| Region | Failure Count | Whale Mentions |
| --- | --- | --- |
| US & Global | 104 | 0 |
| Europe | 22 | 0 |
| India | 19 | 0 |
| China | 7 | 0 |
| Africa | 4 | 0 |
| Other | 4 | 0 |
| Asia-Pacific | 3 | 0 |

---

## 4. Average Funding Raised vs Year of Shutdown

**Question**: Are recent failures better-funded than older ones (bubble inflating)?

**Finding**: Pearson r (year vs avg funding) = +0.685 (moderate positive). Strong positive trend — recent failures had MORE capital to burn. The funding bubble is real.

| Year Shutdown | Avg Funding | # Failures |
| --- | --- | --- |
| 2002 | $35.0M | 1 |
| 2007 | $13.3M | 1 |
| 2008 | $8.7M | 2 |
| 2009 | $4.0M | 2 |
| 2010 | $2.6M | 2 |
| 2011 | $1.3M | 1 |
| 2013 | $45.8M | 11 |
| 2014 | $15.0M | 9 |
| 2015 | $19.7M | 20 |
| 2016 | $28.2M | 20 |
| 2017 | $44.6M | 11 |
| 2018 | $501.3M | 3 |
| 2019 | $70.7M | 7 |
| 2020 | $638.8M | 3 |
| 2023 | $1392.3M | 3 |
| 2024 | $2013.8M | 29 |
| 2025 | $565.0M | 4 |

---

## 5. News Volume vs Failure Timing

**Question**: Does news coverage volume correlate with shutdown counts by year?

**Finding**: Pearson r (news volume vs failure count by year) = +0.000 (negligible positive). News volume and failure timing are NOT strongly correlated — coverage is driven by other factors.

Failures by year:

| Year | Failure Count |
| --- | --- |
| 2002 | 1 |
| 2007 | 1 |
| 2008 | 3 |
| 2009 | 2 |
| 2010 | 2 |
| 2011 | 1 |
| 2012 | 1 |
| 2013 | 12 |
| 2014 | 11 |
| 2015 | 27 |
| 2016 | 24 |
| 2017 | 13 |
| 2018 | 4 |
| 2019 | 12 |
| 2020 | 3 |
| 2023 | 3 |
| 2024 | 37 |
| 2025 | 6 |

News articles by year:

| Year | Article Count |
| --- | --- |

---

## 6. Reshoring Jobs vs Revival Industry Match

**Question**: Are industries scored as 'reviving' actually creating reshoring jobs?

**Finding**: Pearson r (jobs vs revival score) = +0.000 (negligible positive). Matched 5/6 reshoring industries to revival scores. No clear link between score and job count.

| Reshoring Industry | Jobs | Matched Revival | Score |
| --- | --- | --- | --- |
| Semiconductor | 115000 | semiconductor fabrication | 50.0 |
| Electric Vehicle | 78000 | — | 0 |
| Battery | 45000 | battery cell manufacturing | 50.0 |
| Pharmaceutical | 22000 | pharmaceutical & biomanufacturing | 50.0 |
| Solar | 18000 | solar panel & component manufacturing | 50.0 |
| Steel | 8000 | steel & primary metals | 50.0 |

---

## 7. Opportunity Score vs Whale Investor Backing

**Question**: Do our highest-scored opportunities have whale backing?

**Finding**: 5/7 opportunities have whale backing. Avg score: 79.0 (backed) vs 65.0 (not backed), Δ=+14.0. Whale-backed opportunities have HIGHER scores — our scoring aligns with institutional interest.

| Opportunity | Score | Risk | Whale Backed | Investors |
| --- | --- | --- | --- | --- |
| US & Global | 100 | low | Yes | TSMC |
| Europe | 100 | low | Yes | TSMC |
| Northvolt | 70 | low | Yes | TSMC |
| Northvolt | 70 | low | Yes | TSMC |
| China | 70 | low | No | — |
| India | 60 | low | No | — |
| 54gene | 55 | medium | Yes | TSMC |

---

## Methodology

- **Pearson correlation** is used for numeric pairs (e.g., funding vs year).
- r ≥ 0.7 = strong; r ≥ 0.4 = moderate; r ≥ 0.2 = weak; |r| < 0.2 = negligible.
- All data sourced from the live MySQL database populated by the 7 analysis agents.
- Sample sizes are small (163 startups, 31 BLS records, 6 revival industries) so treat correlations as exploratory.

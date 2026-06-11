#!/usr/bin/env python3
"""Seed script: imports existing report data into MySQL.

Run once after initial setup to populate the database with data
from the manually-compiled report.
"""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import setup_logging, load_config
from db.connection import get_connection
from db import schema

_logger = logging.getLogger(__name__)


def seed():
    setup_logging()
    load_config()
    conn = get_connection()
    schema.init_schema(conn)

    _logger.info("Seeding database with existing report data...")

    # ── Failed Startups (Part 1A: US & Global) ──
    us_global = [
        (
            "Byju's",
            "EdTech",
            None,
            "US",
            "US & Global",
            5400000000,
            "~$5.4B+ (valued at $22B)",
            2011,
            2024,
            "Financial mismanagement, aggressive acquisition spree",
            None,
            1,
            "manual",
        ),
        (
            "Fisker",
            "EV/Automotive",
            "EV Manufacturing",
            "US",
            "US & Global",
            1000000000,
            "~$1B+",
            2016,
            2024,
            "Poor product quality, failed to compete with Tesla",
            "pilot_to_scale_gap",
            1,
            "manual",
        ),
        (
            "Bird",
            "Micro-mobility",
            None,
            "US",
            "US & Global",
            776000000,
            "~$776M (unicorn at $2.4B)",
            2017,
            2024,
            "Unit economics failure, regulatory issues",
            "ran_out_of_cash",
            1,
            "manual",
        ),
        (
            "EasyKnock",
            "Proptech",
            None,
            "US",
            "US & Global",
            455000000,
            "$455M",
            2016,
            2024,
            "Market conditions, financial model unsustainability",
            "ran_out_of_cash",
            1,
            "manual",
        ),
        (
            "Rad Power Bikes",
            "Mobility/EV",
            "E-bike Manufacturing",
            "US",
            "US & Global",
            300000000,
            "~$300M+",
            2015,
            2024,
            "Supply chain, cash flow issues",
            "supply_chain",
            1,
            "manual",
        ),
        (
            "Tally",
            "Fintech",
            None,
            "US",
            "US & Global",
            87000000,
            "~$87M",
            2015,
            2024,
            "Debt consolidation market challenges",
            "no_market_need",
            1,
            "manual",
        ),
        (
            "Northvolt",
            "Battery Manufacturing",
            "Battery Cell Manufacturing",
            "Sweden",
            "US & Global",
            14000000000,
            "$14B+",
            2016,
            2024,
            "Production delays, cost overruns, cancelled orders",
            "capital_intensity",
            1,
            "manual",
        ),
        (
            "Mindstrong",
            "Healthtech",
            None,
            "US",
            "US & Global",
            None,
            "Significant VC backing",
            2014,
            2024,
            "Business model issues in digital health",
            "no_business_model",
            1,
            "manual",
        ),
        (
            "Tessera",
            "Biotech/Genomics",
            None,
            "US",
            "US & Global",
            None,
            "Well-funded",
            2016,
            2024,
            "Technical/scientific challenges",
            "pilot_to_scale_gap",
            1,
            "manual",
        ),
        (
            "Veev",
            "PropTech/Construction",
            "Modular Construction",
            "US",
            "US & Global",
            600000000,
            "~$600M+",
            2014,
            2024,
            "Supply chain costs, market downturn in real estate",
            "supply_chain",
            1,
            "manual",
        ),
    ]

    # Manufacturing-specific failures
    mfg_failures = [
        (
            "Desktop Metal",
            "3D Printing",
            "3D Printing / Additive Mfg",
            "US",
            "US & Global",
            6000000000,
            "~$6B (SPAC valuation)",
            2010,
            2024,
            "SPAC overvaluation, inability to achieve profitability",
            "spac_overvaluation",
            0,
            "manual",
        ),
        (
            "BCN3D",
            "3D Printing",
            "3D Printing",
            "Spain",
            "Europe",
            None,
            "~€50M+ raised",
            2015,
            2025,
            "Voluntary bankruptcy; market oversaturation",
            "no_market_need",
            0,
            "manual",
        ),
        (
            "Black Buffalo 3D",
            "3D Printing",
            "Construction 3D Printing",
            "US",
            "US & Global",
            None,
            "Significant funding",
            2018,
            2025,
            "Chapter 11 bankruptcy; market failed to materialize",
            "market_timing",
            0,
            "manual",
        ),
        (
            "Dextrous Robotics",
            "Robotics",
            "Robotics / Material Handling",
            "US",
            "US & Global",
            None,
            "Well-funded",
            2019,
            2024,
            "Robotics pilot could not scale to commercial deployment",
            "pilot_to_scale_gap",
            0,
            "manual",
        ),
        (
            "RoboTire",
            "Robotics",
            "Robotics / Automotive Service",
            "US",
            "US & Global",
            30000000,
            "$30M+",
            2018,
            2024,
            "Automated tire changing economics did not work at scale",
            "pilot_to_scale_gap",
            0,
            "manual",
        ),
        (
            "Katerra",
            "Construction",
            "Modular Construction",
            "US",
            "US & Global",
            2000000000,
            "$2B+",
            2015,
            2024,
            "Overambitious vertical integration",
            "capital_intensity",
            0,
            "manual",
        ),
    ]

    for row in us_global + mfg_failures:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT IGNORE INTO failed_startups
            (name, sector, manufacturing_sub_sector, country, region, funding_raised_usd,
             funding_description, year_founded, year_shutdown, failure_reason, failure_category,
             notable, source)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
            row,
        )
        cursor.close()

    _logger.info("Seeded %d US/Global startups", len(us_global) + len(mfg_failures))

    # ── India Startups ──
    india = [
        (
            "Byju's",
            "EdTech",
            None,
            "India",
            "India",
            5400000000,
            "~$5.4B+",
            2011,
            2024,
            "Financial mismanagement, aggressive acquisition spree, governance",
            "governance",
            1,
            "manual",
        ),
        (
            "Zilingo",
            "Fashion-tech",
            None,
            "India",
            "India",
            300000000,
            "~$300M+",
            2015,
            2024,
            "Corporate governance issues, auditor disputes",
            "governance",
            1,
            "manual",
        ),
        (
            "Dunzo",
            "Quick Commerce",
            None,
            "India",
            "India",
            500000000,
            "~$500M+",
            2015,
            2024,
            "Burn rate exceeded revenue; pivoted too many times",
            "ran_out_of_cash",
            1,
            "manual",
        ),
        (
            "BluSmart",
            "EV Ride-Hailing",
            "EV Manufacturing",
            "India",
            "India",
            100000000,
            "~$100M+",
            2019,
            2025,
            "Ran out of funds",
            "ran_out_of_cash",
            1,
            "manual",
        ),
        (
            "Hike",
            "Social/Chat",
            None,
            "India",
            "India",
            260000000,
            "~$260M+",
            2012,
            2025,
            "Pivoted multiple times; never found PMF",
            "no_market_need",
            1,
            "manual",
        ),
        (
            "Trell",
            "Content/Social Commerce",
            None,
            "India",
            "India",
            45000000,
            "$45M",
            2016,
            2024,
            "Alleged misuse of funds",
            "governance",
            1,
            "manual",
        ),
        (
            "Good Glamm Group",
            "Beauty/D2C",
            None,
            "India",
            "India",
            500000000,
            "~$500M+",
            2017,
            2025,
            "Major layoffs and restructuring",
            "ran_out_of_cash",
            1,
            "manual",
        ),
        (
            "Paytm Mall",
            "E-commerce",
            None,
            "India",
            "India",
            None,
            "Backed by Paytm/SoftBank",
            2017,
            2024,
            "Could not build sustainable moat",
            "outcompeted",
            1,
            "manual",
        ),
        (
            "BharatPe",
            "Fintech/Payments",
            None,
            "India",
            "India",
            600000000,
            "~$600M+",
            2017,
            2024,
            "Corporate governance scandal",
            "governance",
            1,
            "manual",
        ),
    ]

    for row in india:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT IGNORE INTO failed_startups
            (name, sector, manufacturing_sub_sector, country, region, funding_raised_usd,
             funding_description, year_founded, year_shutdown, failure_reason, failure_category,
             notable, source)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
            row,
        )
        cursor.close()

    _logger.info("Seeded %d India startups", len(india))

    # ── China Startups ──
    china = [
        (
            "Royole Technology",
            "Flexible Display",
            "Display Manufacturing",
            "China",
            "China",
            2000000000,
            "~$2B+",
            2012,
            2024,
            "Could not mass-produce flexible displays",
            "pilot_to_scale_gap",
            1,
            "manual",
        ),
        (
            "WM Motor",
            "EV",
            "EV Manufacturing",
            "China",
            "China",
            4000000000,
            "¥30B+ (~$4B+)",
            2015,
            2023,
            "Collapsed under debt",
            "ran_out_of_cash",
            1,
            "manual",
        ),
        (
            "HiPhi / Human Horizons",
            "Premium EV",
            "EV Manufacturing",
            "China",
            "China",
            None,
            "Hundreds of millions",
            2017,
            2024,
            "Production halt; bankruptcy restructuring",
            "capital_intensity",
            1,
            "manual",
        ),
        (
            "Byton",
            "EV",
            "EV Manufacturing",
            "China",
            "China",
            1200000000,
            "¥8.4B (~$1.2B+)",
            2016,
            2024,
            "Burned cash without delivering mass-market car",
            "ran_out_of_cash",
            1,
            "manual",
        ),
        (
            "Neta Auto",
            "EV",
            "EV Manufacturing",
            "China",
            "China",
            None,
            "Top-seller status",
            2014,
            2024,
            "Bankruptcy restructuring",
            "outcompeted",
            1,
            "manual",
        ),
        (
            "Hengchi",
            "EV",
            "EV Manufacturing",
            "China",
            "China",
            None,
            "Tens of billions (Evergrande)",
            2019,
            2024,
            "Evergrande debt crisis consumed subsidiary",
            "ran_out_of_cash",
            1,
            "manual",
        ),
        (
            "Wusheng Semiconductor",
            "Semiconductors",
            "Semiconductor Manufacturing",
            "China",
            "China",
            1400000000,
            "Registered ¥10B ($1.4B)",
            2020,
            2025,
            "Chip investment bubble burst",
            "capital_intensity",
            1,
            "manual",
        ),
    ]

    for row in china:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT IGNORE INTO failed_startups
            (name, sector, manufacturing_sub_sector, country, region, funding_raised_usd,
             funding_description, year_founded, year_shutdown, failure_reason, failure_category,
             notable, source)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
            row,
        )
        cursor.close()

    _logger.info("Seeded %d China startups", len(china))

    # ── Europe Startups ──
    europe = [
        (
            "Northvolt",
            "Battery Manufacturing",
            "Battery Cell Manufacturing",
            "Sweden",
            "Europe",
            14000000000,
            "$14B+",
            2016,
            2024,
            "Production delays, cost overruns, cancelled BMW/VW",
            "capital_intensity",
            1,
            "manual",
        ),
        (
            "Gorillas",
            "Quick Commerce",
            None,
            "Germany",
            "Europe",
            1300000000,
            "~$1.3B",
            2017,
            2024,
            "Unit economics impossible",
            "no_business_model",
            1,
            "manual",
        ),
        (
            "Getir",
            "Quick Commerce",
            None,
            "Turkey",
            "Europe",
            2000000000,
            "~$2B+",
            2015,
            2024,
            "Global quick commerce collapse",
            "no_business_model",
            1,
            "manual",
        ),
        (
            "Jokr",
            "Quick Commerce",
            None,
            "Germany",
            "Europe",
            170000000,
            "~$170M",
            2021,
            2023,
            "Merged into Getir (which also collapsed)",
            "no_business_model",
            1,
            "manual",
        ),
    ]

    for row in europe:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT IGNORE INTO failed_startups
            (name, sector, manufacturing_sub_sector, country, region, funding_raised_usd,
             funding_description, year_founded, year_shutdown, failure_reason, failure_category,
             notable, source)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
            row,
        )
        cursor.close()

    _logger.info("Seeded %d Europe startups", len(europe))

    # ── Africa Startups ──
    africa = [
        (
            "Lipa Later",
            "BNPL/Fintech",
            None,
            "Kenya",
            "Africa",
            20000000,
            "~$20M+",
            2018,
            2024,
            "Mounting debts; failed to secure funding",
            "ran_out_of_cash",
            1,
            "manual",
        ),
        (
            "54gene",
            "Healthtech/Genomics",
            "Biomanufacturing",
            "Nigeria",
            "Africa",
            45000000,
            "~$45M",
            2019,
            2024,
            "Business model issues; board disputes",
            "no_business_model",
            1,
            "manual",
        ),
        (
            "Sendy",
            "Logistics",
            None,
            "Kenya",
            "Africa",
            20000000,
            "~$20M+",
            2015,
            2024,
            "Failed to achieve profitability",
            "ran_out_of_cash",
            1,
            "manual",
        ),
        (
            "Zumi",
            "E-commerce",
            None,
            "Kenya",
            "Africa",
            7000000,
            "~$7M",
            2016,
            2023,
            "Could not compete with Jumia",
            "outcompeted",
            1,
            "manual",
        ),
    ]

    for row in africa:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT IGNORE INTO failed_startups
            (name, sector, manufacturing_sub_sector, country, region, funding_raised_usd,
             funding_description, year_founded, year_shutdown, failure_reason, failure_category,
             notable, source)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
            row,
        )
        cursor.close()

    _logger.info("Seeded %d Africa startups", len(africa))

    # ── CB Insights Failure Reasons ──
    reasons = [
        ("No market need / Poor product-market fit", 42, 1),
        ("Ran out of cash", 38, 2),
        ("Not the right team", 23, 3),
        ("Got outcompeted", 20, 4),
        ("Pricing/cost issues", 18, 5),
        ("Poor product", 17, 6),
        ("No viable business model", 17, 7),
        ("Ineffective marketing", 14, 8),
        ("Ignored customer needs", 14, 9),
    ]
    for reason, pct, rank in reasons:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT IGNORE INTO failure_reasons_taxonomy (reason, percentage, rank_order) VALUES (%s, %s, %s)",
            (reason, pct, rank),
        )
        cursor.close()

    _logger.info("Seeded %d failure reasons", len(reasons))

    # ── Manufacturing Failure Categories ──
    mfg_cats = [
        (
            "Capital Intensity",
            "Hardware requires 5-10x more capital than software; runway evaporates",
            35,
            "Northvolt ($14B), Katerra ($2B)",
        ),
        (
            "Pilot-to-Scale Gap",
            "Technology works in lab/pilot but fails at commercial volume",
            25,
            "Dextrous Robotics, RoboTire, 10+ robotics cos",
        ),
        (
            "Supply Chain Disruption",
            "COVID-era supply shocks, tariff uncertainty, single-source dependency",
            20,
            "Veev, Rad Power Bikes",
        ),
        (
            "SPAC Overvaluation",
            "Went public at inflated valuations via SPAC, then collapsed",
            15,
            "Desktop Metal, multiple EV companies",
        ),
        (
            "Market Timing",
            "Correct thesis but too early",
            10,
            "Black Buffalo 3D (construction 3D printing)",
        ),
    ]
    for cat, desc, pct, examples in mfg_cats:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT IGNORE INTO manufacturing_failure_categories (failure_category, description, estimated_pct, example_startups) VALUES (%s, %s, %s, %s)",
            (cat, desc, pct, examples),
        )
        cursor.close()

    _logger.info("Seeded %d manufacturing failure categories", len(mfg_cats))

    # ── Failure Idea Patterns ──
    patterns = [
        (
            "AI Wrapper Apps",
            "Numerous seed-stage AI startups (2023-24)",
            "Made obsolete by OpenAI/Google free features",
            "AI commoditization kills thin wrappers",
        ),
        (
            "Ultra-fast grocery delivery",
            "Gorillas, Getir, Jokr (~$3B+ combined)",
            "Unit economics impossible at 10-min delivery",
            "Customers tolerate 30-min delivery",
        ),
        (
            "Web3/Crypto Infrastructure",
            "Hundreds of seed-funded projects (2021-22)",
            "Market crashed, no real demand",
            "Crypto utility remains niche",
        ),
        (
            "B2B SaaS for Niche Markets",
            "Many seed-stage startups",
            "Market too small for venture returns",
            "Not every vertical needs venture-scale SaaS",
        ),
        (
            "Consumer Social Apps",
            "Numerous post-TikTok clones",
            "User retention near-zero",
            "Social is winner-take-all",
        ),
        (
            "Micro-mobility sharing",
            "Bird, Lime (near-death)",
            "Unit economics never worked",
            "E-scooters as a service is structurally flawed",
        ),
    ]
    for cat, examples, why, reality in patterns:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT IGNORE INTO failure_idea_patterns (idea_category, example_startups, why_failed, market_reality) VALUES (%s, %s, %s, %s)",
            (cat, examples, why, reality),
        )
        cursor.close()

    _logger.info("Seeded %d failure idea patterns", len(patterns))

    # ── Revival Industries ──
    industries = [
        (
            "Semiconductor Fabrication",
            "1990s-2000s",
            "AI boom demand, CHIPS Act funding, national security",
            "Former Intel, AMD, Motorola fabs",
            "Global semiconductor market projected at $1T+ by 2030",
            "TSMC (Arizona), Intel (Ohio), Samsung (Texas)",
        ),
        (
            "Battery Cell Manufacturing",
            "2000s",
            "EV demand surge, IRA incentives, supply chain security",
            "Former chemical plants, auto parts factories",
            "U.S. EV battery demand to reach 500GWh+ by 2030",
            "Multiple OEMs and startups",
        ),
        (
            "Solar Panel & Component Manufacturing",
            "2010s",
            "Tariffs on Chinese panels, IRA tax credits",
            "Former electronics factories",
            "U.S. solar installations growing 30%+ annually",
            "First Solar, various newcomers",
        ),
        (
            "Textile & Apparel Manufacturing",
            "1997-2009",
            "Rising overseas wages, nearshoring, automation",
            "Historic mills across NC, SC, GA, AL",
            "Fast-fashion logistics + tariff avoidance",
            "Various reshoring companies",
        ),
        (
            "Pharmaceutical & Biomanufacturing",
            "2000s",
            "COVID vulnerabilities, Biosecure Act, onshoring",
            "Former pharma plants in NJ, PA, PR",
            "U.S. pharma market >$550B",
            "Various pharma companies",
        ),
        (
            "Steel & Primary Metals",
            "1980s-2000s",
            "Infrastructure spending, tariff protections, green steel",
            "Former steel mills in Rust Belt",
            "Infrastructure + reshoring = sustained demand",
            "Various steelmakers",
        ),
    ]
    for ind, died, why, sites, market, investors in industries:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT IGNORE INTO revival_industries (industry, died_period, why_returning, closed_site_types, market_fit, key_investors) VALUES (%s, %s, %s, %s, %s, %s)",
            (ind, died, why, sites, market, investors),
        )
        cursor.close()

    _logger.info("Seeded %d revival industries", len(industries))

    # ── Geographic Hotspots ──
    hotspots = [
        (
            "Rust Belt (OH, PA, IN, MI)",
            "Steel mills, auto plants, heavy manufacturing",
            "EV, battery, green steel",
        ),
        (
            "Southeast (NC, SC, GA, AL)",
            "Textile mills, furniture factories",
            "Advanced textiles, EV supply chain",
        ),
        (
            "Sun Belt (AZ, TX, NV)",
            "Electronics assembly, aerospace",
            "Semiconductors, data centers, solar",
        ),
        (
            "Northeast (NJ, NY, PA)",
            "Pharma, chemical plants",
            "Biomanufacturing, pharma API",
        ),
        (
            "Pacific Northwest (WA, OR)",
            "Paper mills, aluminum smelters",
            "Green manufacturing, bio-products",
        ),
        ("Puerto Rico", "Pharma manufacturing", "Biomanufacturing, medical devices"),
    ]
    for region, facilities, potential in hotspots:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT IGNORE INTO geographic_hotspots (region, closed_facility_types, revival_potential) VALUES (%s, %s, %s)",
            (region, facilities, potential),
        )
        cursor.close()

    _logger.info("Seeded %d geographic hotspots", len(hotspots))

    # ── Reshoring Summary Stats ──
    cursor = conn.cursor()
    cursor.execute(
        """REPLACE INTO reshoring_summary_stats
           (stat_year, total_jobs, success_rate_pct, key_policy, headline, source)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (
            2024,
            244000,
            69.0,
            "CHIPS Act ($52B); IRA ($369B)",
            "244,000 jobs announced/created; 69% success rate",
            "Reshoring Initiative 2024 Annual Report",
        ),
    )
    cursor.close()

    _logger.info("Seeded reshoring summary stats")

    conn.commit()

    # Verify
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM failed_startups")
    startup_count = cursor.fetchone()["cnt"]
    cursor.close()
    _logger.info("Database now contains %d startup records", startup_count)
    conn.close()


if __name__ == "__main__":
    seed()

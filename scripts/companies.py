"""
Company metadata for the IPO Filing Analyzer.
Single source of truth: tickers, IPO dates, sectors, CIK numbers.
"""

COMPANIES = [
    {"company": "Snowflake",     "ticker": "SNOW",  "ipo_date": "2020-09-16", "sector": "Cloud/Data",       "cik": "0001640147"},
    {"company": "Palantir",      "ticker": "PLTR",  "ipo_date": "2020-09-30", "sector": "Data Analytics",   "cik": "0001321655"},
    {"company": "DoorDash",      "ticker": "DASH",  "ipo_date": "2020-12-09", "sector": "Delivery",         "cik": "0001792789"},
    {"company": "Coinbase",      "ticker": "COIN",  "ipo_date": "2021-04-14", "sector": "Crypto/Fintech",   "cik": "0001679788"},
    {"company": "Rivian",        "ticker": "RIVN",  "ipo_date": "2021-11-10", "sector": "EV/Auto",          "cik": "0001874178"},
    {"company": "Unity",         "ticker": "U",     "ipo_date": "2020-09-18", "sector": "Gaming/Dev Tools", "cik": "0001810806"},
    {"company": "Roblox",        "ticker": "RBLX",  "ipo_date": "2021-03-10", "sector": "Gaming",           "cik": "0001315098"},
    {"company": "Bumble",        "ticker": "BMBL",  "ipo_date": "2021-02-11", "sector": "Social/Dating",    "cik": "0001830043"},
    {"company": "Affirm",        "ticker": "AFRM",  "ipo_date": "2021-01-13", "sector": "Fintech",          "cik": "0001820953"},
    {"company": "Robinhood",     "ticker": "HOOD",  "ipo_date": "2021-07-29", "sector": "Fintech",          "cik": "0001783879"},
    {"company": "Toast",         "ticker": "TOST",  "ipo_date": "2021-09-22", "sector": "Restaurant Tech",  "cik": "0001650164"},
    {"company": "Confluent",     "ticker": "CFLT",  "ipo_date": "2021-06-24", "sector": "Data Streaming",   "cik": "0001820630"},
    {"company": "GitLab",        "ticker": "GTLB",  "ipo_date": "2021-10-14", "sector": "DevOps",           "cik": "0001653482"},
    {"company": "HashiCorp",     "ticker": "HCP",   "ipo_date": "2021-12-09", "sector": "Cloud Infra",      "cik": "0001720671"},
    {"company": "Duolingo",      "ticker": "DUOL",  "ipo_date": "2021-07-28", "sector": "EdTech",           "cik": "0001562088"},
    {"company": "Instacart",     "ticker": "CART",  "ipo_date": "2023-09-19", "sector": "Delivery",         "cik": "0001579091"},
    {"company": "Klaviyo",       "ticker": "KVYO",  "ipo_date": "2023-09-20", "sector": "Marketing Tech",   "cik": "0001826168"},
    {"company": "Arm Holdings",  "ticker": "ARM",   "ipo_date": "2023-09-14", "sector": "Semiconductors",   "cik": "0001973239"},
    {"company": "Reddit",        "ticker": "RDDT",  "ipo_date": "2024-03-21", "sector": "Social Media",     "cik": "0001713445"},
    {"company": "Rubrik",        "ticker": "RBRK",  "ipo_date": "2024-04-25", "sector": "Cybersecurity",    "cik": "0001943896"},
    {"company": "Astera Labs",   "ticker": "ALAB",  "ipo_date": "2024-03-20", "sector": "Semiconductors",   "cik": "0001838293"},
    {"company": "Ibotta",        "ticker": "IBTA",  "ipo_date": "2024-04-18", "sector": "Fintech",          "cik": "0001496268"},
]


def get_tickers():
    return [c["ticker"] for c in COMPANIES]


def get_company_by_ticker(ticker):
    return next((c for c in COMPANIES if c["ticker"] == ticker), None)

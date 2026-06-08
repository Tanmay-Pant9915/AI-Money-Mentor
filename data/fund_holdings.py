"""
data/fund_holdings.py — MVP Fund Holdings Database
===================================================

In production this data comes from:
  - AMC monthly portfolio disclosures (SEBI-mandated)
  - Value Research / Morning Star API
  - AMFI data feeds

For the MVP we maintain a static snapshot matching the scheme names in
data/expense_ratios.py plus two demo funds so the overlap feature
works immediately without an external API.

Add new schemes here as you onboard real portfolio data.
Holdings are top-10 stocks (approximate) for each fund.
"""

FUND_HOLDINGS: dict[str, list[str]] = {
    # Matches expense_ratios.py — will auto-appear when a real CAMS PDF is parsed.
    "ABC Large Cap Fund - Direct Growth": [
        "Reliance Industries",
        "HDFC Bank",
        "Infosys",
        "TCS",
        "ICICI Bank",
        "Larsen & Toubro",
        "Axis Bank",
        "Kotak Mahindra Bank",
        "ITC",
        "Bharti Airtel",
    ],
    "XYZ Flexi Cap Fund - Direct Growth": [
        "Reliance Industries",
        "Infosys",
        "TCS",
        "HDFC Bank",
        "Sun Pharma",
        "Maruti Suzuki",
        "Bajaj Finance",
        "Wipro",
        "HCL Technologies",
        "Titan Company",
    ],
    # ---------------------------------------------------------------------------
    # Demo funds — used for built-in MVPdemo mode and tests.
    # ---------------------------------------------------------------------------
    "Fund A": [
        "Reliance Industries",
        "TCS",
        "Infosys",
    ],
    "Fund B": [
        "Reliance Industries",
        "Infosys",
        "ICICI Bank",
    ],
    # ---------------------------------------------------------------------------
    # ---------------------------------------------------------------------------
    # Realistic Indian Mutual Fund Holdings Snapshot
    # ---------------------------------------------------------------------------
    "Axis Bluechip Fund - Direct Growth": [
        "Axis Bank",
        "Bajaj Finance",
        "Bharti Airtel",
        "HCL Technologies",
        "HDFC Bank",
        "ICICI Bank",
        "ITC",
        "Infosys",
        "Kotak Mahindra Bank",
        "Larsen & Toubro",
        "Mahindra & Mahindra",
        "Maruti Suzuki",
        "NTPC",
        "Power Grid",
        "Reliance Industries",
        "SBI",
        "Sun Pharma",
        "TCS",
        "Tata Motors",
        "Titan Company",
    ],
    "UTI Nifty 50 Index Fund - Direct Growth": [
        "Adani Ports",
        "Asian Paints",
        "Bharti Airtel",
        "Coal India",
        "HCL Technologies",
        "HDFC Bank",
        "ICICI Bank",
        "ITC",
        "Infosys",
        "Jindal Steel",
        "Jio Financial Services",
        "Kotak Mahindra Bank",
        "Larsen & Toubro",
        "Mahindra & Mahindra",
        "Power Grid",
        "Reliance Industries",
        "SBI",
        "Sun Pharma",
        "TCS",
        "Titan Company",
    ],
    "Parag Parikh Flexi Cap Fund - Direct Growth": [
        "Alphabet Inc",
        "Amazon.com",
        "Axis Bank",
        "Bajaj Holdings",
        "CDSL",
        "HDFC AMC",
        "HDFC Bank",
        "ICICI Bank",
        "Infosys",
        "MCX India",
        "Maruti Suzuki",
        "Meta Platforms",
        "Microsoft Corp",
        "NTPC",
        "Reliance Industries",
        "SBI",
        "Sun Pharma",
        "TCS",
        "Tata Motors",
        "Titan Company",
    ],
    "Kotak Emerging Equity Fund - Direct Growth": [
        "Aarti Industries",
        "Bajaj Finance",
        "Bharat Electronics",
        "Coromandel International",
        "Cummins India",
        "Federal Bank",
        "HDFC Bank",
        "ICICI Bank",
        "IPCA Laboratories",
        "Infosys",
        "MRF",
        "Persistent Systems",
        "Polycab India",
        "Reliance Industries",
        "SBI",
        "Solar Industries",
        "TCS",
        "Titan Company",
        "Trent",
        "Voltas",
    ],
    "Nippon India Small Cap Fund - Direct Growth": [
        "Bank of Baroda",
        "Birlasoft",
        "CEAT",
        "Carborundum Universal",
        "Cholamandalam Financial",
        "Coforge",
        "Cyient",
        "Glenmark Pharma",
        "Grindwell Norton",
        "HBL Power Systems",
        "HDFC Bank",
        "ICICI Bank",
        "KPIT Technologies",
        "Kirloskar Pneumatic",
        "Multi Commodity Exchange",
        "Reliance Industries",
        "SBI",
        "Tejas Networks",
        "Tube Investments",
        "eMudhra",
    ],
}


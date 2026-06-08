# 💰 AI Money Mentor

> AI-Powered Mutual Fund Portfolio X-Ray & Wealth Analysis Platform

AI Money Mentor helps Indian mutual fund investors understand their true portfolio performance by analyzing CAMS Consolidated Account Statements (CAS), calculating XIRR, measuring expense drag, detecting fund overlap, benchmarking against market indices, and generating AI-powered portfolio insights.

---

## 🌐 Live Demo

**Application:** https://ai-money-mentor-ub96dcmvkptpsttmsk5a7w.streamlit.app/

**GitHub Repository:** https://github.com/Tanmay-Pant9915/AI-Money-Mentor

---

# 🚀 Features

### 📄 CAMS Statement Processing

* Upload CAMS Consolidated Account Statement (CAS) PDFs
* Automatic extraction of holdings, folio numbers, units, NAV, and transaction history
* Multi-fund portfolio support

### 📈 True Portfolio Return Analysis

* XIRR (Extended Internal Rate of Return) calculation
* Transaction-aware annualized return measurement
* Portfolio-level weighted return analysis

### 💸 Expense Drag Analysis

* Fund-wise expense ratio tracking
* Annual fee impact estimation
* Portfolio-wide cost drag calculation

### 🔄 Fund Overlap Detection

* Pairwise overlap matrix
* Jaccard Similarity based overlap analysis
* Concentrated stock identification
* Common holdings frequency analysis

### 📊 Benchmark Comparison

Compare performance against:

* Nifty 50
* Sensex
* Midcap Index
* Smallcap Index

Features:

* Alpha analysis
* Outperforming vs underperforming fund detection
* Benchmark visualization

### 🤖 AI Portfolio Mentor

Powered by Groq + Llama 3.3 70B.

Provides:

* Portfolio health assessment
* Returns analysis
* Expense analysis
* Risk identification
* Actionable recommendations

### 📉 Interactive Visualizations

* Portfolio allocation charts
* XIRR comparison charts
* Expense drag charts
* Overlap frequency charts
* Benchmark performance visualizations

---

# 🛠️ Tech Stack

## Frontend

* Streamlit
* Plotly

## Backend & Analytics

* Python
* Pandas
* SciPy

## Financial Computation

* Newton-Raphson Solver
* XIRR Engine
* Jaccard Similarity Analysis

## PDF Processing

* pdfplumber

## AI Layer

* Groq Cloud SDK
* Llama 3.3 70B Versatile

## Testing

* Pytest

## Deployment

* GitHub
* Streamlit Community Cloud

---

# 🏗️ System Architecture

CAS PDF Upload

↓

PDF Parsing Engine

↓

Portfolio Extraction Layer

↓

Analytics Engine

├── XIRR Calculation

├── Expense Drag Analysis

├── Fund Overlap Detection

└── Benchmark Comparison

↓

AI Recommendation Engine

↓

Interactive Dashboard

---

# 📊 Mathematical Models

## XIRR (Extended Internal Rate of Return)

The application computes annualized returns by solving:

NPV = Σ(Cᵢ / (1+r)^((dᵢ-d₁)/365))

Where:

* Cᵢ = Cashflow amount
* dᵢ = Transaction date
* r = Annualized return

The equation is solved numerically using SciPy's Newton-Raphson method.

---

## Fund Overlap Detection

Overlap between two funds is calculated using Jaccard Similarity:

Overlap % = |A ∩ B| / |A ∪ B| × 100

Where:

* A = Holdings of Fund A
* B = Holdings of Fund B

This identifies duplicate exposure across mutual funds.

---

# 🧪 Testing

Current Status:

✅ 60 / 60 Tests Passing

Coverage Includes:

* PDF Parsing
* Portfolio Extraction
* XIRR Calculations
* Expense Drag Analysis
* Benchmark Analytics
* Overlap Detection
* Portfolio Analysis Pipeline

Run tests:

```bash
uv run pytest -v
```

---

# ⚙️ Local Setup

### Clone Repository

```bash
git clone https://github.com/Tanmay-Pant9915/AI-Money-Mentor.git

cd AI-Money-Mentor
```

### Create Virtual Environment

```bash
uv venv
```

Activate:

Windows:

```bash
.venv\Scripts\activate
```

### Install Dependencies

```bash
uv pip install -r requirements.txt
```

### Configure API Key

Create a `.env` file:

```env
GROQ_API_KEY=your_groq_api_key
```

### Run Application

```bash
uv run streamlit run app.py
```

---

# 🔒 Privacy & Security

* Uploaded PDFs are processed locally during analysis.
* Temporary PDF files are automatically deleted after processing.
* API keys are stored securely using environment variables or Streamlit Secrets.
* No user portfolio data is permanently stored.

---

# 🔮 Future Roadmap

### Portfolio Analytics

* Historical NAV Integration
* Portfolio Timeline Analysis
* SIP Performance Tracking
* Goal-Based Investing Analysis

### Optimization Features

* Portfolio Rebalancing Suggestions
* Risk Scoring Engine
* Asset Allocation Analysis

### Data Infrastructure

* Live Mutual Fund Data APIs
* Persistent Portfolio Storage
* User Authentication

### Reporting

* Downloadable PDF Reports
* Portfolio Sharing
* Automated Monthly Reviews

---

# 👨‍💻 Author

**Tanmay Pant**

B.Tech Computer Science Engineering

Manipal University Jaipur

---

# ⭐ Project Impact

Most retail investors only see current portfolio value.

AI Money Mentor converts raw mutual fund statements into actionable financial intelligence by helping investors understand:

* What they actually earned (XIRR)
* How much fees reduce returns
* Whether funds overlap excessively
* How they compare against benchmarks
* What actions can improve portfolio quality

The objective is to make professional-grade portfolio analysis accessible to everyday investors.

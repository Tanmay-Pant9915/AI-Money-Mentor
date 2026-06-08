# 💰 AI Money Mentor

> **A Smart Portfolio X-Ray & AI-Powered Wealth Advisor for Indian Mutual Funds.**

AI Money Mentor parses standard CAMS CAS statements to calculate your true annualized returns (XIRR), expose hidden fees (Expense Drag), detect overlap risks across funds, and deliver grounded, compliant investment advice.

---

## 🚀 Key Features

*   **Smart PDF CAS Ingestion:** Extract transaction logs and portfolio holdings from Consolidated Account Statements.
*   **True Return Analytics (XIRR):** Utilizes numerical solvers (Newton-Raphson) to compute your exact annualized internal rate of return based on transaction dates.
*   **Expense Cost Drag:** Visualizes the long-term impact of expense ratios, highlighting how much you pay in fees every year.
*   **Fund Overlap & Risk Detection:** Employs Jaccard Similarity to find overlapping stock holdings and flag concentration risks.
*   **Interactive Benchmarking:** Live comparison against Nifty 50, Sensex, Midcap, and Smallcap indexes with customizable time horizons.
*   **Grounded AI Advisory:** Integrated Groq LLM (Llama 3.3 70B) acting as a SEBI-registered advisor providing hallucination-free portfolio health reports.

---

## 🛠️ Architecture & Tech Stack

*   **Frontend:** [Streamlit](https://streamlit.io/) (Responsive, custom CSS variables, dynamic Plotly visualisations)
*   **Engine & Math:** [SciPy](https://scipy.org/) (Newton-Raphson Solver), [Pandas](https://pandas.pydata.org/) (Data processing)
*   **PDF Extraction:** [pdfplumber](https://github.com/samkit-w/pdfplumber)
*   **LLM Core:** [Groq Cloud SDK](https://groq.com/) (Llama-3.3-70B-Versatile)
*   **Tests:** [Pytest](https://pytest.org/) (53 unit tests validating math, parsing, and pipeline edge cases)

---

## 🏃 Getting Started

### Prerequisites
*   Python 3.10+
*   Groq API Key

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/ai-money-mentor.git
   cd ai-money-mentor
   ```

2. Set up a virtual environment and install dependencies:
   ```bash
   pip install uv  # Highly recommended
   uv venv
   .venv\Scripts\activate  # On Windows
   uv sync
   ```

3. Create a `.env` file in the root directory:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   ```

4. Run the Streamlit application:
   ```bash
   uv run streamlit run app.py
   ```

5. Run the test suite:
   ```bash
   uv run pytest -v
   ```

---

## 📊 Math & Methodology

### 1. Annualized Returns (XIRR)
Calculated by solving for $r$ in the Net Present Value equation:
$$NPV = \sum_{i=1}^{n} \frac{C_i}{(1 + r)^{\frac{d_i - d_1}{365}}} = 0$$
Where $C_i$ is the cashflow amount on date $d_i$.

### 2. Fund Overlap (Jaccard Similarity)
Identifies duplicate exposure across funds $A$ and $B$:
$$\text{Overlap \%} = \frac{|H_A \cap H_B|}{|H_A \cup H_B|} \times 100$$
Where $H$ is the set of stock holdings.

---

## 📜 License
Distributed under the MIT License. See `LICENSE` for more information.

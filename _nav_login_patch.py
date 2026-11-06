"""
Patch script: 
1. Moves navigation from sidebar to horizontal top navbar
2. Keeps sidebar for file upload only  
3. Adds login/logout system
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

content = open('c:/Users/Jai/Desktop/AI-Money-Mentor/app.py', 'r', encoding='utf-8').read()

# ─────────────────────────────────────────────────────────────────
# 1. ADD CSS for horizontal top navbar + login page styles
# ─────────────────────────────────────────────────────────────────
NAV_CSS = """
    /* ─── Top Horizontal Navbar (radio disguised) ─────────────── */
    /* Hide the radio label "Navigation" */
    div[data-testid="stRadio"] > label { display: none !important; }

    /* Row layout for the radio options */
    div[data-testid="stRadio"] > div[role="radiogroup"] {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: wrap !important;
        gap: 2px !important;
        background: rgba(13, 13, 22, 0.85) !important;
        padding: 5px 6px !important;
        border-radius: 14px !important;
        border: 1px solid rgba(99, 102, 241, 0.18) !important;
        margin-bottom: 20px !important;
        backdrop-filter: blur(10px) !important;
    }

    /* Each nav item */
    div[data-testid="stRadio"] [data-baseweb="radio"] {
        padding: 7px 14px !important;
        border-radius: 9px !important;
        cursor: pointer !important;
        transition: all 0.2s ease !important;
        margin: 0 !important;
    }

    /* Hide the actual circle dot */
    div[data-testid="stRadio"] [data-baseweb="radio"] > div:first-child {
        display: none !important;
    }

    /* Label text */
    div[data-testid="stRadio"] [data-baseweb="radio"] > div:last-child {
        color: #64748b !important;
        font-size: 0.82rem !important;
        font-weight: 500 !important;
        line-height: 1 !important;
        margin: 0 !important;
    }

    /* Hover state */
    div[data-testid="stRadio"] [data-baseweb="radio"]:hover {
        background: rgba(99, 102, 241, 0.1) !important;
    }
    div[data-testid="stRadio"] [data-baseweb="radio"]:hover > div:last-child {
        color: #c7d2fe !important;
    }

    /* Selected/active state */
    div[data-testid="stRadio"] [aria-checked="true"] {
        background: rgba(99, 102, 241, 0.2) !important;
    }
    div[data-testid="stRadio"] [aria-checked="true"] > div:last-child {
        color: #a5b4fc !important;
        font-weight: 650 !important;
    }

    /* ─── Login page ───────────────────────────────────────────── */
    .login-card {
        max-width: 420px;
        margin: 80px auto 0 auto;
        background: linear-gradient(145deg, rgba(22, 22, 36, 0.95), rgba(13, 13, 22, 0.98));
        border: 1px solid rgba(99, 102, 241, 0.2);
        border-radius: 20px;
        padding: 40px 36px 36px 36px;
        box-shadow: 0 20px 60px rgba(0,0,0,0.5), 0 0 0 1px rgba(99,102,241,0.08);
        text-align: center;
    }
    .login-logo {
        font-size: 2.8rem;
        margin-bottom: 8px;
    }
    .login-title {
        font-size: 1.6rem;
        font-weight: 800;
        background: linear-gradient(135deg, #f1f5f9, #a5b4fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 4px;
    }
    .login-subtitle {
        font-size: 0.85rem;
        color: #475569;
        margin-bottom: 28px;
    }

    /* ─── Slim sidebar (no nav, just upload) ───────────────────── */
    [data-testid="stSidebar"] .stRadio { display: none !important; }
    """

# Inject navbar + login CSS before closing </style>
old_close = '        </style>'
content = content.replace(old_close, NAV_CSS + '        </style>', 1)

# ─────────────────────────────────────────────────────────────────
# 2. ADD login logic + auth gate AFTER session state init block
# ─────────────────────────────────────────────────────────────────
LOGIN_CODE = '''
# ─── Authentication ───────────────────────────────────────────────────────────
# Default demo credentials. In production add a [users] section to
# .streamlit/secrets.toml:  admin = "your_secure_password"
_DEFAULT_USERS = {"admin": "admin123", "demo": "demo"}
try:
    _USERS = dict(st.secrets.get("users", _DEFAULT_USERS))
except Exception:
    _USERS = _DEFAULT_USERS


def _render_login():
    """Full-page premium login screen."""
    st.markdown(
        """
        <div class="login-card">
            <div class="login-logo">💰</div>
            <div class="login-title">AI Money Mentor</div>
            <div class="login-subtitle">AI-Powered Portfolio Intelligence</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    # Centre the form under the card
    _, col, _ = st.columns([1, 1.6, 1])
    with col:
        st.markdown("<br>", unsafe_allow_html=True)
        with st.form("login_form", clear_on_submit=False):
            username = st.text_input("Username", placeholder="Enter username")
            password = st.text_input("Password", type="password", placeholder="Enter password")
            submitted = st.form_submit_button("Sign In", use_container_width=True, type="primary")

        if submitted:
            if _USERS.get(username) == password:
                st.session_state["authenticated"] = True
                st.session_state["login_user"] = username
                st.rerun()
            else:
                st.error("❌ Invalid username or password.")

        st.markdown(
            '<p style="text-align:center;color:#334155;font-size:0.78rem;margin-top:16px;">'
            'Demo — username: <b>demo</b> &nbsp;|&nbsp; password: <b>demo</b></p>',
            unsafe_allow_html=True,
        )


# Auth gate — block everything below until signed in
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "login_user" not in st.session_state:
    st.session_state["login_user"] = None

if not st.session_state["authenticated"]:
    _render_login()
    st.stop()

'''

# Insert login code right after the CSS/markdown block ends (after the closing paren + blank line)
INSERT_AFTER = 'if "result" not in st.session_state:'
content = content.replace(INSERT_AFTER, LOGIN_CODE + 'if "result" not in st.session_state:', 1)

# ─────────────────────────────────────────────────────────────────
# 3. REPLACE sidebar title/subtitle + sidebar radio nav
#    with slim sidebar (logo only, no nav)
# ─────────────────────────────────────────────────────────────────
OLD_SIDEBAR_HEADER = '''st.sidebar.title("💰 AI Money Mentor")
st.sidebar.markdown('<p style="color:#64748b;font-size:0.8rem;margin-top:-10px;">AI-Powered Portfolio Intelligence</p>', unsafe_allow_html=True)

nav_options = [
    "📊 CAMS Portfolio Analysis",
    "👤 Financial Profile",
    "🎯 Risk Assessment",
    "🩺 Money Health Score",
    "📋 Financial Planning & Budgeting",
    "🎯 Goal Investment Planning",
    "🏖️ FIRE & Retirement Planning",
    "🛡️ Emergency Fund & Insurance Planning",
    "🏷️ Tax Optimization & Planning",
    "🤖 AI Financial Mentor",
]
default_index = 0
if "nav_override" in st.session_state and st.session_state["nav_override"] in nav_options:
    default_index = nav_options.index(st.session_state.pop("nav_override"))

nav_selection = st.sidebar.radio(
    "Navigation",
    nav_options,
    index=default_index,
)
st.sidebar.divider()'''

NEW_SIDEBAR_HEADER = '''# ── Slim Sidebar: logo + file upload + logout only ───────────────────────────
with st.sidebar:
    st.markdown(
        """
        <div style="text-align:center;padding:16px 0 12px 0;">
            <div style="font-size:2rem;">💰</div>
            <div style="font-size:1rem;font-weight:800;background:linear-gradient(135deg,#f1f5f9,#a5b4fc);
                        -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                        background-clip:text;">AI Money Mentor</div>
            <div style="font-size:0.72rem;color:#475569;margin-top:2px;">Portfolio Intelligence</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.divider()

    # ── CAMS upload lives here exclusively ────────────────────────
    st.markdown('<p style="color:#64748b;font-size:0.78rem;font-weight:700;text-transform:uppercase;letter-spacing:1px;">Portfolio Upload</p>', unsafe_allow_html=True)

    # ── Logged-in user badge ──────────────────────────────────────
    _user_label = st.session_state.get("login_user", "user")
    st.markdown(
        f'<div style="background:rgba(99,102,241,0.1);border:1px solid rgba(99,102,241,0.25);'
        f'border-radius:8px;padding:6px 10px;font-size:0.78rem;color:#a5b4fc;margin-bottom:12px;">'
        f'👤 Signed in as <b>{_user_label}</b></div>',
        unsafe_allow_html=True,
    )

    if st.button("🚪 Sign Out", use_container_width=True, key="logout_btn"):
        for _k in list(st.session_state.keys()):
            del st.session_state[_k]
        st.rerun()

    st.divider()

# ── Top horizontal navigation bar ────────────────────────────────────────────
nav_options = [
    "📊 Portfolio",
    "👤 Profile",
    "🎯 Risk",
    "🩺 Health",
    "📋 Budget",
    "🏹 Goals",
    "🏖️ FIRE",
    "🛡️ Protection",
    "🏷️ Tax",
    "🤖 AI Mentor",
]

# Map short labels → full route keys used in routing below
_NAV_MAP = {
    "📊 Portfolio":    "📊 CAMS Portfolio Analysis",
    "👤 Profile":      "👤 Financial Profile",
    "🎯 Risk":         "🎯 Risk Assessment",
    "🩺 Health":       "🩺 Money Health Score",
    "📋 Budget":       "📋 Financial Planning & Budgeting",
    "🏹 Goals":        "🎯 Goal Investment Planning",
    "🏖️ FIRE":        "🏖️ FIRE & Retirement Planning",
    "🛡️ Protection":  "🛡️ Emergency Fund & Insurance Planning",
    "🏷️ Tax":         "🏷️ Tax Optimization & Planning",
    "🤖 AI Mentor":   "🤖 AI Financial Mentor",
}

# Resolve nav_override (set by other views via st.session_state["nav_override"])
_FULL_TO_SHORT = {v: k for k, v in _NAV_MAP.items()}
default_index = 0
if "nav_override" in st.session_state and st.session_state["nav_override"] in _FULL_TO_SHORT:
    _short = _FULL_TO_SHORT[st.session_state.pop("nav_override")]
    if _short in nav_options:
        default_index = nav_options.index(_short)

nav_short = st.radio(
    "Navigation",
    nav_options,
    index=default_index,
    horizontal=True,
    key="main_nav",
)
nav_selection = _NAV_MAP[nav_short]'''

content = content.replace(OLD_SIDEBAR_HEADER, NEW_SIDEBAR_HEADER, 1)

# ─────────────────────────────────────────────────────────────────
# 4. MOVE file upload OUT of the else block into the sidebar
#    and simplify the else block so it doesn't duplicate sidebar controls
# ─────────────────────────────────────────────────────────────────
OLD_ELSE_BLOCK_START = '''else:
    st.sidebar.subheader("Portfolio Control Panel")

    uploaded_file = st.sidebar.file_uploader(
        "Upload CAMS CAS PDF",
        type=["pdf"]
    )

    if uploaded_file:
        if st.session_state.uploaded_file_name != uploaded_file.name:
            st.session_state.result = None
            st.session_state.summary = None
            st.session_state.uploaded_file_name = uploaded_file.name

    if st.session_state.result is not None:
        if st.sidebar.button("🧹 Clear & Reset", use_container_width=True):
            st.session_state.result = None
            st.session_state.summary = None
            st.session_state.uploaded_file_name = None
            st.rerun()

    st.sidebar.divider()
    st.sidebar.markdown(
        """
        ### 📂 How to get your statement:
        1. Request a **Consolidated Account Statement (CAS)** from [CAMS Online](https://www.camsonline.com/).
        2. Choose **Detailed** statement (includes transaction history for XIRR calculation).
        3. Enter a password if required.
        4. Download the PDF statement.
        """
    )

    st.title("💰 AI Money Mentor")
    st.caption("Mutual Fund Portfolio X-Ray & AI-Powered Advisory")
    st.divider()

    if uploaded_file and st.session_state.result is None:
        if st.sidebar.button("🚀 Analyze Portfolio", type="primary", use_container_width=True):'''

NEW_ELSE_BLOCK_START = '''else:
    # ── File upload in sidebar ────────────────────────────────────────────────
    with st.sidebar:
        uploaded_file = st.file_uploader(
            "Upload CAMS CAS PDF",
            type=["pdf"],
            label_visibility="collapsed",
        )

        if uploaded_file:
            if st.session_state.uploaded_file_name != uploaded_file.name:
                st.session_state.result = None
                st.session_state.summary = None
                st.session_state.uploaded_file_name = uploaded_file.name

            if st.session_state.result is None:
                if st.button("🚀 Analyze Portfolio", type="primary", use_container_width=True, key="analyze_btn"):
                    _do_analyze = True
                else:
                    _do_analyze = False
            else:
                _do_analyze = False

            if st.session_state.result is not None:
                if st.button("🧹 Clear & Reset", use_container_width=True, key="clear_btn"):
                    st.session_state.result = None
                    st.session_state.summary = None
                    st.session_state.uploaded_file_name = None
                    st.rerun()
        else:
            uploaded_file = None
            _do_analyze = False

        st.divider()
        st.markdown(
            '<p style="color:#475569;font-size:0.74rem;line-height:1.6;">'
            '📂 Get your <b>Consolidated Account Statement</b> from '
            '<a href="https://www.camsonline.com/" target="_blank" style="color:#818cf8;">CAMS Online</a>. '
            'Choose <b>Detailed</b> format for XIRR calculation.</p>',
            unsafe_allow_html=True,
        )

    st.title("💰 AI Money Mentor")
    st.caption("Mutual Fund Portfolio X-Ray & AI-Powered Advisory")
    st.divider()

    if _do_analyze:
        try:'''

content = content.replace(OLD_ELSE_BLOCK_START, NEW_ELSE_BLOCK_START, 1)

# Fix the try block that was originally under "if st.sidebar.button(...)"
# The old code had an extra indentation level - we need to fix the analyze block
OLD_ANALYZE_TRY = '''            try:
                with st.spinner("Analyzing Statement..."):
                    with open("temp.pdf", "wb") as f:
                        f.write(uploaded_file.getbuffer())

                    # Step 1: Extract PDF text — may raise PDFReadError or EmptyPDFError.
                    text = extract_text("temp.pdf")

                    # Step 2: Parse fund blocks from text.
                    df = parse_funds(text)

                    if df.empty:
                        st.error(
                            "❌ **No mutual fund data found.** "
                            "The PDF was readable but contained no CAMS scheme blocks. "
                            "Please upload a **Detailed** CAMS Consolidated Account Statement."
                        )
                        st.stop()

                    # Step 3: Run portfolio analysis (XIRR + expense drag + overlap + benchmark).
                    result, overlap_report, benchmark_report = analyze_portfolio(df)
                    st.session_state.result = result
                    st.session_state.overlap_report = overlap_report
                    st.session_state.benchmark_report = benchmark_report

                    # Step 4: Generate LLM recommendations.
                    # ai_summary never raises — returns a user-friendly string on any error.
                    ai_df = result.drop(columns=["transactions"], errors="ignore")
                    portfolio_json = ai_df.to_dict(orient="records")

                with st.spinner("Consulting AI Money Mentor..."):
                    summary = generate_portfolio_summary(portfolio_json)
                    st.session_state.summary = summary

                st.success("✅ Analysis Complete!")
                st.rerun()

            except PDFReadError as exc:
                st.error(
                    f"❌ **Could not read the PDF.** {exc} "
                    "\\n\\nMake sure you uploaded a valid, non-encrypted CAMS PDF."
                )

            except EmptyPDFError as exc:
                st.error(f"❌ **PDF has no readable text.** {exc}")

            except ValueError as exc:
                # Raised by analyze_portfolio for missing columns or empty DataFrames.
                st.error(f"❌ **Portfolio data error:** {exc}")

            except OSError as exc:
                st.error(
                    f"❌ **File system error** while saving the uploaded PDF: {exc}"
                )

            except Exception:
                st.error(
                    "❌ **An unexpected error occurred.** "
                    "Please try re-uploading your statement."
                )

            finally:
                # Always clean up the temporary PDF — never persist user data to disk.
                if os.path.exists("temp.pdf"):
                    os.remove("temp.pdf")'''

NEW_ANALYZE_TRY = '''        with st.spinner("Analyzing Statement..."):
            with open("temp.pdf", "wb") as f:
                f.write(uploaded_file.getbuffer())

            # Step 1: Extract PDF text — may raise PDFReadError or EmptyPDFError.
            text = extract_text("temp.pdf")

            # Step 2: Parse fund blocks from text.
            df = parse_funds(text)

            if df.empty:
                st.error(
                    "❌ **No mutual fund data found.** "
                    "The PDF was readable but contained no CAMS scheme blocks. "
                    "Please upload a **Detailed** CAMS Consolidated Account Statement."
                )
                st.stop()

            # Step 3: Run portfolio analysis (XIRR + expense drag + overlap + benchmark).
            result, overlap_report, benchmark_report = analyze_portfolio(df)
            st.session_state.result = result
            st.session_state.overlap_report = overlap_report
            st.session_state.benchmark_report = benchmark_report

            # Step 4: Generate LLM recommendations.
            ai_df = result.drop(columns=["transactions"], errors="ignore")
            portfolio_json = ai_df.to_dict(orient="records")

        with st.spinner("Consulting AI Money Mentor..."):
            summary = generate_portfolio_summary(portfolio_json)
            st.session_state.summary = summary

        st.success("✅ Analysis Complete!")
        st.rerun()

    except PDFReadError as exc:
        st.error(
            f"❌ **Could not read the PDF.** {exc} "
            "\\n\\nMake sure you uploaded a valid, non-encrypted CAMS PDF."
        )
    except EmptyPDFError as exc:
        st.error(f"❌ **PDF has no readable text.** {exc}")
    except ValueError as exc:
        st.error(f"❌ **Portfolio data error:** {exc}")
    except OSError as exc:
        st.error(f"❌ **File system error** while saving the uploaded PDF: {exc}")
    except Exception:
        st.error("❌ **An unexpected error occurred.** Please try re-uploading your statement.")
    finally:
        if os.path.exists("temp.pdf"):
            os.remove("temp.pdf")'''

content = content.replace(OLD_ANALYZE_TRY, NEW_ANALYZE_TRY, 1)

open('c:/Users/Jai/Desktop/AI-Money-Mentor/app.py', 'w', encoding='utf-8').write(content)
print("Patch written. Running syntax check...")

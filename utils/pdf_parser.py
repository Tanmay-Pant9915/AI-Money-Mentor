import re

import pandas as pd
import pdfplumber
import streamlit as st


class PDFReadError(Exception):
    """Raised when the PDF file cannot be opened or read."""


class EmptyPDFError(Exception):
    """Raised when the PDF opens but contains no extractable text."""


def extract_text(pdf_path: str) -> str:
    """
    Open a PDF and return all extractable text.

    Raises:
        PDFReadError:  File is missing, corrupted, encrypted, or not a PDF.
        EmptyPDFError: File opened fine but every page is blank / image-only.
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            pages_text = []
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    pages_text.append(page_text)

    except FileNotFoundError:
        raise PDFReadError(f"PDF not found: {pdf_path}")
    except Exception as exc:
        # pdfplumber raises generic exceptions for encrypted/corrupt files.
        raise PDFReadError(
            f"Could not open PDF. It may be corrupted, encrypted, or not a "
            f"valid PDF file. Details: {exc}"
        )

    if not pages_text:
        raise EmptyPDFError(
            "The PDF contains no readable text. "
            "It may be a scanned image PDF. Please use a text-based CAMS statement."
        )

    return "\n".join(pages_text)


def _parse_fund_block(block: str) -> dict | None:
    """
    Parse a single Scheme block into a fund dict.
    Returns None if the block cannot be meaningfully parsed.
    """
    if "Scheme:" not in block:
        return None

    fund: dict = {}

    # Scheme name — mandatory; skip block entirely if absent.
    name_match = re.search(r"Scheme:\s*(.+)", block)
    if not name_match:
        return None
    fund["scheme"] = name_match.group(1).strip()

    # Optional fields — individual parse failures produce None, not a crash.
    folio_match = re.search(
        r"Folio\s*(?:No\.?\s*)?[:\-]?\s*(\S+)", block, re.IGNORECASE
    )
    fund["folio"] = folio_match.group(1).strip() if folio_match else None

    try:
        units_match = re.search(r"Units Held:\s*([\d.]+)", block)
        fund["units"] = float(units_match.group(1)) if units_match else None
    except (AttributeError, ValueError):
        fund["units"] = None

    try:
        nav_match = re.search(r"NAV:\s*n?([\d.,]+)", block)
        fund["nav"] = (
            float(nav_match.group(1).replace(",", "")) if nav_match else None
        )
    except (AttributeError, ValueError):
        fund["nav"] = None

    try:
        value_match = re.search(r"Current Value:\s*n?([\d.,]+)", block)
        fund["current_value"] = (
            float(value_match.group(1).replace(",", "")) if value_match else None
        )
    except (AttributeError, ValueError):
        fund["current_value"] = None

    # Transactions — each row parsed independently so one bad row won't drop the fund.
    txn_pattern = re.findall(
        r"(\d{2}-\w{3}-\d{4})\s*\|\s*([^|]+)\s*\|\s*n?([\d.,]+)", block
    )
    transactions = []
    for t in txn_pattern:
        try:
            transactions.append(
                {
                    "date": pd.to_datetime(t[0], format="%d-%b-%Y").to_pydatetime(),
                    "type": t[1].strip(),
                    "amount": float(t[2].replace(",", "")),
                }
            )
        except (ValueError, OverflowError):
            # Skip individual malformed transaction rows silently.
            continue

    fund["transactions"] = transactions
    return fund


@st.cache_data
def parse_funds(text: str) -> pd.DataFrame:
    """
    Split PDF text into per-scheme blocks and parse each one.

    Silently skips unparseable blocks so one bad fund doesn't lose all data.
    Returns an empty DataFrame (with correct columns) if nothing was parsed.
    """
    blocks = re.split(r"(?=Scheme:)", text)
    funds = []

    for block in blocks:
        try:
            fund = _parse_fund_block(block)
            if fund is not None:
                funds.append(fund)
        except Exception:
            # A completely unexpected error in one block should not stop others.
            continue

    if not funds:
        return pd.DataFrame(
            columns=["scheme", "folio", "units", "nav", "current_value", "transactions"]
        )

    return pd.DataFrame(funds)

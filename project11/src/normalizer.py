"""Turn imported rows into normalized transactions: clean merchant, type, category."""
from __future__ import annotations

import difflib
import re

import pandas as pd

ESSENTIAL = "Essential"
DISCRETIONARY = "Discretionary"
AVOIDABLE = "Potentially avoidable"
UNKNOWN = "Unknown"

OTHER = "Other expenses"
CATEGORY_CLASS = {
    "Food delivery": AVOIDABLE,
    "Cafes & snacks": AVOIDABLE,
    "Subscriptions": DISCRETIONARY,
    "Shopping": DISCRETIONARY,
    "Entertainment": DISCRETIONARY,
    "Groceries": ESSENTIAL,
    "Transport": ESSENTIAL,
    "Mobile & internet": ESSENTIAL,
    "Education": ESSENTIAL,
    "Healthcare": ESSENTIAL,
    "Bills & rent": ESSENTIAL,
    OTHER: UNKNOWN,
}

# Order matters: the first match wins.
CATEGORY_RULES = [
    ("Food delivery", r"food\s*panda|uber\s*eats|deliveroo|doordash|grubhub|swiggy|zomato|talabat"
                      r"|careem\s*food|bykea\s*food|food\s*delivery"),
    ("Subscriptions", r"prime\s*video|amzn\s*prime|netflix|spotify|youtube\s*(premium|music)|disney|\bhbo\b"
                      r"|canva|icloud|apple\s*(music|tv|one)|chatgpt|adobe|subscription|membership"),
    ("Mobile & internet", r"\b(jazz|zong|ufone|telenor|ptcl|vodafone|verizon)\b|mobile\s*(bundle|package|plan)"
                          r"|internet|broadband|airtime|\bwi-?fi\b"),
    ("Groceries", r"grocer|supermarket|mart\b|carrefour|imtiaz|naheed|walmart|tesco|aldi|lidl|kiryana"),
    ("Education", r"\bbooks?\b|bookstore|tuition|\bcourse\b|university|college|school|stationery|\bexam\b"),
    ("Healthcare", r"pharmacy|chemist|doctor|clinic|hospital|medicine|dental|\blab\b"),
    ("Bills & rent", r"electric|\bgas bill\b|water bill|\brent\b|utility|utilities|hostel"),
    ("Transport", r"\bbus\b|metro|\buber\b|careem|bykea|indrive|\btaxi\b|\bfuel\b|petrol|\btrain\b|parking"),
    ("Entertainment", r"cinema|movie|\bgames?\b|steam|playstation|xbox|concert|arcade"),
    ("Cafes & snacks", r"\bcafe\b|café|coffee|starbucks|snack|bakery|juice|canteen|\bdhaba\b"),
    ("Shopping", r"daraz|amazon|\bshop|clothing|khaadi|shoes|\bmall\b|\bstore\b|aliexpress"),
]
HINT_CATEGORIES = {
    "food delivery": "Food delivery", "delivery": "Food delivery", "subscription": "Subscriptions",
    "subscriptions": "Subscriptions", "groceries": "Groceries", "grocery": "Groceries",
    "transport": "Transport", "travel": "Transport", "entertainment": "Entertainment",
    "shopping": "Shopping", "education": "Education", "health": "Healthcare", "healthcare": "Healthcare",
    "medical": "Healthcare", "mobile": "Mobile & internet", "internet": "Mobile & internet",
    "bills": "Bills & rent", "rent": "Bills & rent", "utilities": "Bills & rent",
}
# Merchant names that vary between statements but are one company.
MERCHANT_ALIASES = [
    (r"food\s*panda", "Foodpanda"), (r"uber\s*eats", "Uber Eats"), (r"prime\s*video|amzn\s*prime", "PrimeVideo"),
    (r"netflix", "Netflix"), (r"spotify", "Spotify"), (r"daraz", "Daraz"), (r"youtube\s*premium", "YouTube Premium"),
    (r"careem", "Careem"), (r"canva", "Canva"),
]
MERCHANT_NOISE = r"\b(pos|purchase|payment|paid|to|card|debit|credit|online|order|ref|txn|ltd|pvt|inc|llc|pk|refund|reversal|reversed)\b"

INTERNAL_TRANSFER = re.compile(
    r"(transfer|trf|moved?)\b.*\b(savings?|own|self|my|between)\b"
    r"|\b(own|self|internal)[- ]?(account[- ]?)?transfer|wallet\s*(top[- ]?up|load)"
    r"|top[- ]?up\s*from|\b(to|from)\s+savings\b|between\s+accounts", re.I)
REFUND = re.compile(r"refund|revers(al|ed)|charge\s*back|money\s*back", re.I)
ADJUSTMENT = re.compile(r"\badjustment\b|\bcorrection\b", re.I)
ANY_TRANSFER = re.compile(r"\b(transfer|trf)\b", re.I)
INCOME_SOURCES = [
    (r"pocket\s*money|allowance", "Pocket money"), (r"tutor", "Tutoring"),
    (r"salary|payroll|wages", "Salary"), (r"scholarship|stipend", "Scholarship"),
    (r"freelance", "Freelance"), (r"\bgift\b", "Gift"),
]

_DIGITS = re.compile(r"(?<![\dA-Za-z])\d(?:[ \-]?\d){7,}(?![\dA-Za-z])")
_IBAN = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")


def redact(text: str) -> str:
    """Mask account/card-like number runs, IBANs and emails. Keeps the last 4 digits."""
    def mask(match: re.Match) -> str:
        digits = re.sub(r"\D", "", match.group())
        return f"****{digits[-4:]}"
    text = _IBAN.sub(lambda m: f"****{m.group()[-4:]}", str(text))
    text = _EMAIL.sub("[email]", text)
    return _DIGITS.sub(mask, text)


def normalize_merchant(description: str) -> str:
    text = str(description or "").strip()
    if not text:
        return "(no description)"
    for pattern, name in MERCHANT_ALIASES:
        if re.search(pattern, text, re.I):
            return name
    text = re.split(r"[*]", text)[0] or text
    text = re.sub(r"#?\b[\w]*\d[\w]*\b", " ", text)
    text = re.sub(MERCHANT_NOISE, " ", text, flags=re.I)
    text = re.sub(r"[^\w&' ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.title() if text else "(unnamed)"


def merge_similar_merchants(merchants: pd.Series) -> pd.Series:
    """Fold spelling variants ('Daily Mart', 'Dailymart') into the most frequent spelling."""
    counts = merchants.value_counts()
    ordered = list(counts.index)
    canonical: dict[str, str] = {}
    keys: list[tuple[str, str]] = []
    for name in ordered:
        key = re.sub(r"[^a-z0-9]", "", name.lower())
        match = None
        if len(key) >= 5:
            for other_key, other_name in keys:
                if key == other_key or difflib.SequenceMatcher(None, key, other_key).ratio() >= 0.88:
                    match = other_name
                    break
        canonical[name] = match or name
        if match is None:
            keys.append((key, name))
    return merchants.map(canonical)


def classify_type(description: str, amount: float, type_hint: str = "") -> str:
    hint = type_hint.lower()
    text = str(description or "")
    if "transfer" in hint:
        return "transfer"
    if "refund" in hint or "reversal" in hint:
        return "refund" if amount > 0 else "adjustment"
    if "adjust" in hint:
        return "adjustment"
    if INTERNAL_TRANSFER.search(text):
        return "transfer"
    if ADJUSTMENT.search(text):
        return "adjustment"
    if REFUND.search(text):
        return "refund" if amount > 0 else "adjustment"
    return "income" if amount > 0 else "expense"


def categorize(description: str, merchant: str, category_hint: str = "") -> str:
    hint = category_hint.strip().lower()
    if hint in HINT_CATEGORIES:
        return HINT_CATEGORIES[hint]
    haystack = f"{description} {merchant}"
    for category, pattern in CATEGORY_RULES:
        if re.search(pattern, haystack, re.I):
            return category
    return OTHER


def income_source(description: str, merchant: str) -> str:
    for pattern, name in INCOME_SOURCES:
        if re.search(pattern, str(description), re.I):
            return name
    return merchant


def normalize(frame: pd.DataFrame) -> pd.DataFrame:
    """Add merchant, transaction_type, category, spending_class and review flags."""
    df = frame.copy()
    df["description"] = df["original_description"].map(redact)
    df["source"] = df["source_file"] + ":" + df["source_row"].astype(str)
    df["merchant"] = merge_similar_merchants(df["original_description"].map(normalize_merchant))
    df["transaction_type"] = [
        classify_type(d, a, h) for d, a, h in zip(df["original_description"], df["amount"], df["type_hint"])
    ]
    df["category"] = [
        categorize(d, m, h) for d, m, h in zip(df["original_description"], df["merchant"], df["category_hint"])
    ]
    df["spending_class"] = df["category"].map(CATEGORY_CLASS)
    df["income_source"] = [
        income_source(d, m) if t == "income" else ""
        for d, m, t in zip(df["original_description"], df["merchant"], df["transaction_type"])
    ]
    # A transfer to a person is real money gone, so it stays in the totals but is flagged.
    df["needs_review"] = [
        bool(ANY_TRANSFER.search(d)) and t in ("income", "expense")
        for d, t in zip(df["original_description"], df["transaction_type"])
    ]
    df.loc[df["transaction_type"] != "expense", "spending_class"] = ""
    return df

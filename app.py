"""
Index Master by Optimize Plus — Google Indexing API Bulk Tool
A single-file Streamlit dashboard for bulk URL indexing via the Google Indexing API.
"""

import io
import json
import time
import csv
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ─── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Index Master — Optimize Plus",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

    /* Global font */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Hero banner */
    .hero-banner {
        background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
        padding: 2.5rem 2rem;
        border-radius: 16px;
        text-align: center;
        margin-bottom: 1.8rem;
        box-shadow: 0 8px 32px rgba(0,0,0,0.35);
    }
    .hero-banner h1 {
        color: #ffffff;
        font-size: 2.4rem;
        font-weight: 800;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .hero-banner h1 span {
        background: linear-gradient(90deg, #00c6ff, #0072ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .hero-banner p {
        color: #b0b3c5;
        margin-top: 0.4rem;
        font-size: 1.05rem;
        font-weight: 400;
    }

    /* Metric cards */
    div[data-testid="stMetric"] {
        background: linear-gradient(145deg, #1e1e2f, #27274a);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 12px;
        padding: 1rem 1.2rem;
        box-shadow: 0 4px 14px rgba(0,0,0,0.25);
    }
    div[data-testid="stMetric"] label {
        color: #8e8ea0 !important;
        font-weight: 600;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #ffffff !important;
        font-weight: 700;
    }

    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background: #12121e;
    }
    section[data-testid="stSidebar"] .stMarkdown h2 {
        color: #ffffff;
    }

    /* Buttons */
    .stButton > button {
        background: linear-gradient(90deg, #0072ff, #00c6ff);
        color: #ffffff;
        font-weight: 700;
        border: none;
        border-radius: 10px;
        padding: 0.65rem 2rem;
        font-size: 1rem;
        transition: transform 0.15s, box-shadow 0.15s;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0,114,255,0.45);
    }

    /* Expander */
    details {
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 10px;
    }

    /* Success / Error toast tweaks */
    .stAlert {
        border-radius: 8px;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ─── Hero Banner ───────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="hero-banner">
        <h1>⚡ Index <span>Master</span></h1>
        <p>by Optimize Plus &mdash; Google Indexing API Bulk Tool</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ─── Constants ─────────────────────────────────────────────────────────────────
SCOPES = ["https://www.googleapis.com/auth/indexing"]
API_ENDPOINT = "https://indexing.googleapis.com/v3/urlNotifications:publish"

ACTION_MAP = {
    "Update URL (URL_UPDATED)": "URL_UPDATED",
    "Delete URL (URL_DELETED)": "URL_DELETED",
}


# ─── Helper Functions ──────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def _build_service(creds_json: dict):
    """Build an authorized Indexing API service from a credentials dict."""
    credentials = service_account.Credentials.from_service_account_info(
        creds_json, scopes=SCOPES
    )
    service = build("indexing", "v3", credentials=credentials)
    return service


def _parse_urls(raw_text: str) -> list[str]:
    """Extract non-empty, unique, stripped URLs from raw text."""
    seen = set()
    urls = []
    for line in raw_text.splitlines():
        url = line.strip()
        if url and url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def _parse_uploaded_file(uploaded_file) -> list[str]:
    """Read URLs from a .txt or .csv file upload."""
    content = uploaded_file.getvalue().decode("utf-8", errors="replace")
    if uploaded_file.name.lower().endswith(".csv"):
        reader = csv.reader(io.StringIO(content))
        lines = []
        for row in reader:
            if row:
                lines.append(row[0])
        return _parse_urls("\n".join(lines))
    else:
        return _parse_urls(content)


# ─── Sidebar: Authentication ──────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🔐 Authentication")
    st.caption(
        "Upload your Google service-account JSON key, "
        "or configure `[google_auth]` in **Streamlit Secrets**."
    )

    uploaded_key = st.file_uploader(
        "Service-account JSON",
        type=["json"],
        help="Upload the JSON key file downloaded from Google Cloud Console.",
    )

    creds_json = None

    if uploaded_key is not None:
        try:
            creds_json = json.load(uploaded_key)
            st.success("✅ Key file loaded successfully.")
        except json.JSONDecodeError:
            st.error("❌ Invalid JSON file. Please upload a valid service-account key.")
    else:
        # Attempt to read from Streamlit secrets
        try:
            creds_json = dict(st.secrets["google_auth"])
            st.success("✅ Using credentials from Streamlit Secrets.")
        except (KeyError, FileNotFoundError):
            st.info("ℹ️ Upload a JSON key or add `[google_auth]` to your secrets.")

    st.markdown("---")
    st.markdown("## ⚙️ Settings")
    action_label = st.selectbox("Action type", list(ACTION_MAP.keys()))
    action_type = ACTION_MAP[action_label]

    delay = st.slider(
        "Delay between requests (sec)",
        min_value=1,
        max_value=10,
        value=1,
        help="Pause between consecutive API calls to respect rate limits.",
    )

    st.markdown("---")
    st.markdown(
        "<div style='text-align:center;color:#555;font-size:0.8rem;'>"
        "Index Master v1.0<br>© 2026 Optimize Plus"
        "</div>",
        unsafe_allow_html=True,
    )

# ─── Main Area: URL Input ─────────────────────────────────────────────────────
col_left, col_right = st.columns(2, gap="large")

with col_left:
    st.markdown("### 📋 Paste URLs")
    raw_urls = st.text_area(
        "Enter URLs (one per line)",
        height=220,
        placeholder="https://example.com/page-1\nhttps://example.com/page-2",
    )

with col_right:
    st.markdown("### 📂 Upload URL File")
    uploaded_file = st.file_uploader(
        "Upload .txt or .csv",
        type=["txt", "csv"],
        help="Each line (or the first column of each row) should contain a URL.",
    )

# Merge URLs from both sources
all_urls: list[str] = []
if raw_urls:
    all_urls.extend(_parse_urls(raw_urls))
if uploaded_file is not None:
    all_urls.extend(_parse_uploaded_file(uploaded_file))

# De-duplicate while preserving order
seen = set()
unique_urls: list[str] = []
for u in all_urls:
    if u not in seen:
        seen.add(u)
        unique_urls.append(u)

if unique_urls:
    st.markdown(f"**{len(unique_urls)}** unique URL(s) ready to process.")
else:
    st.info("👆 Paste URLs above or upload a file to get started.")

# ─── Execution ─────────────────────────────────────────────────────────────────
st.markdown("---")

run_btn = st.button("🚀 Run Indexer", disabled=(not unique_urls or creds_json is None), use_container_width=True)

if run_btn and unique_urls and creds_json:
    # Build service
    try:
        service = _build_service(creds_json)
    except Exception as exc:
        st.error(f"❌ Failed to authenticate: {exc}")
        st.stop()

    total = len(unique_urls)
    successes = 0
    errors = 0
    results: list[dict] = []

    progress_bar = st.progress(0, text="Starting…")

    with st.expander("📜 Real-time Log", expanded=True):
        log_container = st.container()

    for idx, url in enumerate(unique_urls, start=1):
        body = {"url": url, "type": action_type}
        try:
            response = service.urlNotifications().publish(body=body).execute()
            successes += 1
            results.append({"URL": url, "Status": "✅ Success", "Detail": response.get("urlNotificationMetadata", {}).get("latestUpdate", {}).get("notifyTime", "—")})
            with log_container:
                st.success(f"[{idx}/{total}] ✅ {url}")
        except HttpError as http_err:
            errors += 1
            detail = http_err._get_reason() if hasattr(http_err, "_get_reason") else str(http_err)
            results.append({"URL": url, "Status": "❌ Error", "Detail": detail})
            with log_container:
                st.error(f"[{idx}/{total}] ❌ {url} — {detail}")
        except Exception as general_err:
            errors += 1
            results.append({"URL": url, "Status": "❌ Error", "Detail": str(general_err)})
            with log_container:
                st.error(f"[{idx}/{total}] ❌ {url} — {general_err}")

        progress_bar.progress(idx / total, text=f"Processing {idx} of {total}…")

        if idx < total:
            time.sleep(delay)

    progress_bar.progress(1.0, text="Done!")

    # ─── Summary Metrics ───────────────────────────────────────────────────
    st.markdown("### 📊 Summary")
    m1, m2, m3 = st.columns(3)
    m1.metric("Total URLs", total)
    m2.metric("Successes", successes)
    m3.metric("Errors", errors)

    # ─── Results Table ─────────────────────────────────────────────────────
    st.markdown("### 📑 Detailed Results")
    st.dataframe(results, use_container_width=True)

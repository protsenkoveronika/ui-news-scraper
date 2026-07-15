import streamlit as st
from streamlit_autorefresh import st_autorefresh
import time
from datetime import datetime, timedelta, timezone
from supabase import create_client, Client

st.set_page_config(page_title="News Radar", page_icon="🚀", layout="centered")

# ======================================================================
# MODERN GLASSMORPHIC CSS INJECTION
# ======================================================================
st.markdown("""
    <style>
    /* INCREASED max-width to make the interface wider */
    .block-container {
        max-width: 1200px !important; /* Expanded from 950px to 1100px */
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
        position: relative !important;
    }
    
    .st-emotion-cache-8atqhb {
        height: 0.5rem;
    }

    /* Completely hide Streamlit's default header spacing bar */
    header[data-testid="stHeader"] {
        display: none !important;
    }

    /* Pull top elements closer to the ceiling */
    div[data-testid="stAppViewBlockContainer"] {
        padding-top: 0rem !important;
    }

    /* Global Background Adjustments & Base Typography */
    .stApp {
        background-color: #0e1117;
    }

    /* Standardize image aspect ratio with an elegant card frame */
    div[data-testid="stImage"] img {
        height: 300px !important; /* Slightly increased height to match the wider card beautifully */
        object-fit: contain !important;
        background-color: #ffffff;
        padding: 16px;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
    }

    /* Premium AI Summary Card with a Neon Left Accent */
    .ai-summary-card {
        background: rgba(17, 24, 39, 0.7);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-left: 4px solid #3b82f6; /* Modern Blue Accent */
        border-radius: 8px;
        padding: 20px;
        margin: 20px 0;
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2);
    }
    .ai-summary-title {
        color: #60a5fa;
        font-weight: 600;
        font-size: 0.95rem;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .ai-summary-text {
        color: #e5e7eb;
        font-size: 0.95rem;
        line-height: 1.6;
    }

    /* Vertically center all 3 columns relative to each other */
    div[data-testid="stHorizontalBlock"] {
        align-items: center !important;
        display: flex !important;
        flex-direction: row !important;
        position: relative !important;
    }

    /* Style for buttons to look like circular side paddles */
    button[data-testid="baseButton-secondary"] {
        background-color: rgba(31, 41, 55, 0.8) !important;
        backdrop-filter: blur(8px) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        color: #f3f4f6 !important;
        border-radius: 50% !important; /* Perfect circle */
        width: 55px !important;
        height: 55px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        font-size: 1.3rem !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4) !important;
    }

    button[data-testid="baseButton-secondary"]:hover {
        border-color: #3b82f6 !important;
        color: #3b82f6 !important;
        box-shadow: 0 0 15px rgba(59, 130, 246, 0.4) !important;
        transform: scale(1.08);
    }
    
    /* Clickable Title CSS Styles */
    .clickable-title {
        color: #f3f4f6 !important;
        text-decoration: none !important;
        font-size: 1.5rem;
        font-weight: 600;
        line-height: 1.3;
        transition: color 0.2s ease-in-out;
    }
    .clickable-title:hover {
        color: #3b82f6 !important; /* Highlights blue on hover */
    }

    /* ======================================================================
       OUTSIDE FLOATING NAVIGATION POSITIONING (RELATIVE TO THE COLUMN GRID)
       ====================================================================== */
    .outside-left-arrow {
        position: absolute !important;
        left: -80px !important; /* Pushes the left arrow outside the 1100px container */
        z-index: 99999 !important;
    }

    .outside-right-arrow {
        position: absolute !important;
        right: -80px !important; /* Pushes the right arrow outside the 1100px container */
        z-index: 99999 !important;
    }

    /* Mobile / Small Screen Safeguard: Keeps buttons safe on smaller widths */
    @media (max-width: 1300px) { /* Adjusted threshold up to match the wider container */
        .outside-left-arrow {
            left: -10px !important;
        }
        .outside-right-arrow {
            right: -10px !important;
        }
    }
    </style>
""", unsafe_allow_html=True)


@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets.get("SUPABASE_URL", "https://your-project.supabase.co")
    key = st.secrets.get("SUPABASE_KEY", "your-anon-key")
    return create_client(url, key)


try:
    supabase = init_supabase()
except Exception as e:
    st.error(f"Supabase connection failed: {e}")
    st.stop()


# Fetch database updates and cache globally for 3 hours
@st.cache_data(ttl=10800)
def fetch_recent_news_from_supabase():
    cutoff_timestamp = (datetime.now(timezone.utc) - timedelta(hours=72)).isoformat()
    response = (
        supabase.table("articles")
        .select("*")
        .gte("pub_date", cutoff_timestamp)
        .order("pub_date", desc=True)
        .execute()
    )
    return response.data


news_data = fetch_recent_news_from_supabase()
total_articles = len(news_data)

if total_articles == 0:
    st.warning("No new articles found from today or yesterday. Checking again shortly...")
    st_autorefresh(interval=60000, key="empty_db_ticker")
    st.stop()

# ======================================================================
# STATE MANAGEMENT FOR THE CAROUSEL
# ======================================================================
if "current_index" not in st.session_state:
    st.session_state.current_index = 0
if "last_auto_advance" not in st.session_state:
    st.session_state.last_auto_advance = time.time()

if st.session_state.current_index >= total_articles:
    st.session_state.current_index = 0

st_autorefresh(interval=20000, key="carousel_ticker")

# Auto-advance calculation
current_time = time.time()
if current_time - st.session_state.last_auto_advance >= 19.5:
    st.session_state.current_index = (st.session_state.current_index + 1) % total_articles
    st.session_state.last_auto_advance = current_time

current_article = news_data[st.session_state.current_index]

# ======================================================================
# RENDER STRUCTURE: 3 COLUMNS (ARROW | CONTAINER | ARROW)
# ======================================================================

# 3 Columns structure to properly hold the elements side by side
left_arrow_col, main_content_col, right_arrow_col = st.columns([1, 14, 1])

# Left Arrow Column
with left_arrow_col:
    st.markdown('<div class="outside-left-arrow">', unsafe_allow_html=True)
    if st.button("🡄", key="left_nav_btn", use_container_width=True):
        st.session_state.current_index = (st.session_state.current_index - 1) % total_articles
        st.session_state.last_auto_advance = time.time()
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# Central Article Container Column
with main_content_col:
    st.title("News Radar")

    # Progress indicator
    progress_percentage = (st.session_state.current_index + 1) / total_articles
    st.progress(progress_percentage)
    st.markdown("<br>", unsafe_allow_html=True)

    with st.container():
        image_source = current_article.get("image_url",
                                           "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=800")
        st.image(image_source, use_container_width=True)

        meta_col1, meta_col2 = st.columns([3, 2])
        with meta_col1:
            st.markdown(f"### **{str(current_article.get('company', 'Unknown')).upper()}**")
        with meta_col2:
            raw_date = current_article.get('pub_date', '')
            try:
                clean_date = datetime.fromisoformat(raw_date.replace("Z", "+00:00")).strftime("%b %d, %Y")
            except Exception:
                clean_date = str(raw_date).split(" ")[0] if raw_date else "Today"

            st.markdown(
                f"<p style='text-align: right; width: 100%; color: #9ca3af; margin-top: 15px; white-space: nowrap;'><em>{clean_date}</em></p>",
                unsafe_allow_html=True)

        # st.markdown("<br>", unsafe_allow_html=True)
        title_text = current_article.get("title", "No Title Available")
        article_url = current_article.get("url", "#")

        st.markdown(
            f'<div style="margin: 10px 0 15px 0;"><a class="clickable-title" href="{article_url}" target="_blank">{title_text}</a></div>',
            unsafe_allow_html=True
        )

        ai_summary = current_article.get('ai_summary', 'No summary generated.')
        st.markdown(f"""
            <div class="ai-summary-card">
                <div class="ai-summary-title">
                    AI Summary
                </div>
                <div class="ai-summary-text">
                    {ai_summary}
                </div>
            </div>
        """, unsafe_allow_html=True)

        # if "url" in current_article:
        #     st.link_button("View Original Article", current_article["url"], use_container_width=True)

# Right Arrow Column
with right_arrow_col:
    st.markdown('<div class="outside-right-arrow">', unsafe_allow_html=True)
    if st.button("🡆", key="right_nav_btn", use_container_width=True):
        st.session_state.current_index = (st.session_state.current_index + 1) % total_articles
        st.session_state.last_auto_advance = time.time()
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# Dynamic indicator below the card
st.markdown(
    f"<div style='max-width: 1100px; margin: 0 auto;'><p style='text-align: center; color: #9ca3af; font-size: 0.9rem; margin-top: 12px;'>Article {st.session_state.current_index + 1} of {total_articles}</p></div>",
    unsafe_allow_html=True
)
import time

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from shared import inject_css, load_news, format_pub_date, title_with_sources_html, render_page_switcher, FALLBACK_IMAGE

st.set_page_config(page_title="News Radar — Carousel", page_icon="🚀", layout="centered")
inject_css()

# Top-align the Insights / Seargin Opportunity cards instead of the global
# vertical-center rule used for the arrow columns elsewhere
st.markdown("""
    <style>
    .st-key-insight_opportunity_row div[data-testid="stHorizontalBlock"] {
        align-items: flex-start !important;
    }
    </style>
""", unsafe_allow_html=True)

# Page switcher fixed in the top-right corner
render_page_switcher("pages/carousel.py")

news_data = load_news()
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
    if st.button("🡄", key="left_nav_btn", use_container_width=True):
        st.session_state.current_index = (st.session_state.current_index - 1) % total_articles
        st.session_state.last_auto_advance = time.time()
        st.rerun()

# Central Article Container Column
with main_content_col:
    st.title("News Radar")

    # Progress indicator
    progress_percentage = (st.session_state.current_index + 1) / total_articles
    st.progress(progress_percentage)
    st.markdown("<br>", unsafe_allow_html=True)

    with st.container():
        image_source = current_article.get("image_url", FALLBACK_IMAGE)
        st.image(image_source, use_container_width=True)

        meta_col1, meta_col2 = st.columns([3, 2])
        with meta_col1:
            st.markdown(f"### **{str(current_article.get('company', 'Unknown')).upper()}**")
        with meta_col2:
            st.markdown(
                f"<p style='text-align: right; width: 100%; color: #9ca3af; margin-top: 15px; white-space: nowrap;'><em>{format_pub_date(current_article)}</em></p>",
                unsafe_allow_html=True)

        # Clickable title; hovering reveals the related-links dropdown
        st.markdown(
            f'<div style="margin: 10px 0 15px 0;">{title_with_sources_html(current_article)}</div>',
            unsafe_allow_html=True
        )

        insight_opportunity_row = st.container(key="insight_opportunity_row")
        insights_col, opportunity_col = insight_opportunity_row.columns(2)
        with insights_col:
            ai_summary = current_article.get('ai_summary') or 'No summary generated.'
            st.markdown(f"""
                <div class="ai-summary-card">
                    <div class="ai-summary-title">
                        Insights
                    </div>
                    <div class="ai-summary-text">
                        {ai_summary}
                    </div>
                </div>
            """, unsafe_allow_html=True)

        with opportunity_col:
            ai_opportunity = current_article.get('ai_opportunity') or 'No opportunity analysis generated.'
            st.markdown(f"""
                <div class="opportunity-card">
                    <div class="opportunity-title">
                        Seargin Opportunity
                    </div>
                    <div class="ai-summary-text">
                        {ai_opportunity}
                    </div>
                </div>
            """, unsafe_allow_html=True)

# Right Arrow Column
with right_arrow_col:
    if st.button("🡆", key="right_nav_btn", use_container_width=True):
        st.session_state.current_index = (st.session_state.current_index + 1) % total_articles
        st.session_state.last_auto_advance = time.time()
        st.rerun()

# Dynamic indicator below the card
st.markdown(
    f"<div style='max-width: 1100px; margin: 0 auto;'><p style='text-align: center; color: #9ca3af; font-size: 0.9rem; margin-top: 12px;'>Article {st.session_state.current_index + 1} of {total_articles}</p></div>",
    unsafe_allow_html=True
)

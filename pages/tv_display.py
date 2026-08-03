"""Unattended slideshow for an office TV: no manual controls, just a large,
auto-advancing, brand-styled view of the latest news. Not part of the normal
click-through navigation — reach it by pointing the TV's browser at /tv_display."""
import time

import streamlit as st
import streamlit.components.v1 as components
from streamlit_autorefresh import st_autorefresh

from shared import inject_css, load_news, format_pub_date, get_article_urls, seargin_logo_data_uri, FALLBACK_IMAGE

SLIDE_SECONDS = 24
ADVANCE_THRESHOLD = 23.5

st.set_page_config(page_title="Seargin News — TV Display", page_icon="🟢", layout="wide")
inject_css()

# ======================================================================
# KIOSK-MODE OVERRIDES: full-bleed Seargin-branded background, no chrome
# ======================================================================
st.markdown("""
    <style>
    .stApp {
        background: radial-gradient(circle at 15% 10%, #16265c 0%, #0a0e27 55%, #05060f 100%) !important;
    }
    .block-container {
        max-width: 100% !important;
        padding: 0 !important;
    }
    div[data-testid="stImage"] img {
        height: 170px !important;
        background-color: #ffffff;
    }
    div[data-testid="stHorizontalBlock"] {
        align-items: flex-start !important;
    }

    /* Logo pinned to the bottom-left corner, like a broadcast bug */
    .tv-logo {
        position: fixed;
        bottom: 32px;
        left: 32px;
        height: 40px;
        width: auto;
        z-index: 9999;
    }

    /* Slide counter pinned to the bottom-right corner, mirroring the logo */
    .tv-footer {
        position: fixed;
        bottom: 32px;
        right: 32px;
        color: #4b5563;
        font-size: 0.9rem;
        z-index: 9999;
    }

    .tv-progress-track {
        height: 4px;
        width: 100%;
        background: rgba(255, 255, 255, 0.08);
    }
    .tv-progress-fill {
        height: 100%;
        background: linear-gradient(90deg, #2563eb, #22c55e);
        border-radius: 0 4px 4px 0;
    }

    .st-key-tv_header_row {
        padding: 40px 80px 0 80px;
    }
    .st-key-tv_panels_row {
        padding: 32px 80px 100px 80px;
    }

    /* Title sits at the top of the column; the date anchors to the bottom-right
       of the row instead — height matches the photo (170px) so "bottom" means
       the same thing for both */
    .tv-header-col {
        position: relative;
        height: 170px;
    }
    .tv-headline {
        color: #f9fafb;
        font-size: 2.6rem;
        font-weight: 700;
        line-height: 1.25;
    }
    .tv-headline a {
        color: inherit;
        text-decoration: none;
    }
    .tv-date {
        position: absolute;
        bottom: 0;
        right: 0;
        color: #6b7280;
        font-size: 1.05rem;
    }

    .tv-panel {
        background: rgba(17, 24, 39, 0.55);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 12px;
        padding: 28px;
        height: 100%;
    }
    .tv-panel-insights { border-left: 4px solid #3b82f6; }
    .tv-panel-opportunity { border-left: 4px solid #34d399; }
    .tv-panel-title {
        font-size: 1rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        margin-bottom: 12px;
    }
    .tv-panel-insights .tv-panel-title { color: #60a5fa; }
    .tv-panel-opportunity .tv-panel-title { color: #34d399; }
    .tv-panel-text {
        color: #e5e7eb;
        font-size: 1.15rem;
        line-height: 1.6;
    }

    /* Real Streamlit buttons that drive prev/next, triggered only via the
       keyboard-arrow / click-side JS below — never shown to the viewer */
    .st-key-tv_prev_btn, .st-key-tv_next_btn {
        display: none !important;
    }
    </style>
""", unsafe_allow_html=True)

news_data = load_news()
total_articles = len(news_data)

if total_articles == 0:
    st.warning("No new articles found from today or yesterday. Checking again shortly...")
    st_autorefresh(interval=60000, key="tv_empty_ticker")
    st.stop()

# ======================================================================
# STATE MANAGEMENT — kept separate from every other page's carousel state
# ======================================================================
if "tv_current_index" not in st.session_state:
    st.session_state.tv_current_index = 0
if "tv_last_auto_advance" not in st.session_state:
    st.session_state.tv_last_auto_advance = time.time()

if st.session_state.tv_current_index >= total_articles:
    st.session_state.tv_current_index = 0

st_autorefresh(interval=SLIDE_SECONDS * 1000, key="tv_ticker")


def _go_to_previous():
    st.session_state.tv_current_index = (st.session_state.tv_current_index - 1) % total_articles
    st.session_state.tv_last_auto_advance = time.time()


def _go_to_next():
    st.session_state.tv_current_index = (st.session_state.tv_current_index + 1) % total_articles
    st.session_state.tv_last_auto_advance = time.time()


# ======================================================================
# MANUAL NAVIGATION — invisible buttons, driven by the left/right arrow
# keys or a click on the left/right half of the screen (clicks on the
# article link itself are left alone so it still opens the source URL).
# Checked BEFORE the auto-advance timer below: st.rerun() here short-circuits
# the rest of the script, so a manual click can never race with — and get
# silently cancelled out by — an auto-advance that fires in the same rerun.
# ======================================================================
if st.button("prev", key="tv_prev_btn"):
    _go_to_previous()
    st.rerun()
if st.button("next", key="tv_next_btn"):
    _go_to_next()
    st.rerun()

current_time = time.time()
if current_time - st.session_state.tv_last_auto_advance >= ADVANCE_THRESHOLD:
    st.session_state.tv_current_index = (st.session_state.tv_current_index + 1) % total_articles
    st.session_state.tv_last_auto_advance = current_time

current_article = news_data[st.session_state.tv_current_index]

components.html(
    """
    <script>
    (function() {
        const doc = window.parent.document;

        function clickButton(key) {
            const btn = doc.querySelector('.st-key-' + key + ' button');
            if (btn) btn.click();
        }

        // This script re-runs on every Streamlit rerun (the iframe it lives in
        // gets recreated), so binding blindly would stack up duplicate
        // listeners over time. Stash the handler on the persistent parent
        // document and always remove the previous one by that exact
        // reference first, guaranteeing at most one of each is ever active.
        if (doc.__tvKeyHandler) doc.removeEventListener('keydown', doc.__tvKeyHandler);
        doc.__tvKeyHandler = function(e) {
            if (e.key === 'ArrowLeft') clickButton('tv_prev_btn');
            else if (e.key === 'ArrowRight') clickButton('tv_next_btn');
        };
        doc.addEventListener('keydown', doc.__tvKeyHandler);

        if (doc.__tvClickHandler) doc.removeEventListener('click', doc.__tvClickHandler, true);
        doc.__tvClickHandler = function(e) {
            // Ignore the article link (let it navigate normally) and clicks
            // that already landed on one of our own hidden nav buttons —
            // otherwise clicking one button here would reinterpret that same
            // click (clientX defaults to 0 for programmatic/keyboard
            // activation) as "left side of screen" and fire the OTHER button too.
            if (e.target.closest('a, .st-key-tv_prev_btn, .st-key-tv_next_btn')) return;
            const halfway = doc.documentElement.clientWidth / 2;
            clickButton(e.clientX < halfway ? 'tv_prev_btn' : 'tv_next_btn');
        };
        doc.addEventListener('click', doc.__tvClickHandler, true);
    })();
    </script>
    """,
    height=0,
)

# ======================================================================
# RENDER
# ======================================================================
progress_pct = round((st.session_state.tv_current_index + 1) / total_articles * 100)
st.markdown(
    f'<div class="tv-progress-track"><div class="tv-progress-fill" style="width:{progress_pct}%;"></div></div>',
    unsafe_allow_html=True,
)

title_text = current_article.get("title", "No Title Available")
article_urls = get_article_urls(current_article)
article_url = article_urls[0] if article_urls else "#"

with st.container(key="tv_header_row"):
    image_col, header_text_col = st.columns([1, 2])
    with image_col:
        st.image(current_article.get("image_url", FALLBACK_IMAGE), use_container_width=True)
    with header_text_col:
        st.markdown(
            f'<div class="tv-header-col">'
            f'<div class="tv-headline"><a href="{article_url}" target="_blank">{title_text}</a></div>'
            f'<div class="tv-date">{format_pub_date(current_article)}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

with st.container(key="tv_panels_row"):
    insights_col, opportunity_col = st.columns(2)
    with insights_col:
        ai_summary = current_article.get("ai_summary") or "No summary generated."
        st.markdown(
            f'<div class="tv-panel tv-panel-insights"><div class="tv-panel-title">INSIGHTS</div>'
            f'<div class="tv-panel-text">{ai_summary}</div></div>',
            unsafe_allow_html=True,
        )
    with opportunity_col:
        ai_opportunity = current_article.get("ai_opportunity") or "No opportunity analysis generated."
        st.markdown(
            f'<div class="tv-panel tv-panel-opportunity"><div class="tv-panel-title">SEARGIN OPPORTUNITY</div>'
            f'<div class="tv-panel-text">{ai_opportunity}</div></div>',
            unsafe_allow_html=True,
        )

st.markdown(f'<img class="tv-logo" src="{seargin_logo_data_uri()}" />', unsafe_allow_html=True)
st.markdown(
    f'<div class="tv-footer">{st.session_state.tv_current_index + 1} / {total_articles}</div>',
    unsafe_allow_html=True,
)

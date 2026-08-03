"""Shared code for all News Radar pages: CSS, Supabase access and helpers."""
import base64
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

import streamlit as st
from supabase import create_client, Client

CACHE_TIMEOUT = 10800
CUTOFF_TIMESPAN = 24*7

FALLBACK_IMAGE = "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=800"
SEARGIN_LOGO_PATH = Path(__file__).parent / "assets" / "Logo_transparent_01.png"


@st.cache_data
def seargin_logo_data_uri():
    """Base64 data URI for the brand logo, for use in a plain <img> tag —
    bypasses Streamlit's st.image wrapper so none of the company-logo card
    styling (white background, fixed height, padding) applies to it."""
    data = SEARGIN_LOGO_PATH.read_bytes()
    return f"data:image/png;base64,{base64.b64encode(data).decode()}"

# Pages shown in the top-right navigation switcher, in display order
NAV_PAGES = [
    {"target": "app.py", "label": "All News"},
    {"target": "pages/dashboard.py", "label": "Dashboard"},
    {"target": "pages/weekly_scores.py", "label": "Weekly Scores"},
    {"target": "pages/sentiment.py", "label": "Sentiment"},
    {"target": "pages/client_alerts.py", "label": "Alerts"},
    {"target": "pages/carousel.py", "label": "Carousel"},
    {"target": "pages/tv_display.py", "label": "TV Display"},
]

# Monday-first weekday labels, indexed to match datetime.weekday()
WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# Single-hue ordinal ramp for tier 1/2/3 (brightest = most important), validated
# against the app's #0e1117 background: contrast 8.96:1 / 5.19:1 / 2.33:1,
# comfortably monotone and clear of the 2:1 floor for the darkest step.
# Any tier beyond the third falls back to the same muted gray already used
# for the plain-text tier/relevance badges elsewhere in the app.
TIER_RAMP = ["#86b6ef", "#3987e5", "#184f95"]
TIER_FALLBACK_COLOR = "#6b7280"


def tier_color(rank_index):
    """Color for the nth (0-based) distinct tier, from the ordinal ramp."""
    if 0 <= rank_index < len(TIER_RAMP):
        return TIER_RAMP[rank_index]
    return TIER_FALLBACK_COLOR


# Categorical palette, dark-mode steps, in fixed hue order — first 5 slots
# (blue/orange/aqua/yellow/violet) cover up to 5 industries. The first 4 are
# the documented default order's slots, validated for every adjacent pair in
# both modes; the 5th swaps in the palette's violet step (was magenta) at the
# user's request — not re-validated against slot 4, but low-risk as a single
# swatch choice on a 5-series business chart.
INDUSTRY_COLOR_RAMP = ["#3987e5", "#d95926", "#199e70", "#c98500", "#9085e9"]
INDUSTRY_FALLBACK_COLOR = "#9ca3af"

# Sentiment is a reserved, fixed 4-step status scale (good/warning/critical),
# never themed — "neutral" has no state to flag, so it gets the same muted
# gray used for plain-text badges elsewhere rather than borrowing a status
# color that would misstate it as good or bad.
SENTIMENT_STATUS = {
    "positive": {"color": "#0ca30c", "icon": "▲", "label": "Positive"},
    "negative": {"color": "#d03b3b", "icon": "▼", "label": "Negative"},
    "mixed": {"color": "#fab219", "icon": "◆", "label": "Mixed"},
    "neutral": {"color": "#9ca3af", "icon": "●", "label": "Neutral"},
}


def industry_color(rank_index):
    """Color for the nth (0-based) distinct industry, from the categorical ramp."""
    if 0 <= rank_index < len(INDUSTRY_COLOR_RAMP):
        return INDUSTRY_COLOR_RAMP[rank_index]
    return INDUSTRY_FALLBACK_COLOR


def sentiment_status(label):
    return SENTIMENT_STATUS.get(str(label).lower(), SENTIMENT_STATUS["neutral"])


def sentiment_badge_html(label):
    """Status-coded sentiment badge: icon + label together, never color alone."""
    s = sentiment_status(label)
    return (
        f'<span style="color:{s["color"]}; font-weight:700; font-size:0.8rem; '
        f'letter-spacing:0.02em;">{s["icon"]} {s["label"].upper()}</span>'
    )


def sort_articles(news_data, mode):
    """Shared sort logic for the "All News" and "Dashboard" pages. Data
    arrives newest-first from the DB; sorts are stable, so ties keep that
    order."""
    if mode == "Top tier first":
        return sorted(
            news_data,
            key=lambda a: (tier_number(a), -(a.get("relevance") or 0), -(a.get("score") or 0)),
        )
    if mode == "Most relevant":
        return sorted(
            news_data,
            key=lambda a: (-(a.get("relevance") or 0), -(a.get("score") or 0)),
        )
    return news_data

# ======================================================================
# MODERN GLASSMORPHIC CSS (shared by every page)
# ======================================================================
GLOBAL_CSS = """
    <style>
    /* INCREASED max-width to make the interface wider */
    .block-container {
        max-width: 1200px !important; /* Expanded from 950px to 1100px */
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
        position: relative !important;
    }

    /* Completely hide Streamlit's default header spacing bar */
    header[data-testid="stHeader"] {
        display: none !important;
    }

    /* Hide the default sidebar page navigation — the app renders its own
       page links at the top of each page instead */
    section[data-testid="stSidebar"],
    div[data-testid="stSidebarNav"],
    div[data-testid="collapsedControl"] {
        display: none !important;
    }

    /* ======================================================================
       HIDE STREAMLIT AUTOREFRESH IFRAME CONTAINER
       ====================================================================== */
    iframe[title="streamlit_autorefresh.st_autorefresh"] {
        display: none !important;
        height: 0 !important;
        width: 0 !important;
        position: absolute !important;
        visibility: hidden !important;
    }

    div[data-testid="stCustomComponentV1"] {
        display: none !important;
        height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
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
        margin-bottom: 10px !important;
    }

    /* Seargin Opportunity card: same shape as the Insights card, with a
       distinct accent color so the two are easy to tell apart at a glance */
    .opportunity-card {
        background: rgba(17, 24, 39, 0.7);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-left: 4px solid #34d399;
        border-radius: 8px;
        padding: 20px;
        margin: 20px 0;
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2);
    }
    .opportunity-title {
        color: #34d399;
        font-weight: 600;
        font-size: 0.95rem;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 8px;
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

    /* Page switcher pinned to the top-right corner of the viewport,
       mirroring the fixed nav arrows in the bottom corners */
    .st-key-page_switch_btn {
        position: fixed !important;
        top: 24px !important;
        right: 24px !important;
        z-index: 99999 !important;
        width: auto !important;
        display: flex !important;
        flex-direction: row !important;
        gap: 8px !important;
    }

    /* Page navigation links (switch between carousel and list views) */
    a[data-testid="stPageLink-NavLink"] {
        background-color: rgba(31, 41, 55, 0.8) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 20px !important;
        padding: 6px 16px !important;
        transition: all 0.2s ease-in-out !important;
    }
    a[data-testid="stPageLink-NavLink"]:hover {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 10px rgba(59, 130, 246, 0.3) !important;
    }
    a[data-testid="stPageLink-NavLink"] p {
        color: #d1d5db !important;
        font-size: 0.9rem !important;
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

    /* Hover wrapper around the title: revealing the related-links dropdown */
    .title-hover-wrap {
        position: relative;
        display: inline-block;
    }

    /* Source link pills: hidden by default, shown as a floating dropdown panel
       while hovering the title (or the panel itself, so links stay clickable) */
    .title-hover-wrap .source-links {
        display: none;
        position: absolute;
        top: 100%;
        left: 0;
        z-index: 10000;
        flex-wrap: wrap;
        gap: 8px;
        padding: 12px;
        background: rgba(17, 24, 39, 0.95);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
        min-width: 240px;
    }
    .title-hover-wrap:hover .source-links {
        display: flex;
    }
    .source-links a {
        background-color: rgba(31, 41, 55, 0.8);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        color: #d1d5db !important;
        text-decoration: none !important;
        font-size: 0.85rem;
        padding: 6px 14px;
        transition: all 0.2s ease-in-out;
    }
    .source-links a:hover {
        border-color: #3b82f6;
        color: #3b82f6 !important;
        box-shadow: 0 0 10px rgba(59, 130, 246, 0.3);
    }

    /* ======================================================================
       DASHBOARD PAGE: stat tiles, tier-distribution bars, article cards
       ====================================================================== */
    .stat-tile {
        background: rgba(17, 24, 39, 0.7);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 8px;
        padding: 16px 18px;
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2);
    }
    .stat-tile .stat-label {
        color: #9ca3af;
        font-size: 0.78rem;
        margin-bottom: 6px;
    }
    .stat-tile .stat-value {
        color: #f3f4f6;
        font-size: 1.8rem;
        font-weight: 600;
        font-variant-numeric: proportional-nums;
    }

    .tier-bar-row {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 8px;
    }
    .tier-bar-row .tier-bar-label {
        color: #9ca3af;
        font-size: 0.8rem;
        width: 68px;
        flex-shrink: 0;
    }
    .tier-bar-row .tier-bar-track {
        flex-grow: 1;
        background: rgba(255, 255, 255, 0.06);
        border-radius: 4px;
        height: 14px;
        overflow: hidden;
    }
    .tier-bar-row .tier-bar-fill {
        height: 100%;
        border-radius: 4px;
        min-width: 4px;
    }
    .tier-bar-row .tier-bar-value {
        color: #d1d5db;
        font-size: 0.8rem;
        width: 28px;
        text-align: right;
        flex-shrink: 0;
    }

    .dashboard-card {
        background: rgba(17, 24, 39, 0.7);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 8px;
        padding: 14px;
        margin-bottom: 16px;
    }
    .dashboard-card .card-title {
        color: #f3f4f6 !important;
        text-decoration: none !important;
        font-size: 1rem;
        font-weight: 600;
        line-height: 1.35;
        transition: color 0.2s ease-in-out;
    }
    .dashboard-card .card-title:hover {
        color: #3b82f6 !important;
    }
    .dashboard-card .card-summary {
        color: #9ca3af;
        font-size: 0.82rem;
        line-height: 1.5;
        margin-top: 8px;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    div[data-testid="stPopover"] button {
        background-color: rgba(31, 41, 55, 0.8) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        color: #d1d5db !important;
        font-size: 0.8rem !important;
    }

    /* ======================================================================
       WEEKLY SCORES PAGE: company x weekday score matrix
       ====================================================================== */
    .score-table-wrap {
        background: rgba(17, 24, 39, 0.7);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 8px;
        padding: 8px;
        overflow-x: auto;
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2);
    }
    .score-table {
        width: 100%;
        border-collapse: collapse;
    }
    .score-table th, .score-table td {
        padding: 10px 14px;
        text-align: center;
        white-space: nowrap;
    }
    .score-table th {
        color: #9ca3af;
        font-size: 0.78rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    }
    .score-table th:first-child, .score-table td:first-child {
        text-align: left;
    }
    .score-table td {
        color: #d1d5db;
        font-size: 0.9rem;
        font-variant-numeric: tabular-nums;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    }
    .score-table tbody tr:last-child td {
        border-bottom: none;
    }
    .score-table td.score-company {
        color: #f3f4f6;
        font-weight: 600;
    }
    .score-table td.score-total, .score-table th:last-child {
        color: #60a5fa;
        font-weight: 700;
    }

    /* ======================================================================
       SENTIMENT PAGE: trend chart, legend, industry cards
       ====================================================================== */
    .sentiment-chart-card {
        background: rgba(17, 24, 39, 0.7);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 8px;
        padding: 20px;
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2);
    }
    .sentiment-chart-svg text {
        font-family: inherit;
    }
    .sentiment-chart-svg .chart-axis-label {
        fill: #6b7280;
        font-size: 11px;
    }
    .sentiment-chart-svg .chart-value-label {
        fill: #d1d5db;
        font-size: 11px;
        font-weight: 600;
    }
    .sentiment-chart-svg .chart-gridline {
        stroke: #2c2c2a;
        stroke-width: 1;
    }
    .sentiment-chart-svg .chart-baseline {
        stroke: #383835;
        stroke-width: 1;
    }
    .sentiment-chart-svg .chart-selected-week {
        stroke: rgba(255, 255, 255, 0.15);
        stroke-width: 1;
    }

    /* Stretch every row of industry cards so short and long cards in the
       same row share the tallest card's height. align-items:stretch only
       resizes the direct stColumn flex item — the wrappers Streamlit nests
       inside it are content-sized by default (and at least one is an
       unlabeled div, so it can't be targeted by data-testid), so a
       percentage height can't reliably reach the card div through them.
       A flex chain sidesteps that: each level becomes a column flex
       container and flexes (flex:1) to fill its own parent, which composes
       correctly regardless of unlabeled wrappers in between. */
    .st-key-industry_cards_grid div[data-testid="stHorizontalBlock"] {
        align-items: stretch !important;
    }
    .st-key-industry_cards_grid div[data-testid="stColumn"],
    .st-key-industry_cards_grid div[data-testid="stColumn"] div[data-testid="stVerticalBlock"],
    .st-key-industry_cards_grid div[data-testid="stElementContainer"],
    .st-key-industry_cards_grid div[data-testid="stMarkdown"],
    .st-key-industry_cards_grid div[data-testid="stMarkdown"] > div,
    .st-key-industry_cards_grid div[data-testid="stMarkdownContainer"],
    .st-key-industry_cards_grid div[data-testid="stMarkdownContainer"] > div {
        display: flex !important;
        flex-direction: column !important;
        flex: 1 1 auto;
        min-height: 0;
    }
    .industry-card {
        background: rgba(17, 24, 39, 0.7);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-left: 4px solid transparent;
        border-radius: 8px;
        padding: 18px;
        margin-bottom: 16px;
        display: flex;
        flex-direction: column;
        flex: 1 1 auto;
    }
    .industry-card .industry-name {
        color: #f3f4f6;
        font-size: 1.1rem;
        font-weight: 700;
    }
    .industry-card .industry-meta {
        color: #9ca3af;
        font-size: 0.78rem;
        margin: 4px 0 12px 0;
    }
    .industry-card .industry-score {
        color: #9ca3af;
        font-size: 0.8rem;
        font-weight: 600;
        margin-left: 8px;
        font-variant-numeric: tabular-nums;
    }
    .industry-card .industry-summary {
        color: #d1d5db;
        font-size: 0.88rem;
        line-height: 1.55;
        margin-bottom: 10px;
    }
    .industry-card .industry-highlights {
        margin: 0;
        padding-left: 18px;
        color: #a1a8b4;
        font-size: 0.84rem;
        line-height: 1.7;
    }

    /* ======================================================================
       CLIENT ALERTS PAGE: ranked "brief" feed, one card per client
       ====================================================================== */
    .alert-feed-header {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        margin-bottom: 20px;
    }
    .alert-feed-meta {
        color: #6b7280;
        font-size: 0.85rem;
    }
    .alert-card {
        background: rgba(17, 24, 39, 0.7);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 20px 22px;
        margin-bottom: 18px;
    }
    .alert-card-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 16px;
        margin-bottom: 14px;
    }
    .alert-card-title-row {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .alert-rank {
        color: #6b7280;
        font-weight: 700;
        font-size: 0.9rem;
        font-variant-numeric: tabular-nums;
    }
    /* Company logos are often wide rectangles (e.g. 2:1), not square, so
       object-fit: contain is used instead of cover — cover would scale a wide
       logo up until it fills the frame's height, cropping away most of its
       width, which reads as an aggressive zoom no size tweak can fix. contain
       shows the whole logo, padded by the wrap's white background. */
    .alert-avatar-wrap {
        width: 32px;
        height: 32px;
        border-radius: 50%;
        overflow: hidden;
        flex-shrink: 0;
        background: #ffffff;
        border: 1px solid rgba(255, 255, 255, 0.1);
        position: relative;
    }
    .alert-avatar {
        position: absolute !important;
        top: 50% !important;
        left: 50% !important;
        width: 110% !important;
        height: 110% !important;
        max-width: none !important;
        max-height: none !important;
        transform: translate(-50%, -50%) !important;
        object-fit: contain !important;
    }
    .alert-client-name {
        color: #f3f4f6;
        font-weight: 700;
        font-size: 1.1rem;
    }
    .alert-stats {
        text-align: right;
        color: #9ca3af;
        font-size: 0.82rem;
        white-space: nowrap;
        flex-shrink: 0;
    }
    .alert-stats .alert-stats-score {
        color: #d1d5db;
        font-weight: 600;
    }
    .alert-basis-label {
        color: #6b7280;
        font-weight: 700;
        font-size: 0.75rem;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        margin-bottom: 8px;
    }
    .alert-evidence-row {
        display: flex;
        gap: 10px;
        font-size: 0.85rem;
        line-height: 1.5;
        margin-bottom: 6px;
    }
    .alert-tier-tag {
        flex-shrink: 0;
        width: 52px;
        font-weight: 700;
        font-size: 0.7rem;
        letter-spacing: 0.04em;
        padding-top: 1px;
    }
    .alert-evidence-row a {
        color: #d1d5db;
        text-decoration: none;
    }
    .alert-evidence-row a:hover {
        color: #3b82f6;
    }
    .alert-evidence-summary {
        color: #9ca3af;
    }
    .alert-more-toggle summary {
        color: #6b7280;
        font-size: 0.8rem;
        cursor: pointer;
        margin-top: 4px;
        margin-bottom: 8px;
    }
    .alert-summary-text {
        color: #9ca3af;
        font-size: 0.85rem;
        line-height: 1.55;
        margin-top: 14px;
        padding-top: 14px;
        border-top: 1px solid rgba(255, 255, 255, 0.06);
    }

    /* ======================================================================
       FIXED NAVIGATION ARROWS — PINNED TO THE BOTTOM CORNERS OF THE VIEWPORT
       ====================================================================== */
    /* Target the buttons' actual Streamlit containers (via their st-key class) directly,
       instead of a wrapper div, since st.markdown/st.button calls don't nest in the DOM.
       position: fixed anchors them to the viewport, so they never move regardless of
       card height, scrolling, or screen size. */
    .st-key-left_nav_btn {
        position: fixed !important;
        bottom: 24px !important;
        left: 24px !important;
        z-index: 99999 !important;
        width: 55px !important;
    }

    .st-key-right_nav_btn {
        position: fixed !important;
        bottom: 24px !important;
        right: 24px !important;
        z-index: 99999 !important;
        width: 55px !important;
    }

    /* Mobile */
    @media (max-width: 800px) {
        .st-key-page_switch_btn {
            top: 12px !important;
            right: 12px !important;
        }

        .st-key-left_nav_btn {
            bottom: 16px !important;
            left: 12px !important;
        }
        .st-key-right_nav_btn {
            bottom: 16px !important;
            right: 12px !important;
        }

        div[data-testid="stImage"] img {
            height: 255px !important;
        }
    }

    @media (max-width: 600px) {

        div[data-testid="stImage"] img {
            height: 200px !important;
        }
    }

    @media (max-height: 900px) {
        div[data-testid="stImage"] img {
            height: 200px !important;
        }
    }

    @media (max-height: 800px) {
        div[data-testid="stImage"] img {
            height: 160px !important;
        }

        #news-radar {
            padding-top: 0;
        }
    }
    </style>
"""


def inject_css():
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def render_page_switcher(current_page):
    """Links to every other page, pinned to the top-right corner of the
    viewport. The keyed container gives CSS a stable .st-key-page_switch_btn
    hook, which also lays the links out in a row."""
    with st.container(key="page_switch_btn"):
        for page in NAV_PAGES:
            if page["target"] != current_page:
                st.page_link(page["target"], label=page["label"])


@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets.get("SUPABASE_URL", "https://your-project.supabase.co")
    key = st.secrets.get("SUPABASE_KEY", "your-anon-key")
    return create_client(url, key)


# Fetch database updates and cache globally for 3 hours
@st.cache_data(ttl=CACHE_TIMEOUT)
def fetch_recent_news_from_supabase():
    supabase = init_supabase()
    cutoff_timestamp = (datetime.now(timezone.utc) - timedelta(hours=CUTOFF_TIMESPAN)).isoformat()
    response = (
        supabase.table("news")
        .select("*")
        .gte("pub_date", cutoff_timestamp)
        .order("pub_date", desc=True)
        .execute()
    )
    return response.data


def load_news():
    """Fetch news, stopping the page with an error message if Supabase fails."""
    try:
        return fetch_recent_news_from_supabase()
    except Exception as e:
        st.error(f"Supabase connection failed: {e}")
        st.stop()


# Fetch the current calendar week's articles (Monday 00:00 UTC through now),
# for the Weekly Scores table. Cached separately from the 72-hour rolling
# window used everywhere else since the two windows rarely match.
@st.cache_data(ttl=CACHE_TIMEOUT)
def fetch_week_news_from_supabase():
    supabase = init_supabase()
    now = datetime.now(timezone.utc)
    week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    response = (
        supabase.table("news")
        .select("*")
        .gte("pub_date", week_start.isoformat())
        .order("pub_date", desc=True)
        .execute()
    )
    return response.data


def load_week_news():
    """Fetch this week's news, stopping the page with an error message if Supabase fails."""
    try:
        return fetch_week_news_from_supabase()
    except Exception as e:
        st.error(f"Supabase connection failed: {e}")
        st.stop()


# Every distinct company ever recorded in `news` (no date filter) — used so
# the Weekly Scores tables list every tracked company, including ones with
# zero articles (and therefore zero score) in the period being shown.
@st.cache_data(ttl=CACHE_TIMEOUT)
def fetch_all_companies_from_supabase():
    supabase = init_supabase()
    response = supabase.table("news").select("company").execute()
    companies = {row.get("company") for row in response.data if row.get("company")}
    return sorted(companies)


def load_all_companies():
    """Fetch the full company list, stopping the page with an error message if Supabase fails."""
    try:
        return fetch_all_companies_from_supabase()
    except Exception as e:
        st.error(f"Supabase connection failed: {e}")
        st.stop()


# Rolling 7-day window (today and the 6 days before it), independent of
# calendar week boundaries — a separate table alongside the Mon-Sun one.
@st.cache_data(ttl=CACHE_TIMEOUT)
def fetch_last_7_days_news_from_supabase():
    supabase = init_supabase()
    now = datetime.now(timezone.utc)
    window_start = (now - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
    response = (
        supabase.table("news")
        .select("*")
        .gte("pub_date", window_start.isoformat())
        .order("pub_date", desc=True)
        .execute()
    )
    return response.data


def load_last_7_days_news():
    """Fetch the rolling last-7-days news, stopping the page with an error message if Supabase fails."""
    try:
        return fetch_last_7_days_news_from_supabase()
    except Exception as e:
        st.error(f"Supabase connection failed: {e}")
        st.stop()


# Fetch every recorded weekly industry-sentiment digest, oldest first (so
# trend lines draw left-to-right chronologically without needing a re-sort).
@st.cache_data(ttl=CACHE_TIMEOUT)
def fetch_industry_digest_from_supabase():
    supabase = init_supabase()
    response = (
        supabase.table("industry_digest_weekly")
        .select("*")
        .order("week_start", desc=False)
        .execute()
    )
    return response.data


def load_industry_digest():
    """Fetch the industry sentiment digest, stopping the page with an error
    message if Supabase fails."""
    try:
        return fetch_industry_digest_from_supabase()
    except Exception as e:
        st.error(f"Supabase connection failed: {e}")
        st.stop()


def parse_highlights(raw):
    """Normalize the `highlights` jsonb column to a flat list of display
    strings — accepts a list of plain strings, or a list of objects with a
    title/text/highlight/summary key (schema not yet fixed by the pipeline)."""
    if not raw:
        return []
    try:
        items = json.loads(raw) if isinstance(raw, str) else raw
    except (json.JSONDecodeError, TypeError):
        return []
    if not isinstance(items, list):
        return []

    highlights = []
    for item in items:
        if isinstance(item, str):
            highlights.append(item)
        elif isinstance(item, dict):
            text = item.get("title") or item.get("text") or item.get("highlight") or item.get("summary")
            if text:
                highlights.append(str(text))
    return highlights


# Fetch every recorded client alert, newest first per client. Small table by
# nature (one row per client per alert run), so no time-window filter needed.
@st.cache_data(ttl=CACHE_TIMEOUT)
def fetch_client_alerts_from_supabase():
    supabase = init_supabase()
    response = (
        supabase.table("client_alerts")
        .select("*")
        .order("alert_date", desc=True)
        .execute()
    )
    return response.data


def load_client_alerts():
    """Fetch client alerts, stopping the page with an error message if
    Supabase fails."""
    try:
        return fetch_client_alerts_from_supabase()
    except Exception as e:
        st.error(f"Supabase connection failed: {e}")
        st.stop()


# One representative logo per company, sourced from the `news` table (whose
# `company` values match `client_alerts.client`). Cached like the other
# Supabase reads.
@st.cache_data(ttl=CACHE_TIMEOUT)
def fetch_company_logos_from_supabase():
    supabase = init_supabase()
    response = supabase.table("news").select("company, image_url").execute()
    logos = {}
    for row in response.data:
        company = row.get("company")
        image_url = row.get("image_url")
        if company and image_url and company not in logos:
            logos[company] = image_url
    return logos


def get_company_logo_map():
    try:
        return fetch_company_logos_from_supabase()
    except Exception:
        return {}


_IMAGE_MIME_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}


@st.cache_data
def company_logo_src(image_url):
    """Resolve a company logo for inline use in raw HTML (<img src="...">).
    A real http(s) URL is used as-is; a local asset path is read and
    base64-encoded into a data URI, since the browser can't fetch an
    arbitrary filesystem path directly. Falls back to FALLBACK_IMAGE (itself
    a URL) if the file is missing or unreadable."""
    if not image_url:
        return FALLBACK_IMAGE
    if image_url.startswith("http://") or image_url.startswith("https://"):
        return image_url
    try:
        path = Path(__file__).parent / image_url
        mime = _IMAGE_MIME_TYPES.get(path.suffix.lower(), "image/jpeg")
        data = path.read_bytes()
        return f"data:{mime};base64,{base64.b64encode(data).decode()}"
    except Exception:
        return FALLBACK_IMAGE


def parse_tier_highlights(raw):
    """Normalize the `tier_highlights` jsonb column — a dict keyed by tier
    name ("Tier 1", "Tier 2", ...), each a list of {url, title, summary,
    relevance} articles — into a list of (tier_name, [items]) tuples ordered
    by tier number. Tolerates plain strings in place of article objects."""
    if not raw:
        return []
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
    except (json.JSONDecodeError, TypeError):
        return []
    if not isinstance(data, dict):
        return []

    tiers = sorted(data.keys(), key=lambda t: tier_number({"tier": t}))
    result = []
    for tier in tiers:
        items = data.get(tier)
        if not isinstance(items, list):
            continue
        normalized = []
        for item in items:
            if isinstance(item, str):
                normalized.append({"title": item, "url": None, "summary": None, "relevance": None})
            elif isinstance(item, dict):
                normalized.append({
                    "title": item.get("title") or item.get("text") or "Untitled",
                    "url": item.get("url") or item.get("link"),
                    "summary": item.get("summary") or item.get("text"),
                    "relevance": item.get("relevance"),
                })
        if normalized:
            result.append((tier, normalized))
    return result


def get_article_urls(article):
    """Collect all unique source URLs from the related_urls column (a Postgres
    text[] array, returned by supabase-py as a native list; a JSON-encoded
    string is also accepted for compatibility with older rows)."""
    urls = []

    raw = article.get("related_urls")
    if raw:
        try:
            parsed = json.loads(raw) if isinstance(raw, str) else raw
        except (json.JSONDecodeError, TypeError):
            parsed = None
        if isinstance(parsed, dict):
            parsed = [parsed]
        if isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, str):
                    urls.append(item)
                elif isinstance(item, dict):
                    candidate = item.get("url") or item.get("link") or item.get("href")
                    if candidate:
                        urls.append(candidate)

    # Deduplicate while preserving order
    seen = set()
    unique_urls = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            unique_urls.append(u)
    return unique_urls


def tier_number(article):
    """Numeric rank extracted from the `tier` column (e.g. "Tier 1" -> 1).
    Lower is more important. Articles with no parseable tier sort last."""
    match = re.search(r"\d+", str(article.get("tier") or ""))
    return int(match.group()) if match else 99


def url_label(url, fallback):
    """Human-friendly label for a URL: its domain without `www.`."""
    try:
        domain = urlparse(url).netloc.replace("www.", "")
        return domain or fallback
    except Exception:
        return fallback


def format_pub_date(article):
    raw_date = article.get('pub_date', '')
    try:
        return datetime.fromisoformat(raw_date.replace("Z", "+00:00")).strftime("%b %d, %Y")
    except Exception:
        return str(raw_date).split(" ")[0] if raw_date else "Today"


def title_with_sources_html(article, title_class="clickable-title"):
    """Clickable title HTML; hovering it reveals the related-links dropdown
    when the article has more than one source URL. Everything lives in one
    HTML fragment so the CSS :hover covers both title and pills."""
    title_text = article.get("title", "No Title Available")
    article_urls = get_article_urls(article)
    article_url = article_urls[0] if article_urls else "#"

    sources_html = ""
    if len(article_urls) > 1:
        pills = "".join(
            f'<a href="{u}" target="_blank" title="{u}">🔗 {url_label(u, f"Source {i + 1}")}</a>'
            for i, u in enumerate(article_urls)
        )
        sources_html = f'<div class="source-links">{pills}</div>'

    return (
        f'<span class="title-hover-wrap">'
        f'<a class="{title_class}" href="{article_url}" target="_blank">{title_text}</a>'
        f'{sources_html}</span>'
    )

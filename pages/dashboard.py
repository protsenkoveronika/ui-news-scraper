from collections import Counter

import streamlit as st

from shared import (
    inject_css, render_page_switcher, load_news, format_pub_date, title_with_sources_html,
    sort_articles, tier_number, tier_color, FALLBACK_IMAGE,
    parse_career_positions, career_positions_table_html,
)

st.set_page_config(page_title="News Radar — Dashboard", page_icon="🚀", layout="centered")
inject_css()
render_page_switcher("pages/dashboard.py")

CARD_COLUMNS = 3

# Page-specific overrides: compact card thumbnails instead of the 300px
# carousel frame, and top-aligned rows so cards of different heights don't
# get vertically centered against each other
st.markdown("""
    <style>
    /* Streamlit's stFullScreenFrame wraps the image in an unnamed flex div
       that shrink-wraps to the image's own aspect ratio instead of
       stretching to the column's full width — so width: 100% on the <img>
       was resolving against an already-shrunk parent. Forcing 100% width
       down through that whole chain so the box itself spans the column. */
    div[data-testid="stFullScreenFrame"] > div,
    div[data-testid="stImage"],
    div[data-testid="stImageContainer"] {
        width: 100% !important;
    }
    /* Same treatment as Carousel/TV Display: object-fit: contain shows the
       whole logo, letterboxed on a white background as needed, instead of
       cover's crop — company logos are often wide wordmarks that lose their
       edges when cropped to fit a much shorter box. */
    div[data-testid="stImageContainer"] {
        display: flex !important;
        justify-content: center !important;
    }
    div[data-testid="stImage"] img {
        height: 110px !important;
        width: 100% !important;
        object-fit: contain !important;
        background-color: #ffffff !important;
        padding: 10px !important;
        border-radius: 10px !important;
        box-sizing: border-box !important;
    }
    div[data-testid="stHorizontalBlock"] {
        align-items: flex-start !important;
    }

    /* Each card row is wrapped in a keyed container ("st-key-dash_card_row_")
       so the Details button lines up along the bottom of the row instead of
       trailing right after each card's (variably long) summary text —
       align-items: stretch makes every column match the row's tallest card,
       then the column's own vertical stack becomes a flex column so the
       last element (the Details popover) can be pushed down with
       margin-top: auto while everything above it keeps its normal flow. */
    div[class*="st-key-dash_card_row_"] div[data-testid="stHorizontalBlock"] {
        align-items: stretch !important;
    }
    div[class*="st-key-dash_card_row_"] div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"] {
        height: 100% !important;
        display: flex !important;
        flex-direction: column !important;
    }
    div[class*="st-key-dash_card_row_"] div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"] > *:last-child {
        margin-top: auto !important;
    }
    /* The card text block itself (2nd child: image is 1st, Details popover
       is 3rd/last) grows to fill whatever space is left in the stretched
       column, so its background/border reaches the same height across the
       whole row — not just the Details button trailing at a shared bottom
       with an empty gap above it. Percentage height only resolves with a
       defined height at every ancestor, hence threading it through each
       wrapper down to .dashboard-card itself. */
    div[class*="st-key-dash_card_row_"] div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"] > div[data-testid="stElementContainer"]:nth-child(2) {
        flex: 1 !important;
        display: flex !important;
        flex-direction: column !important;
    }
    div[class*="st-key-dash_card_row_"] div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"] > div[data-testid="stElementContainer"]:nth-child(2) div[data-testid="stMarkdown"],
    div[class*="st-key-dash_card_row_"] div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"] > div[data-testid="stElementContainer"]:nth-child(2) div[data-testid="stMarkdown"] > div,
    div[class*="st-key-dash_card_row_"] div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"] > div[data-testid="stElementContainer"]:nth-child(2) div[data-testid="stMarkdownContainer"] {
        height: 100% !important;
    }
    div[class*="st-key-dash_card_row_"] .dashboard-card {
        height: 100% !important;
        box-sizing: border-box !important;
        margin-bottom: 0 !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("Dashboard")

news_data = load_news()

if not news_data:
    st.warning("No new articles found from today or yesterday.")
    st.stop()

# ======================================================================
# KPI STAT TILES
# ======================================================================
total = len(news_data)
companies = {a.get("company") for a in news_data if a.get("company")}
relevances = [a.get("relevance") for a in news_data if a.get("relevance") is not None]
avg_relevance = f"{sum(relevances) / len(relevances):.1f}" if relevances else "—"
top_tier_count = sum(1 for a in news_data if tier_number(a) == 1)

stats = [
    ("Total articles", str(total)),
    ("Top-tier articles", str(top_tier_count)),
    ("Companies covered", str(len(companies))),
    ("Avg. relevance", avg_relevance),
]
for col, (label, value) in zip(st.columns(4), stats):
    with col:
        st.markdown(
            f'<div class="stat-tile"><div class="stat-label">{label}</div>'
            f'<div class="stat-value">{value}</div></div>',
            unsafe_allow_html=True,
        )

st.markdown("<br>", unsafe_allow_html=True)

# ======================================================================
# TIER DISTRIBUTION (ordinal one-hue ramp: brighter = more important)
# ======================================================================
tier_counts = Counter(a.get("tier") for a in news_data if a.get("tier"))
ordered_tiers = sorted(tier_counts.keys(), key=lambda t: tier_number({"tier": t}))

if ordered_tiers:
    max_count = max(tier_counts.values())
    bar_rows = ""
    for i, tier in enumerate(ordered_tiers):
        count = tier_counts[tier]
        width_pct = max(6, round(count / max_count * 100))
        bar_rows += (
            f'<div class="tier-bar-row">'
            f'<div class="tier-bar-label">{tier}</div>'
            f'<div class="tier-bar-track">'
            f'<div class="tier-bar-fill" style="width:{width_pct}%; background:{tier_color(i)};"></div>'
            f'</div>'
            f'<div class="tier-bar-value">{count}</div>'
            f'</div>'
        )
    st.markdown(f'<div class="stat-tile">{bar_rows}</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

# ======================================================================
# FILTERS + SORT
# ======================================================================
all_companies = sorted(companies)
all_industries = sorted({a.get("industry") for a in news_data if a.get("industry")})
all_tiers = sorted({a.get("tier") for a in news_data if a.get("tier")}, key=lambda t: tier_number({"tier": t}))

filter_col1, filter_col2, filter_col3, sort_col = st.columns([2, 2, 2, 2])
with filter_col1:
    company_filter = st.multiselect("Company", all_companies, key="dash_company_filter")
with filter_col2:
    industry_filter = st.multiselect("Industry", all_industries, key="dash_industry_filter")
with filter_col3:
    tier_filter = st.multiselect("Tier", all_tiers, key="dash_tier_filter")
with sort_col:
    sort_option = st.selectbox(
        "Sort by", ["Newest first", "Top tier first", "Most relevant"], key="dash_sort",
    )

filtered_data = [
    a for a in news_data
    if (not company_filter or a.get("company") in company_filter)
    and (not industry_filter or a.get("industry") in industry_filter)
    and (not tier_filter or a.get("tier") in tier_filter)
]
filtered_data = sort_articles(filtered_data, sort_option)

st.markdown(
    f"<p style='color: #9ca3af; font-size: 0.85rem; margin: 4px 0 16px 0;'>"
    f"Showing {len(filtered_data)} of {total} articles from the last 7 days</p>",
    unsafe_allow_html=True,
)

# ======================================================================
# ARTICLE CARD GRID
# ======================================================================
if not filtered_data:
    st.info("No articles match the current filters.")

for row_start in range(0, len(filtered_data), CARD_COLUMNS):
    row_articles = filtered_data[row_start:row_start + CARD_COLUMNS]
    row = st.container(key=f"dash_card_row_{row_start}")
    for col, article in zip(row.columns(CARD_COLUMNS), row_articles):
        with col:
            st.image(article.get("image_url", FALLBACK_IMAGE), use_container_width=True)

            company = str(article.get("company", "Unknown")).upper()
            tier = article.get("tier")
            tier_badge = f' <span class="tier-badge" style="margin-left:10px;">{tier.upper()}</span>' if tier else ""
            relevance = article.get("relevance")
            relevance_badge = f' <span class="tier-badge" style="margin-left:10px;">RELEVANCE {relevance}</span>' if relevance is not None else ""
            summary_preview = article.get("ai_summary") or "No summary generated."

            # A careers-table row carries its per-posting `positions` list — shown
            # as a Position/Type/Location table instead of the free-text summary,
            # same as the Client News and TV Display pages.
            career_positions = parse_career_positions(article.get("positions"))

            st.markdown(
                f'<div class="dashboard-card">'
                f"<p style='color: #9ca3af; font-size: 0.75rem; margin: 0 0 4px 0;'>"
                f"<strong>{company}</strong> &nbsp;·&nbsp; <em>{format_pub_date(article)}</em>{tier_badge}{relevance_badge}</p>"
                f'<div>{title_with_sources_html(article, title_class="card-title")}</div>'
                f'<div class="card-summary">{summary_preview}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            with st.popover("Details", use_container_width=True):
                st.markdown("**Insights**")
                if career_positions:
                    st.markdown(career_positions_table_html(career_positions), unsafe_allow_html=True)
                else:
                    st.markdown(article.get("ai_summary") or "No summary generated.")
                st.markdown("**Seargin Opportunity**")
                st.markdown(article.get("ai_opportunity") or "No opportunity analysis generated.")

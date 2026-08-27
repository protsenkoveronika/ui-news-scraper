import streamlit as st

from shared import (
    inject_css, render_page_switcher, load_all_news, load_news, format_pub_date,
    title_with_sources_html, sort_articles, tier_number, FALLBACK_IMAGE,
    parse_career_positions, career_positions_table_html,
)

st.set_page_config(page_title="News Radar", page_icon="🚀", layout="centered")
inject_css()
render_page_switcher("app.py")

st.markdown("""
    <style>
    /* Each article row is wrapped in a keyed container (class name contains
       "st-key-news_row_"). The logo card is a fixed height (not tied to the
       content column, which varies with title length) — stImageContainer is
       the white rounded card at that fixed height, and the image floats
       centered inside it at its natural (aspect-preserved) size, capped by
       max-width/max-height so wide logos never overflow the card. */
    div[class*="st-key-news_row_"] div[data-testid="stImageContainer"] {
        height: 150px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        background: #ffffff !important;
        border-radius: 10px !important;
        padding: 10px !important;
        box-sizing: border-box !important;
        overflow: hidden !important;
    }
    /* shared.py's global stImage rule paints its own white card frame
       (background, padding, border-radius, box-shadow) directly onto the
       <img> — meant for pages with one big image. Here that card frame
       lives on stImageContainer instead, so it's reset to plain here;
       otherwise the img's own shadow shows as a blurry halo nested inside
       the container's card. */
    div[class*="st-key-news_row_"] div[data-testid="stImage"] img {
        width: auto !important;
        height: auto !important;
        max-width: 100% !important;
        max-height: 100% !important;
        object-fit: contain !important;
        background: transparent !important;
        padding: 0 !important;
        border: none !important;
        border-radius: 0 !important;
        box-shadow: none !important;
    }

    .list-title {
        color: #f3f4f6 !important;
        text-decoration: none !important;
        font-size: 1.15rem;
        font-weight: 600;
        line-height: 1.4;
        transition: color 0.2s ease-in-out;
    }
    .list-title:hover {
        color: #3b82f6 !important;
    }

    div[data-testid="stHorizontalBlock"] {
        align-items: flex-start !important;
    }

    /* Expander styled to match the glassmorphic cards. The parent
       stVerticalBlock already adds a 16px flex gap between the two
       expanders, so a negative margin here is needed to actually tighten it. */
    div[data-testid="stExpander"] {
        background: rgba(17, 24, 39, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-left: 4px solid #3b82f6;
        border-radius: 8px;
        margin-bottom: -10px;
    }
    div[data-testid="stExpander"] summary p {
        color: #60a5fa !important;
        font-weight: 600;
        font-size: 0.9rem;
    }

    .news-row-divider {
        border: none;
        border-top: 1px solid rgba(255, 255, 255, 0.08);
        margin: 18px 0;
    }

    /* Subtle tier marker: plain muted text, no background or border */
    .tier-badge {
        color: #6b7280;
        font-size: 0.7rem;
        font-weight: 600;
        letter-spacing: 0.08em;
        margin-left: 10px;
        vertical-align: middle;
    }

    /* "All time" checkbox: its container is width: fit-content by default,
       sitting flush left in its (wider, fractional) column and leaving a
       dead gap to the right — margin-left: auto pushes it to the column's
       right edge instead. Checked state forced to the app's blue accent
       instead of Streamlit's default red fill. */
    .st-key-news_all_time {
        margin-left: auto !important;
    }
    div[data-testid="stCheckbox"] label[data-selected="true"] > div:first-of-type {
        background-color: #3b82f6 !important;
        border-color: #3b82f6 !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("Client News")

# ======================================================================
# FILTERS
# ======================================================================
filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)
count_col, all_time_col = st.columns([5, 1])

with filter_col4:
    sort_option = st.selectbox(
        "Sort by",
        ["Newest first", "Top tier first", "Most relevant"],
        key="news_sort",
    )
with all_time_col:
    all_time = st.checkbox("All time", key="news_all_time")

news_data = load_all_news() if all_time else load_news()

if not news_data:
    st.warning("No articles found.")
    st.stop()

all_companies = sorted({a.get("company") for a in news_data if a.get("company")})
all_industries = sorted({a.get("industry") for a in news_data if a.get("industry")})
all_tiers = sorted({a.get("tier") for a in news_data if a.get("tier")}, key=lambda t: tier_number({"tier": t}))

with filter_col1:
    company_filter = st.multiselect("Company", all_companies, key="news_company_filter")
with filter_col2:
    industry_filter = st.multiselect("Industry", all_industries, key="news_industry_filter")
with filter_col3:
    tier_filter = st.multiselect("Tier", all_tiers, key="news_tier_filter")

news_data = [
    a for a in news_data
    if (not company_filter or a.get("company") in company_filter)
    and (not industry_filter or a.get("industry") in industry_filter)
    and (not tier_filter or a.get("tier") in tier_filter)
]

range_label = "all time" if all_time else "the last 7 days"
with count_col:
    st.markdown(
        f"<p style='color: #9ca3af; font-size: 0.9rem; margin-top: 8px;'>Showing {len(news_data)} articles from {range_label}</p>",
        unsafe_allow_html=True
    )
news_data = sort_articles(news_data, sort_option)

if not news_data:
    st.info("No articles match the current filters.")

st.markdown("<br>", unsafe_allow_html=True)

for row_idx, article in enumerate(news_data):
    row = st.container(key=f"news_row_{row_idx}")
    logo_col, content_col = row.columns([1, 5])

    with logo_col:
        st.image(article.get("image_url", FALLBACK_IMAGE), use_container_width=True)

    with content_col:
        # Company + date meta line
        company = str(article.get('company', 'Unknown')).upper()
        tier = article.get("tier")
        tier_badge = f'<span class="tier-badge">{tier.upper()}</span>' if tier else ""
        relevance = article.get("relevance")
        relevance_badge = f'<span class="tier-badge">RELEVANCE {relevance}</span>' if relevance is not None else ""
        st.markdown(
            f"<p style='color: #9ca3af; font-size: 0.8rem; margin: 0 0 4px 0;'>"
            f"<strong>{company}</strong> &nbsp;·&nbsp; <em>{format_pub_date(article)}</em>{tier_badge}{relevance_badge}</p>",
            unsafe_allow_html=True
        )

        # Clickable title; hovering reveals the related-links dropdown
        st.markdown(
            f'<div style="margin: 0 0 10px 0;">{title_with_sources_html(article, title_class="list-title")}</div>',
            unsafe_allow_html=True
        )

        # Insights and Seargin Opportunity collapsed below the title, each expandable on click.
        # A careers-table row carries its per-posting `positions` list — shown
        # as a Position/Type/Location table instead of the free-text summary.
        career_positions = parse_career_positions(article.get("positions"))
        with st.expander("Insights"):
            if career_positions:
                st.markdown(career_positions_table_html(career_positions), unsafe_allow_html=True)
            else:
                st.markdown(
                    f"<div class='ai-summary-text'>{article.get('ai_summary') or 'No summary generated.'}</div>",
                    unsafe_allow_html=True
                )

        with st.expander("Seargin Opportunity"):
            st.markdown(
                f"<div class='ai-summary-text'>{article.get('ai_opportunity') or 'No opportunity analysis generated.'}</div>",
                unsafe_allow_html=True
            )

    st.markdown("<hr class='news-row-divider'>", unsafe_allow_html=True)

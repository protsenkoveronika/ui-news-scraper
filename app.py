import streamlit as st

from shared import inject_css, load_news, format_pub_date, title_with_sources_html, render_page_switcher, sort_articles, FALLBACK_IMAGE

st.set_page_config(page_title="News Radar", page_icon="🚀", layout="centered")
inject_css()

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

    /* Compact horizontal radio for the sort control, aligned to the right */
    div[data-testid="stRadio"] label p {
        color: #d1d5db !important;
        font-size: 0.85rem !important;
    }
    div[data-testid="stRadio"] div[role="radiogroup"] {
        justify-content: flex-end !important;
    }
    /* Selected radio dot: blue instead of Streamlit's default red.
       :first-child is required — the same nesting level also holds the
       label's text container as a sibling div, and a bare "> div > div"
       matches both, painting the text's background blue too. */
    div[data-testid="stRadio"] label[data-testid="stRadioOption"]:has(input:checked) > div:nth-child(2) > div > div:first-child {
        background-color: #3b82f6 !important;
        border-color: #3b82f6 !important;
    }
    /* Push the sort control's container to the right edge of its column */
    .st-key-news_sort {
        margin-left: auto !important;
        width: auto !important;
    }
    </style>
""", unsafe_allow_html=True)

# Page switcher fixed in the top-right corner
render_page_switcher("app.py")

st.title("All News")

news_data = load_news()

if not news_data:
    st.warning("No new articles found from today or yesterday.")
    st.stop()

count_col, sort_col = st.columns([3, 2])
with count_col:
    st.markdown(
        f"<p style='color: #9ca3af; font-size: 0.9rem; margin-top: 8px;'>{len(news_data)} articles from the last 3 days</p>",
        unsafe_allow_html=True
    )
with sort_col:
    sort_option = st.radio(
        "Sort by",
        ["Newest first", "Top tier first", "Most relevant"],
        horizontal=True,
        label_visibility="collapsed",
        key="news_sort",
    )

news_data = sort_articles(news_data, sort_option)

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

        # Insights and Seargin Opportunity collapsed below the title, each expandable on click
        with st.expander("Insights"):
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

from collections import defaultdict
from datetime import datetime, timedelta, timezone

import streamlit as st

from shared import inject_css, load_all_companies, load_last_7_days_news, load_week_news, render_page_switcher, WEEKDAY_LABELS

st.set_page_config(page_title="News Radar — Weekly Scores", page_icon="🚀", layout="centered")
inject_css()

# Page switcher fixed in the top-right corner
render_page_switcher("pages/weekly_scores.py")

st.title("Weekly Scores")
st.markdown(
    "<p style='color: #9ca3af; font-size: 0.85rem; margin: -8px 0 20px 0;'>"
    "Sum of article scores per company and day, for the current week (Mon–Sun).</p>",
    unsafe_allow_html=True,
)

news_data = load_week_news()
all_companies = load_all_companies()

# ======================================================================
# BUILD THE COMPANY x WEEKDAY SCORE MATRIX
# ======================================================================
scores_by_company = defaultdict(lambda: [0] * 7)

for article in news_data:
    company = article.get("company") or "Unknown"
    raw_date = article.get("pub_date", "")
    try:
        pub_dt = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
    except Exception:
        continue
    scores_by_company[company][pub_dt.weekday()] += article.get("score") or 0

# Every tracked company is listed, not just ones with articles this week —
# accessing a defaultdict key that isn't there yet creates its zeroed row.
ordered_companies = sorted(set(all_companies) | set(scores_by_company))

# ======================================================================
# RENDER TABLE
# ======================================================================
header_cells = "".join(f"<th>{day}</th>" for day in WEEKDAY_LABELS)
rows_html = ""
for company in ordered_companies:
    day_scores = scores_by_company[company]
    total = sum(day_scores)
    day_cells = "".join(f"<td>{score or '—'}</td>" for score in day_scores)
    rows_html += (
        f"<tr><td class='score-company'>{str(company).upper()}</td>"
        f"{day_cells}<td class='score-total'>{total}</td></tr>"
    )

st.markdown(
    f"""
    <div class="score-table-wrap">
        <table class="score-table">
            <thead><tr><th>Company</th>{header_cells}<th>Total</th></tr></thead>
            <tbody>{rows_html}</tbody>
        </table>
    </div>
    """,
    unsafe_allow_html=True,
)

# ======================================================================
# LAST 7 DAYS (rolling window, independent of calendar week boundaries)
# ======================================================================
st.markdown("<br>", unsafe_allow_html=True)
st.subheader("Last 7 Days")
st.markdown(
    "<p style='color: #9ca3af; font-size: 0.85rem; margin: -8px 0 20px 0;'>"
    "Sum of article scores per company and day, for the rolling last 7 days.</p>",
    unsafe_allow_html=True,
)

last7_data = load_last_7_days_news()

today = datetime.now(timezone.utc).date()
day_dates = [today - timedelta(days=i) for i in range(6, -1, -1)]
day_index_by_date = {d: i for i, d in enumerate(day_dates)}
day_labels_7 = [f"{d.strftime('%a')} {d.month}/{d.day}" for d in day_dates]

scores_by_company_7 = defaultdict(lambda: [0] * 7)
for article in last7_data:
    company = article.get("company") or "Unknown"
    raw_date = article.get("pub_date", "")
    try:
        pub_dt = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
    except Exception:
        continue
    day_idx = day_index_by_date.get(pub_dt.date())
    if day_idx is None:
        continue
    scores_by_company_7[company][day_idx] += article.get("score") or 0

ordered_companies_7 = sorted(set(all_companies) | set(scores_by_company_7))

header_cells_7 = "".join(f"<th>{day}</th>" for day in day_labels_7)
rows_html_7 = ""
for company in ordered_companies_7:
    day_scores = scores_by_company_7[company]
    total = sum(day_scores)
    day_cells = "".join(f"<td>{score or '—'}</td>" for score in day_scores)
    rows_html_7 += (
        f"<tr><td class='score-company'>{str(company).upper()}</td>"
        f"{day_cells}<td class='score-total'>{total}</td></tr>"
    )

st.markdown(
    f"""
    <div class="score-table-wrap">
        <table class="score-table">
            <thead><tr><th>Company</th>{header_cells_7}<th>Total</th></tr></thead>
            <tbody>{rows_html_7}</tbody>
        </table>
    </div>
    """,
    unsafe_allow_html=True,
)

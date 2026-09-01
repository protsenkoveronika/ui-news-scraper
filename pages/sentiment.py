from datetime import datetime

import streamlit as st

from shared import (
    inject_css, render_page_switcher, load_industry_digest, parse_highlights, parse_trends,
    industry_color, industry_legend_html, sentiment_status, sentiment_badge_html, INDUSTRY_COLOR_RAMP,
)

st.set_page_config(page_title="News Radar — Sentiment", page_icon="🚀", layout="centered")
inject_css()
render_page_switcher("pages/sentiment.py")

# Top-align card grids instead of the shared vertical-center rule; theme the
# industry-filter pills to match the rest of the page
st.markdown("""
    <style>
    div[data-testid="stHorizontalBlock"] {
        align-items: flex-start !important;
    }
    div[data-testid="stButtonGroup"] button[data-variant="pills"] {
        background-color: rgba(31, 41, 55, 0.5) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        color: #9ca3af !important;
        opacity: 0.6;
        font-size: 0.78rem !important;
        padding: 2px 10px !important;
        height: 24px !important;
        min-height: 24px !important;
    }
    div[data-testid="stButtonGroup"] button[data-variant="pills"] p {
        font-size: 0.78rem !important;
    }
    div[data-testid="stButtonGroup"] button[data-variant="pills"]:hover {
        border-color: rgba(255, 255, 255, 0.4) !important;
        color: #f3f4f6 !important;
        opacity: 1;
    }
    div[data-testid="stButtonGroup"] button[data-variant="pills"][data-selected="true"] {
        background-color: transparent !important;
        color: #f3f4f6 !important;
        opacity: 1;
    }
    </style>
""", unsafe_allow_html=True)

st.title("Client Industry Sentiment")

digest = load_industry_digest()

if not digest:
    st.info(
        "No sentiment digest data available yet. If you've already inserted rows into "
        "`industry_digest_weekly`, double-check that a SELECT policy for the anon role "
        "exists on that table (the same fix used for the `news` table)."
    )
    st.stop()


def _fmt_date(d):
    try:
        return datetime.fromisoformat(str(d)).strftime("%b %d")
    except Exception:
        return str(d)


def _fmt_date_full(d):
    try:
        return datetime.fromisoformat(str(d)).strftime("%b %d, %Y")
    except Exception:
        return str(d)


industries = sorted({row["industry"] for row in digest})

# Colors are assigned by all-time article volume, not alphabetical position:
# an industry's assigned color must stay stable across reruns/weeks (color
# follows the entity, not its rank in whatever's currently selected), and
# with more industries all-time than the palette has slots for, ranking by
# actual prominence is far more likely to give the industries people
# actually look at (and default-select, by this week's volume) a real
# color instead of alphabetical luck deciding it for them.
total_articles_by_industry = {}
for row in digest:
    industry = row["industry"]
    total_articles_by_industry[industry] = total_articles_by_industry.get(industry, 0) + (row.get("article_count") or 0)
industries_by_prominence = sorted(industries, key=lambda i: -total_articles_by_industry[i])
industry_colors = {industry: industry_color(i) for i, industry in enumerate(industries_by_prominence)}

weeks = sorted({row["week_start"] for row in digest})
by_industry_week = {(row["industry"], row["week_start"]): row for row in digest}

# ======================================================================
# WEEK SELECTOR
# ======================================================================
week_labels = {}
week_end_by_start = {}
for w in weeks:
    sample = next(row for row in digest if row["week_start"] == w)
    week_labels[w] = f"Week of {_fmt_date(w)} – {_fmt_date_full(sample['week_end'])}"
    week_end_by_start[w] = sample["week_end"]

selected_week = st.selectbox(
    "Week",
    options=list(reversed(weeks)),
    format_func=lambda w: week_labels[w],
    key="sentiment_week",
)

week_rows = [row for row in digest if row["week_start"] == selected_week]

# ======================================================================
# STAT TILES for the selected week
# ======================================================================
scores = [row["sentiment_score"] for row in week_rows]
avg_score = sum(scores) / len(scores) if scores else 0
most_positive = max(week_rows, key=lambda r: r["sentiment_score"]) if week_rows else None
most_negative = min(week_rows, key=lambda r: r["sentiment_score"]) if week_rows else None

stats = [
    ("Avg. sentiment", f"{avg_score:+.2f}"),
    ("Most positive", most_positive["industry"] if most_positive else "—"),
    ("Most negative", most_negative["industry"] if most_negative else "—"),
]
for col, (label, value) in zip(st.columns([1, 2, 2]), stats):
    with col:
        st.markdown(
            f'<div class="stat-tile"><div class="stat-label">{label}</div>'
            f'<div class="stat-value" style="font-size:1.3rem;">{value}</div></div>',
            unsafe_allow_html=True,
        )

st.markdown("<br>", unsafe_allow_html=True)

# ======================================================================
# INDUSTRY CARDS for the selected week
# ======================================================================
CARD_COLUMNS = 1
week_rows_sorted = sorted(week_rows, key=lambda r: r["industry"])

with st.container(key="industry_cards_grid"):
    for row_start in range(0, len(week_rows_sorted), CARD_COLUMNS):
        row_chunk = week_rows_sorted[row_start:row_start + CARD_COLUMNS]
        # A trailing lone card (odd count) gets its own single-column row,
        # so it spans full width and isn't height-stretched against a sibling.
        for col, row in zip(st.columns(len(row_chunk)), row_chunk):
            with col:
                color = industry_colors[row["industry"]]
                highlights = parse_highlights(row.get("highlights"))
                highlights_html = (
                    "<ul class='industry-highlights'>" + "".join(f"<li>{h}</li>" for h in highlights) + "</ul>"
                    if highlights else ""
                )
                trends = parse_trends(row.get("trends"))
                trend_icon = {"up": "▲", "down": "▼", "neutral": "●"}
                trends_html = (
                    "<div class='industry-trends'>" + "".join(
                        f'<span class="trend-pill">'
                        f'<span class="trend-icon trend-{t["direction"]}">{trend_icon[t["direction"]]}</span> '
                        f'{t["label"]}</span>'
                        for t in trends
                    ) + "</div>"
                    if trends else ""
                )
                st.markdown(
                    f'<div class="industry-card" style="border-left-color:{color};">'
                    f'<div class="industry-name">{row["industry"]}</div>'
                    f'<div class="industry-meta">{row["article_count"]} articles this week</div>'
                    f'<div class="industry-score-row">'
                    f'{sentiment_badge_html(row["sentiment_label"])}'
                    f'<span class="industry-score">{row["sentiment_score"]:+.2f}</span>'
                    f'</div>'
                    f'{trends_html}'
                    f'<details class="industry-details">'
                    f'<summary>Summary &amp; highlights</summary>'
                    f'<div class="industry-summary">{row.get("summary") or "No summary generated."}</div>'
                    f'{highlights_html}'
                    f'</details>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

st.markdown("<br>", unsafe_allow_html=True)

# ======================================================================
# TREND CHART — sentiment score by week, one line per industry
# ======================================================================
CHART_W, CHART_H = 1000, 480
PAD_LEFT, PAD_RIGHT, PAD_TOP, PAD_BOTTOM = 46, 40, 16, 32
plot_w = CHART_W - PAD_LEFT - PAD_RIGHT
plot_h = CHART_H - PAD_TOP - PAD_BOTTOM

# Cap the chart to the 8 most recent weeks — older weeks stay pickable in the
# week dropdown above, they just don't clutter the trend line with more dots
# than the axis can label cleanly.
weeks = weeks[-8:]


def x_for(week_index):
    if len(weeks) == 1:
        return PAD_LEFT + plot_w / 2
    return PAD_LEFT + (week_index / (len(weeks) - 1)) * plot_w


def y_for(score):
    # score in [-1, 1], 1 at the top, -1 at the bottom
    return PAD_TOP + (1 - (score + 1) / 2) * plot_h


svg_parts = []

# Gridlines at 1, 0.5, 0(baseline), -0.5, -1
for value in (1, 0.5, 0, -0.5, -1):
    y = y_for(value)
    line_class = "chart-baseline" if value == 0 else "chart-gridline"
    svg_parts.append(f'<line x1="{PAD_LEFT}" y1="{y}" x2="{CHART_W - PAD_RIGHT}" y2="{y}" class="{line_class}" />')
    svg_parts.append(f'<text x="{PAD_LEFT - 10}" y="{y + 4}" text-anchor="end" class="chart-axis-label">{value:+.1f}</text>')

# Vertical guide at the selected week
if selected_week in weeks:
    sel_x = x_for(weeks.index(selected_week))
    svg_parts.append(f'<line x1="{sel_x}" y1="{PAD_TOP}" x2="{sel_x}" y2="{CHART_H - PAD_BOTTOM}" class="chart-selected-week" />')

# X-axis week labels, thinned out if there are many
label_stride = max(1, -(-len(weeks) // 8))
for i, w in enumerate(weeks):
    if i % label_stride == 0 or i == len(weeks) - 1:
        svg_parts.append(
            f'<text x="{x_for(i)}" y="{CHART_H - PAD_BOTTOM + 18}" text-anchor="middle" class="chart-axis-label">{_fmt_date(week_end_by_start[w])}</text>'
        )

# Filter widget — st.pills, a real Streamlit widget that renders as
# clickable pill buttons. st.markdown strips <script> tags and Streamlit's
# own frontend swallows click events on foreign <input> elements injected
# via unsafe_allow_html, so a pure-CSS/HTML toggle can't be made reliably
# interactive here — a real widget sidesteps that entirely. Its labels are
# plain text rather than a color-matched dot: st.pills can't render
# arbitrary HTML, only text/emoji, and with potentially many more
# industries than the 8-color palette has slots for, an emoji "dot" per
# industry couldn't stay uniquely color-matched anyway — the real swatch
# legend below (industry_legend_html) carries color identity instead.
#
# Defaults to only the top DEFAULT_ACTIVE_CAP industries, not every
# industry ever seen: the categorical palette is only validated for up to
# 8 simultaneous series (see INDUSTRY_COLOR_RAMP) — defaulting to all of
# them, once there are more industries than that, is what made the chart
# unreadable (colors repeating across unrelated lines). Users can still add
# more manually; the cap is just the default. Same all-time-prominence
# ranking as the color assignment above (not this week's article count) so
# the default view is exactly the industries that got a real color — never
# a line that's default-shown but falls back grey.
DEFAULT_ACTIVE_CAP = len(INDUSTRY_COLOR_RAMP)
default_industries = industries_by_prominence[:DEFAULT_ACTIVE_CAP]

selected_industries = st.pills(
    "Filter industries",
    options=industries,
    selection_mode="multi",
    default=default_industries,
    key="sentiment_industry_filter",
    label_visibility="collapsed",
)
active_industries = set(selected_industries or [])

st.markdown(
    industry_legend_html([i for i in industries if i in active_industries], industry_colors),
    unsafe_allow_html=True,
)

# One polyline + points per active industry (skipping weeks where that industry has no row)
for industry in industries:
    if industry not in active_industries:
        continue

    color = industry_colors[industry]
    points = [(i, w) for i, w in enumerate(weeks) if (industry, w) in by_industry_week]
    if not points:
        continue

    if len(points) == 1:
        # A single week of data has no line to draw. Draw a flat reference
        # line across the full plot width at that score's level instead, same
        # solid style as every multi-week line.
        cy = y_for(by_industry_week[(industry, points[0][1])]["sentiment_score"])
        svg_parts.append(
            f'<line x1="{PAD_LEFT}" y1="{cy}" x2="{CHART_W - PAD_RIGHT}" y2="{cy}" '
            f'stroke="{color}" stroke-width="2" />'
        )
    else:
        poly_coords = " ".join(f"{x_for(i)},{y_for(by_industry_week[(industry, w)]['sentiment_score'])}" for i, w in points)
        svg_parts.append(f'<polyline points="{poly_coords}" fill="none" stroke="{color}" stroke-width="2" />')

    for i, w in points:
        row = by_industry_week[(industry, w)]
        score = row["sentiment_score"]
        cx, cy = x_for(i), y_for(score)
        tooltip = f"{industry} — {week_labels[w]}: {score:+.2f} ({row['sentiment_label']})"
        svg_parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="12" fill="transparent"><title>{tooltip}</title></circle>'
        )
        svg_parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="4" fill="{color}" stroke="#0e1117" stroke-width="2"><title>{tooltip}</title></circle>'
        )

    # Value label at the line's last point
    last_i, last_w = points[-1]
    last_score = by_industry_week[(industry, last_w)]["sentiment_score"]
    svg_parts.append(
        f'<text x="{x_for(last_i) + 10}" y="{y_for(last_score) + 4}" class="chart-value-label">{last_score:+.2f}</text>'
    )

st.markdown(
    f'<div class="sentiment-chart-card">'
    f'<svg class="sentiment-chart-svg" viewBox="0 0 {CHART_W} {CHART_H}" style="width:100%; height:auto;">'
    f'{"".join(svg_parts)}'
    f'</svg>'
    f'</div>',
    unsafe_allow_html=True,
)

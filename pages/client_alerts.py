from datetime import datetime

import streamlit as st

from shared import (
    inject_css, render_page_switcher, load_client_alerts, load_client_employee_map, load_employee_name_map,
    parse_tier_highlights, tier_color, get_company_logo_map, company_logo_src,
    get_alert_source_urls, url_label,
)

st.set_page_config(page_title="News Radar — Alerts", page_icon="🚀", layout="centered")
inject_css()
render_page_switcher("pages/client_alerts.py")

st.markdown("""
    <style>
    /* Employee filter kept narrow (its own column, not full page width) and
       styled to match the muted-label look used elsewhere on this page. */
    .st-key-alerts_employee_filter_col label[data-testid="stWidgetLabel"] p {
        color: #9ca3af !important;
        font-size: 0.85rem !important;
    }
    .st-key-alerts_employee_filter_col {
        max-width: 320px;
        margin-bottom: 20px;
    }

    /* The sources dropdown (shared .source-links styling) normally opens
       flush with the hover text's left edge, growing rightward — fine for
       an article title at the left of its row, but this hover text sits at
       the *right* edge of the right-aligned alert-stats block, so growing
       rightward would push it off the card and often off the viewport.
       Anchored to the right edge and growing leftward instead. */
    .alert-stats .title-hover-wrap .source-links {
        left: auto;
        right: 0;
        /* The shared panel's min-width: 240px is narrower than most pills,
           so only one fit per line — wrapping still happens for more
           sources than fit on a row, but rows hold as many pills as there's
           room for instead of one each. Sized to fit its content up to
           that cap rather than always claiming the full 240px minimum. */
        max-width: min(90vw, 420px);
        min-width: 0;
        width: max-content;
    }
    /* Unlike an article title, this hover text isn't itself a link, so it
       doesn't get a pointer cursor or hover color for free — added
       explicitly here so it still reads as interactive, only when it
       actually has sources to show (an alert with none shouldn't invite a
       hover that does nothing). */
    .alert-stats .title-hover-wrap:has(.source-links) {
        cursor: pointer;
    }
    .alert-stats .title-hover-wrap:has(.source-links):hover {
        color: #3b82f6;
    }
    </style>
""", unsafe_allow_html=True)

alerts = load_client_alerts()

if not alerts:
    st.info(
        "No client alerts available yet. If you've already inserted rows into "
        "`client_alerts`, double-check that a SELECT policy for the anon role "
        "exists on that table (the same fix used for the `news` table)."
    )
    st.stop()


def _fmt_date(d):
    try:
        return datetime.fromisoformat(str(d)).strftime("%b %d, %Y")
    except Exception:
        return str(d)


company_logos = get_company_logo_map()
client_employee_map = load_client_employee_map()
employee_name_map = load_employee_name_map()


def _employee_names_for_client(client_id):
    return [employee_name_map.get(eid, eid) for eid in client_employee_map.get(client_id, [])]


# Latest alert per client, ranked by total_score — a prioritized feed rather
# than a full history: the most current signal for each account, most
# important first.
latest_by_client = {}
for row in alerts:
    existing = latest_by_client.get(row["client"])
    if not existing or row["alert_date"] > existing["alert_date"]:
        latest_by_client[row["client"]] = row

cards_all = sorted(latest_by_client.values(), key=lambda r: -r["total_score"])

all_employee_names = sorted({
    name for row in cards_all for name in _employee_names_for_client(row.get("client_id"))
})

# Read the filter's current value from session_state before the widget
# itself is declared (further down, so it renders under the title) — a
# widget's value is already in session_state by the time the script re-runs
# after the user changes it, so this reflects the current selection just
# the same. Rendering header then filter in this natural top-to-bottom
# order (matching their visual order) avoids inserting content into an
# already-rendered container after the fact, which caused a layout jump.
employee_filter = st.session_state.get("alerts_employee_filter", [])
cards = cards_all
if employee_filter:
    cards = [
        row for row in cards_all
        if set(_employee_names_for_client(row.get("client_id"))) & set(employee_filter)
    ]

if not cards:
    st.info("No clients match the selected employee filter.")
    st.stop()

most_recent_date = max(row["alert_date"] for row in cards)

st.markdown(
    f'<div class="alert-feed-header">'
    f'<h1 style="margin:0;">Client Alerts</h1>'
    f'<div class="alert-feed-meta">{len(cards)} clients&nbsp;&nbsp;latest as of {_fmt_date(most_recent_date)}</div>'
    f'</div>',
    unsafe_allow_html=True,
)

with st.container(key="alerts_employee_filter_col"):
    st.multiselect("Filter by employee", all_employee_names, key="alerts_employee_filter")

EVIDENCE_PREVIEW_COUNT = 4

for rank, alert in enumerate(cards, start=1):
    client = alert["client"]
    logo_src = company_logo_src(company_logos.get(client))
    period_label = f"{_fmt_date(alert['period_start'])} – {_fmt_date(alert['period_end'])}"

    # Hovering "N articles" reveals the alert's source links, same
    # hover-dropdown pattern as an article title elsewhere in the app
    # (title_with_sources_html) — reusing its .title-hover-wrap/.source-links
    # CSS directly for a consistent look, just without a wrapping <a> here
    # since (unlike a title) there's no single URL for this text to link to.
    source_urls = get_alert_source_urls(alert)
    sources_html = ""
    if source_urls:
        pills = "".join(
            f'<a href="{u}" target="_blank" title="{u}">🔗 {url_label(u, f"Source {i + 1}")}</a>'
            for i, u in enumerate(source_urls)
        )
        sources_html = f'<div class="source-links">{pills}</div>'
    articles_stat_html = f'<span class="title-hover-wrap">{alert["article_count"]} articles{sources_html}</span>'

    tier_groups = parse_tier_highlights(alert.get("tier_highlights"))
    tier_rank_by_name = {tier: idx for idx, (tier, _) in enumerate(tier_groups)}

    # "On which basis" is ranked by relevance score (highest first) rather
    # than tier order, so the most relevant evidence surfaces first
    # regardless of which tier it came from. Items without a relevance score
    # sort last.
    flat_evidence = sorted(
        ((tier, item) for tier, items in tier_groups for item in items),
        key=lambda pair: pair[1].get("relevance") if pair[1].get("relevance") is not None else float("-inf"),
        reverse=True,
    )

    preview = flat_evidence[:EVIDENCE_PREVIEW_COUNT]
    remainder = flat_evidence[EVIDENCE_PREVIEW_COUNT:]

    def _evidence_row_html(tier, item):
        color = tier_color(tier_rank_by_name[tier])
        title_html = (
            f'<a href="{item["url"]}" target="_blank">{item["title"]}</a>'
            if item.get("url") else item["title"]
        )
        summary_html = f' — <span class="alert-evidence-summary">{item["summary"]}</span>' if item.get("summary") else ""
        return (
            f'<div class="alert-evidence-row">'
            f'<span class="alert-tier-tag" style="color:{color};">{tier.upper()}</span>'
            f'<span>{title_html}{summary_html}</span>'
            f'</div>'
        )

    evidence_html = "".join(_evidence_row_html(tier, item) for tier, item in preview)

    # A native <details> element (not st.expander) so "more highlights" lives
    # inside the same card markup, right under the shown rows — st.expander
    # renders as its own separate widget after the card's closing </div>.
    more_html = ""
    if remainder:
        more_html = (
            f'<details class="alert-more-toggle">'
            f'<summary>+{len(remainder)} more highlights</summary>'
            f'{"".join(_evidence_row_html(tier, item) for tier, item in remainder)}'
            f'</details>'
        )

    card_html = (
        f'<div class="alert-card">'
        f'<div class="alert-card-header">'
        f'<div class="alert-card-title-row">'
        f'<span class="alert-rank">#{rank}</span>'
        f'<div class="alert-avatar-wrap"><img class="alert-avatar" src="{logo_src}" alt="{client} logo"></div>'
        f'<span class="alert-client-name">{client}</span>'
        f'</div>'
        f'<div class="alert-stats">'
        f'<span class="alert-stats-score">Score {alert["total_score"]:g}</span>&nbsp;&nbsp;{articles_stat_html}<br>'
        f'{period_label}'
        f'</div>'
        f'</div>'
        f'<div class="alert-basis-label">On which basis</div>'
        f'{evidence_html}'
        f'{more_html}'
    )

    if not flat_evidence:
        card_html += '<div class="alert-evidence-row"><span class="alert-evidence-summary">No highlights recorded for this period.</span></div>'

    card_html += f'<div class="alert-summary-text">{alert.get("summary") or "No summary generated."}</div>'
    card_html += '</div>'

    st.markdown(card_html, unsafe_allow_html=True)

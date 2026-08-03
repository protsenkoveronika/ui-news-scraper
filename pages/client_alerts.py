from datetime import datetime

import streamlit as st

from shared import (
    inject_css, load_client_alerts, parse_tier_highlights, render_page_switcher,
    tier_color, get_company_logo_map, company_logo_src,
)

st.set_page_config(page_title="News Radar — Alerts", page_icon="🚀", layout="centered")
inject_css()

render_page_switcher("pages/client_alerts.py")

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

# Latest alert per client, ranked by total_score — a prioritized feed rather
# than a full history: the most current signal for each account, most
# important first.
latest_by_client = {}
for row in alerts:
    existing = latest_by_client.get(row["client"])
    if not existing or row["alert_date"] > existing["alert_date"]:
        latest_by_client[row["client"]] = row

cards = sorted(latest_by_client.values(), key=lambda r: -r["total_score"])
most_recent_date = max(row["alert_date"] for row in cards)

st.markdown(
    f'<div class="alert-feed-header">'
    f'<h1 style="margin:0;">Client Alerts</h1>'
    f'<div class="alert-feed-meta">{len(cards)} clients · latest as of {_fmt_date(most_recent_date)}</div>'
    f'</div>',
    unsafe_allow_html=True,
)

EVIDENCE_PREVIEW_COUNT = 4

for rank, alert in enumerate(cards, start=1):
    client = alert["client"]
    logo_src = company_logo_src(company_logos.get(client))
    period_label = f"{_fmt_date(alert['period_start'])} – {_fmt_date(alert['period_end'])}"

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
        f'<span class="alert-stats-score">Score {alert["total_score"]:g}</span> · {alert["article_count"]} articles<br>'
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

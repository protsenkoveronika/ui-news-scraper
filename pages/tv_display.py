"""Unattended slideshow for an office TV: no manual controls, just a large,
auto-advancing, brand-styled view of the latest news. Not part of the normal
click-through navigation — reach it by pointing the TV's browser at /tv_display."""
import time

import streamlit as st
import streamlit.components.v1 as components
from streamlit_autorefresh import st_autorefresh

from shared import (
    inject_css, load_news, format_pub_date, get_article_urls, seargin_logo_data_uri, FALLBACK_IMAGE,
    parse_career_positions,
)

SLIDE_SECONDS = 24
ADVANCE_THRESHOLD = 23.5


def _tv_career_table_html(positions):
    """Position / Type / Location table for a careers row, same content as
    shared.career_positions_table_html but with this page's own tv-career-*
    classes (dark-panel styling, sized relative to the panel's own font size
    instead of shared.py's fixed px scale)."""
    rows = []
    for p in positions:
        title_html = p["title"]
        if p.get("source"):
            title_html = f'<a href="{p["source"]}" target="_blank">{title_html}</a>'
        rows.append(
            f'<tr><td class="tv-cpt-position">{title_html}</td>'
            f'<td class="tv-cpt-type">{p["type"]}</td>'
            f'<td class="tv-cpt-location">{p["location"]}</td></tr>'
        )
    return (
        f'<div class="tv-career-table-wrap">'
        f'<table class="tv-career-table">'
        f'<thead><tr><th>Position</th><th>Type</th><th>Location</th></tr></thead>'
        f'<tbody>{"".join(rows)}</tbody>'
        f'</table>'
        f'</div>'
    )

st.set_page_config(page_title="Seargin News — TV Display", page_icon="🟢", layout="wide")
inject_css()

# ======================================================================
# KIOSK-MODE OVERRIDES: full-bleed Seargin-branded background, no chrome
# ======================================================================
# Wrapped in its own keyed container (rather than a bare st.markdown) so it
# can be display:none'd as a whole — see .st-key-tv_style_wrap below. A
# <style> tag has no visual footprint of its own regardless of its
# container's display, but the WRAPPING stElementContainer is still a
# normal flex item in the page's vertical block unless it's explicitly
# hidden too, and Streamlit puts a 16px gap between every pair of flex
# items — so a handful of these zero-height utility elements (this style
# block, the autorefresh component, the keyboard-nav script) were each
# quietly padding out the space above the progress bar despite rendering
# nothing themselves.
st.container(key="tv_style_wrap").markdown("""
    <style>
    /* Fluid sizing tokens: clamp(min, preferred, max) scales every dimension
       continuously with viewport width instead of jumping at a couple of
       fixed breakpoints — the same page needs to read well on a phone held
       at arm's length, a laptop at a desk, and an office TV seen from across
       the room, and those don't fall into 2-3 neat buckets. The preferred
       value is vw-based so it keeps scaling smoothly all the way up to very
       wide TV viewports, capped by the max so text doesn't run away on an
       8K display. */
    :root {
        /* Bakes in the same look you got from setting the browser to 80%
           zoom, permanently, instead of something that has to be set by
           hand on every device and wouldn't survive a kiosk reboot anyway.
           Browser zoom doesn't just shrink the rendered page uniformly —
           it also enlarges the *effective* viewport that vw units measure
           against by the inverse amount (1 / 0.8), and those two effects
           exactly cancel out for anything sized with vw. What's left over
           is that only the fixed (non-vw) part of each size actually ends
           up smaller. That's why every clamp() below has its fixed
           min/base/max wrapped in calc(... * var(--tv-zoom)) while its vw
           coefficient is untouched — this reproduces exactly what 80% zoom
           looked like, at 100% zoom. Tune this one number to try a
           different level. */
        --tv-zoom: 0.75;

        --tv-headline-size: clamp(calc(1.15rem * var(--tv-zoom)), calc(0.8rem * var(--tv-zoom)) + 1.6vw, calc(3.4rem * var(--tv-zoom)));
        --tv-panel-text-size: clamp(calc(0.85rem * var(--tv-zoom)), calc(0.72rem * var(--tv-zoom)) + 0.5vw, calc(1.55rem * var(--tv-zoom)));
        --tv-panel-title-size: clamp(calc(0.72rem * var(--tv-zoom)), calc(0.65rem * var(--tv-zoom)) + 0.25vw, calc(1.2rem * var(--tv-zoom)));
        --tv-date-size: clamp(calc(0.78rem * var(--tv-zoom)), calc(0.68rem * var(--tv-zoom)) + 0.3vw, calc(1.3rem * var(--tv-zoom)));
        --tv-footer-size: clamp(calc(0.65rem * var(--tv-zoom)), calc(0.58rem * var(--tv-zoom)) + 0.2vw, calc(1.05rem * var(--tv-zoom)));
        --tv-media-h: clamp(calc(46px * var(--tv-zoom)), calc(10px * var(--tv-zoom)) + 9vw, calc(180px * var(--tv-zoom)));
        --tv-pad-x: clamp(calc(16px * var(--tv-zoom)), 4vw, calc(80px * var(--tv-zoom)));
        --tv-pad-top: clamp(calc(16px * var(--tv-zoom)), 2.5vw, calc(40px * var(--tv-zoom)));
        --tv-pad-bottom: clamp(calc(40px * var(--tv-zoom)), 6vw, calc(100px * var(--tv-zoom)));
        --tv-panel-pad: clamp(calc(14px * var(--tv-zoom)), 1.6vw, calc(28px * var(--tv-zoom)));
        --tv-corner-gap: clamp(calc(14px * var(--tv-zoom)), 2.5vw, calc(32px * var(--tv-zoom)));
        --tv-logo-h: clamp(calc(24px * var(--tv-zoom)), 3vw, calc(44px * var(--tv-zoom)));
        --tv-panels-pad-top: clamp(calc(8px * var(--tv-zoom)), 1.5vw, calc(16px * var(--tv-zoom)));
        /* How tall the career table is allowed to get before it scrolls
           internally — computed from the actual layout instead of a flat
           guess (an earlier version used a flat 42vh, which left a lot of
           unused space on a wide/short screen where the header row and
           logo clearance eat a smaller share of the viewport). Subtracts,
           from 100vh: the header row's own top padding and photo height,
           the panels row's top padding, the panels row's bottom padding
           (which is what actually reserves clearance for the fixed
           logo/counter), the panel's own top+bottom padding, and the
           INSIGHTS/SEARGIN OPPORTUNITY title's line height + margin —
           i.e. everything above and around the table that isn't the table
           itself, plus a small safety margin. */
        --tv-career-table-max-h: calc(
            100vh
            - var(--tv-pad-top) - var(--tv-media-h)
            - var(--tv-panels-pad-top) - var(--tv-pad-bottom)
            - (var(--tv-panel-pad) * 2)
            - (var(--tv-panel-title-size) * 1.3) - calc(12px * var(--tv-zoom))
            - 8px
        );
    }

    /* Kiosk display — nobody can ever scroll it, so it should never look
       scrollable either. Content that runs long simply gets clipped at the
       bottom instead of growing the page. */
    html, body {
        overflow: hidden !important;
    }
    .stApp {
        background: radial-gradient(circle at 15% 10%, #16265c 0%, #0a0e27 55%, #05060f 100%) !important;
        height: 100vh !important;
        overflow: hidden !important;
    }
    /* Streamlit gives its own main content area (a <section>, not a div —
       a div[data-testid="stMain"] selector silently never matches it)
       overflow-y: auto by default. html/body/.stApp being non-scrollable
       doesn't stop THIS specific ancestor from becoming the one that
       scrolls once content (a long AI summary) grows taller than the
       screen. */
    section[data-testid="stMain"] {
        height: 100vh !important;
        overflow: hidden !important;
    }
    .block-container {
        max-width: 100% !important;
        padding: 0 !important;
    }
    /* Streamlit's stFullScreenFrame wraps the image in an unnamed flex div
       that shrink-wraps to the image's own aspect ratio instead of
       stretching to the column's full width (same fix as dashboard.py) —
       so width: 100% on the <img> alone was resolving against an
       already-shrunk parent, leaving the image narrower than its column
       (most visible once the column goes full-row-width on a narrow screen).
       stFullScreenFrame is the outermost of this whole chain and the one
       whose own box is what's actually visible as the card, so it's the
       one sized here — every level below it (the unnamed div, stImage,
       stImageContainer, and the <img> itself) just fills 100% of it, so
       they all end up the exact same width as the column, with no gap
       anywhere in the chain. */
    div[data-testid="stFullScreenFrame"] {
        width: 100% !important;
    }
    div[data-testid="stFullScreenFrame"] > div,
    div[data-testid="stImage"],
    div[data-testid="stImageContainer"] {
        width: 100% !important;
    }
    div[data-testid="stImage"] img {
        height: var(--tv-media-h) !important;
        width: 100% !important;
        /* Was object-fit: cover, appropriate for a news photo — but this
           feed now also carries careers-table rows, whose image is a
           company logo (often a wordmark, e.g. Orange's) rather than a
           photo. cover crops to fill the frame, which for a logo means
           slicing off part of the actual brand/text instead of just
           trimming empty photo background. contain never crops (just
           letterboxes on the white background below when the aspect ratio
           doesn't match), which is correct for both a logo and a photo. */
        object-fit: contain !important;
        background-color: #ffffff;
    }
    div[data-testid="stHorizontalBlock"] {
        align-items: flex-start !important;
    }

    /* Logo pinned to the bottom-left corner, like a broadcast bug */
    .tv-logo {
        position: fixed;
        bottom: var(--tv-corner-gap);
        left: var(--tv-corner-gap);
        height: var(--tv-logo-h);
        width: auto;
        z-index: 9999;
    }

    /* Slide counter pinned to the bottom-right corner, mirroring the logo */
    .tv-footer {
        position: fixed;
        bottom: var(--tv-corner-gap);
        right: var(--tv-corner-gap);
        color: #4b5563;
        font-size: var(--tv-footer-size);
        z-index: 9999;
    }

    .tv-progress-track {
        height: calc(4px * var(--tv-zoom));
        width: 100%;
        background: rgba(255, 255, 255, 0.08);
    }
    .tv-progress-fill {
        height: 100%;
        background: linear-gradient(90deg, #2563eb, #22c55e);
        border-radius: 0 calc(4px * var(--tv-zoom)) calc(4px * var(--tv-zoom)) 0;
    }

    .st-key-tv_header_row {
        padding: var(--tv-pad-top) var(--tv-pad-x) 0 var(--tv-pad-x);
    }
    /* Image column 20px narrower than its normal 1:2 split — flex-grow: 0
       keeps it pinned at exactly that reduced basis instead of growing
       back to reclaim the space (flex's default behavior when there's
       slack to fill); the headline column next to it keeps its own
       flex-grow: 1 unchanged, so it's the only one left to absorb the
       freed-up 20px, growing by exactly that much. */
    .st-key-tv_header_row div[data-testid="stColumn"]:first-child {
        flex: 0 1 calc(33.3333% - 28px) !important;
    }
    .st-key-tv_panels_row {
        padding: var(--tv-panels-pad-top) var(--tv-pad-x) var(--tv-pad-bottom) var(--tv-pad-x);
    }

    /* Title sits at the top of the column; the date anchors to the
       bottom-right of the row instead — height matches the photo so
       "bottom" means the same thing for both. This side-by-side alignment
       only makes sense while the image/text columns sit next to each other;
       below the stacking breakpoint it's overridden to plain flow instead
       (see the max-width: 640px block), since a fixed height here would
       either clip a longer wrapped headline or leave a dead gap. */
    .tv-header-col {
        position: relative;
        height: var(--tv-media-h);
    }
    .tv-headline {
        color: #f9fafb;
        font-size: var(--tv-headline-size);
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
        font-size: var(--tv-date-size);
    }

    .tv-panel {
        background: rgba(17, 24, 39, 0.55);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: calc(12px * var(--tv-zoom));
        padding: var(--tv-panel-pad);
        height: 100%;
    }
    .tv-panel-insights { border-left: 4px solid #3b82f6; }
    .tv-panel-opportunity { border-left: 4px solid #34d399; }
    .tv-panel-title {
        font-size: var(--tv-panel-title-size);
        font-weight: 700;
        letter-spacing: 0.04em;
        margin-bottom: calc(12px * var(--tv-zoom));
    }
    .tv-panel-insights .tv-panel-title { color: #60a5fa; }
    .tv-panel-opportunity .tv-panel-title { color: #34d399; }
    .tv-panel-text {
        color: #e5e7eb;
        font-size: var(--tv-panel-text-size);
        line-height: 1.6;
    }

    /* Career postings table (in place of the free-text Insights summary for
       a careers-table row) — same table shown on Client News, restyled for
       this page's dark panel look. Sized in em relative to the panel's own
       font-size (rather than a fixed px scale) so it automatically tracks
       --tv-zoom the same way the rest of the panel text does. */
    /* Capped instead of letting a long positions list push the whole panel
       taller — this page can't scroll itself (kiosk display), so an
       uncapped table risks growing past the fixed logo/slide-counter with
       no way to see what got clipped. Scrolling within the table itself
       keeps every position reachable regardless of how long the list is.
       The header scrolls away with the rows (no position: sticky) — a
       pinned header needs its own background to hide scrolled-past rows
       underneath it, and that background inevitably reads as a visibly
       darker patch layered on top of the card's own translucent one. */
    .tv-career-table-wrap {
        overflow-x: auto;
        overflow-y: auto;
        max-height: var(--tv-career-table-max-h);
    }
    .tv-career-table-wrap::-webkit-scrollbar {
        width: 6px;
    }
    .tv-career-table-wrap::-webkit-scrollbar-track {
        background: transparent;
    }
    .tv-career-table-wrap::-webkit-scrollbar-thumb {
        background: rgba(255, 255, 255, 0.18);
        border-radius: 3px;
    }
    .tv-career-table {
        width: 100%;
        border-collapse: collapse;
        font-size: var(--tv-panel-text-size);
    }
    /* Streamlit's own default table styling (for markdown-rendered tables)
       puts a 1px border on all four sides of every th/td — left unchecked,
       that shows through as vertical rule lines between/around columns,
       since only border-bottom below is an intentional override. Reset to
       none first so the only borders left are the ones we actually want. */
    .tv-career-table th, .tv-career-table td {
        border: none;
        padding: 0.4em 0.7em;
        text-align: left;
        vertical-align: top;
    }
    .tv-career-table th:first-child, .tv-career-table td:first-child {
        padding-left: 0;
    }
    .tv-career-table th {
        color: #9ca3af;
        font-size: 0.72em;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        border-bottom: 1px solid rgba(255, 255, 255, 0.12);
    }
    .tv-career-table td {
        color: #e5e7eb;
        font-size: 0.86em;
        line-height: 1.4;
        border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    }
    .tv-career-table tbody tr:last-child td {
        border-bottom: none;
    }
    .tv-career-table td.tv-cpt-position {
        color: #f9fafb;
        font-weight: 600;
    }
    .tv-career-table td.tv-cpt-position a {
        color: inherit;
        text-decoration: none;
    }
    .tv-career-table td.tv-cpt-position a:hover {
        color: #3b82f6;
    }
    .tv-career-table td.tv-cpt-type {
        white-space: nowrap;
    }

    /* Streamlit gives every stMarkdownContainer a -16px bottom margin, meant
       to cancel out the gap it puts between multiple stacked elements in a
       vertical block — with only one element in each of these columns (the
       panel card itself), that compensation has nothing to offset, and
       instead makes the column's own layout box end 16px above the panel's
       actual bottom edge. Invisible while the panel is pinned to
       height: 100% (the desktop side-by-side case, below), but once it
       switches to height: auto on a narrow screen that phantom 16px lets it
       overflow past its own column and swallow the gap to the next one. */
    .st-key-tv_panels_row div[data-testid="stMarkdownContainer"] {
        margin-bottom: 0 !important;
    }

    /* Real Streamlit buttons that drive prev/next, triggered only via the
       keyboard-arrow / click-side JS below — never shown to the viewer.
       display: none alone should be enough, but these are the very first
       elements in the page (rendered before the progress bar/header), so
       any brief instant where this rule hasn't taken effect yet — e.g. a
       slower/older embedded browser on the actual TV — would show up right
       at the top. The extra properties are pure defense in depth: even if
       something else ever forced display back on, there's still nothing
       to see. */
    .st-key-tv_prev_btn, .st-key-tv_next_btn {
        display: none !important;
        position: absolute !important;
        width: 0 !important;
        height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow: hidden !important;
        pointer-events: none !important;
    }

    /* This page's own style block, the autorefresh timer, and the
       keyboard-nav script (below) render nothing visible either — same
       phantom-gap issue as above, fixed the same way. Hiding an ancestor
       doesn't stop a <style> tag from applying or an iframe from running
       its script/timer, so this is safe for all three.
       st_autorefresh's own element carries its key class directly
       (.st-key-tv_ticker), but st.container(key=...) puts that class on an
       *inner* node while the container's own outer stLayoutWrapper — the
       thing that actually sits in this page's flex layout and counts
       toward the gap — stays unkeyed. :has() reaches that outer wrapper
       via the keyed descendant instead. */
    .st-key-tv_ticker,
    div[data-testid="stLayoutWrapper"]:has(.st-key-tv_style_wrap),
    div[data-testid="stLayoutWrapper"]:has(.st-key-tv_kbd_wrap) {
        display: none !important;
    }

    /* Below Streamlit's own column-stacking breakpoint (phones, narrow
       windows), the image and headline stack vertically instead of sitting
       side by side — the fixed height that keeps them bottom-aligned while
       side-by-side no longer serves a purpose, and would either clip a
       wrapped headline or leave dead space beneath a short one. Panels
       (Insights / Seargin Opportunity) also stack, so their card padding
       and text size come down another notch to keep both fully visible
       without scrolling on a small screen. */
    @media (max-width: 640px) {
        .tv-header-col {
            height: auto;
            padding-bottom: calc(8px * var(--tv-zoom));
        }
        .tv-date {
            position: static;
            display: block;
            margin-top: calc(6px * var(--tv-zoom));
        }
        .st-key-tv_header_row {
            padding-top: calc(12px * var(--tv-zoom));
        }
        .st-key-tv_panels_row {
            padding-top: calc(8px * var(--tv-zoom));
        }
        .tv-panel {
            padding: calc(16px * var(--tv-zoom));
            /* height: 100% is what keeps the two panels the same height
               while they sit side by side (their column is only as tall as
               the shorter one, so it stretches to match). Once the row
               wraps and each panel gets its own full-width line, that same
               100% instead resolves against the *whole wrapped block*
               (both panels + the gap between them combined), so the first
               panel overflows by exactly the gap's height and visually
               swallows it, leaving the two cards touching with no visible
               separation. Auto height here lets each card size to its own
               content so the row's real gap shows between them. */
            height: auto;
        }
        div[data-testid="stImage"] img {
            height: clamp(calc(90px * var(--tv-zoom)), 42vw, calc(170px * var(--tv-zoom))) !important;
        }
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

with st.container(key="tv_kbd_wrap"):
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
    insights_col, opportunity_col = st.columns([11, 9])
    with insights_col:
        career_positions = parse_career_positions(current_article.get("positions"))
        if career_positions:
            insights_body = _tv_career_table_html(career_positions)
        else:
            ai_summary = current_article.get("ai_summary") or "No summary generated."
            insights_body = f'<div class="tv-panel-text">{ai_summary}</div>'
        st.markdown(
            f'<div class="tv-panel tv-panel-insights"><div class="tv-panel-title">INSIGHTS</div>'
            f'{insights_body}</div>',
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

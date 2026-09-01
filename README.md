# News Radar

A multi-page Streamlit app for monitoring company/sector news, tracking sentiment, and surfacing per-client alerts — built on a shared Supabase backend and AI-generated summaries.

## Pages

- **Client News** (`app.py`, entry point) — filterable/sortable feed of company news (last 7 days or all-time), with collapsible AI "Insights" and "Seargin Opportunity" panels per article, and hover-to-reveal source URLs. A careers/job-posting row shows a Position/Type/Location table instead of a free-text summary.
- **Dashboard** (`pages/dashboard.py`) — KPI tiles (article count, top-tier count, companies covered, avg relevance), a tier-distribution chart, and a filterable card grid for the last 7 days, with the same careers-table treatment inside each card's "Details" popover.
- **Sector News** (`pages/sector_news.py`) — same list/filter/sort UI as Client News, for industry-wide (non-company) news items.
- **Alerts** (`pages/client_alerts.py`) — ranked feed of per-client alerts (highest total score first), with an employee filter.
- **Client Industry Sentiment** (`pages/sentiment.py`) — weekly sentiment score cards per industry (colored by all-time article volume, with a matching swatch legend), plus an SVG trend chart whose pill filter defaults to the top 8 most-covered industries.
- **Sector Sentiment** (`pages/industry_sentiment.py`) — the same weekly-card/trend-chart layout, scoped to a fixed 15-topic sector taxonomy (e.g. AI Regulation & Policy, Cyber Threat & Breach Trends), each topic with its own permanent color.
- **Weekly Scores** (`pages/weekly_scores.py`) — company × weekday score matrices, for the current calendar week and the rolling last 7 days.
- **TV Display** (`pages/tv_display.py`) — unattended kiosk slideshow for an office TV, including the careers table for job-posting rows. Not linked from the nav menu; reach it by pointing the TV's browser directly at `/tv_display`.

Routing uses Streamlit's default `pages/` auto-discovery; the visible menu is a custom hamburger dropdown (`shared.render_page_switcher`), not `st.navigation`.

## Data

Supabase tables: `news`, `sector_news`, `client_alerts`, `industry_digest_weekly`, `industry_sentiment_weekly`. A `news` row can carry a `positions` jsonb column (a list of `{title, type, location, source}` job postings) to render as a careers table instead of an AI summary.

## Requirements

- Python 3.9+
- A Supabase project with the tables listed above

## Setup

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Configure Supabase credentials in `.streamlit/secrets.toml` (see `.streamlit/secrets-example.toml` for the expected format):

   ```toml
   SUPABASE_URL = "https://your-project.supabase.co"
   SUPABASE_KEY = "your-anon-key"
   ```

   This file is gitignored and should never be committed.

3. (Optional) For the Alerts page's employee filter, create these local mapping files in the project root — they're gitignored and not required for the app to run, just for that filter to have entries:

   - `client_pseudonyms.local.json` — company slug → pseudonym code
   - `client_employees.local.json` — pseudonym code → list of employee IDs
   - `employee_names.local.json` — employee ID → display name

   This is a temporary stand-in until client-to-employee assignment lives in the database.

4. Run the app:

   ```bash
   streamlit run app.py
   ```

## Project Structure

```
app.py                           # Client News page (entry point)
shared.py                        # Shared CSS, nav menu, Supabase helpers, formatting utils
pages/
    dashboard.py                  # Dashboard
    sector_news.py                 # Sector News
    client_alerts.py                # Alerts
    sentiment.py                    # Client Industry Sentiment
    industry_sentiment.py           # Sector Sentiment
    weekly_scores.py                # Weekly Scores
    tv_display.py                   # TV kiosk slideshow (not in nav)
assets/                          # Local company logo/images
*.local.json                     # Gitignored client/employee mapping files (see Setup)
.streamlit/secrets-example.toml  # Template for required secrets
requirements.txt                 # Python dependencies
```

# News Radar

A Streamlit app that displays recent company news pulled from a Supabase database and summarized with AI as a full sortable list.

## Features

- Fetches news from the last 72 hours from a Supabase `news` table (cached for 3 hours)
- **Client News** page (`app.py`): full list with company logo, clickable title, and a collapsible AI-summary "Insights" panel; sortable by newest or by top tier
- Hovering an article title reveals every related source URL when more than one is stored
- Falls back to an auto-refresh "waiting" screen when no recent news is found

## Requirements

- Python 3.9+
- A Supabase project with a `news` table containing columns such as `company`, `industry`, `topic`, `title`, `pub_date`, `image_url`, `body_text`, `ai_summary`, `related_urls` (text array), `tier`, `score`, and `relevance`

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

3. Run the app:

   ```bash
   streamlit run app.py
   ```

## Project Structure

```
app.py                          # Client News list page (entry point)
shared.py                       # Shared CSS, Supabase access, and helpers
assets/                         # Local company logo/images
.streamlit/secrets-example.toml # Template for required secrets
requirements.txt                # Python dependencies
```

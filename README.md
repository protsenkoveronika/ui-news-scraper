# News Radar

A Streamlit app that displays a self-advancing carousel of recent company news, pulled from a Supabase database and summarized with AI.

## Features

- Fetches articles from the last 72 hours from a Supabase `articles` table (cached for 3 hours)
- Auto-advances through articles every ~20 seconds, with manual prev/next arrows
- Shows article image, company, publish date, clickable title, and an AI-generated summary
- Falls back to an auto-refresh "waiting" screen when no recent articles are found

## Requirements

- Python 3.9+
- A Supabase project with an `articles` table containing columns such as `company`, `title`, `url`, `image_url`, `pub_date`, and `ai_summary`

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
app.py                          # Streamlit app entry point
assets/                         # Local company logo/images
.streamlit/secrets-example.toml # Template for required secrets
requirements.txt                # Python dependencies
```

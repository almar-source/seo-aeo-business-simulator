# Trust & Visibility Intelligence Platform

Streamlit app for simulating SEO, AEO/GEO, trust, social visibility, email impact and 7-day action plans.

## Features

- Manual authority inputs when Ahrefs export is not available
- Google Search Console CSV upload
- Google Analytics 4 CSV upload
- LinkedIn Analytics CSV upload
- Social Media CSV upload
- Email Marketing CSV upload
- Trust Score
- Visibility Score
- Opportunity Engine
- 7-Day Sprint recommendations
- Business impact projection
- CSV exports

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Community Cloud

1. Create or open your GitHub repository.
2. Upload these root files:
   - app.py
   - requirements.txt
   - README.md
3. Go to Streamlit Community Cloud.
4. Select the repository, branch, and `app.py` as the main file.
5. Deploy or reboot the app.

## CSV notes

The app is flexible with column names. It tries to detect common fields such as:

- GSC: clicks, impressions, ctr, position, query, page
- GA4: sessions, users, active users, conversions, key events
- LinkedIn: impressions, views, clicks, engagements, reactions
- Social: impressions, reach, views, clicks, engagements, likes, comments, shares
- Email: sent, recipients, delivered, opens, clicks

If your platform exports different names, rename the CSV columns before uploading.

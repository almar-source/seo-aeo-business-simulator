# Trust & Visibility Intelligence Platform v7

A Streamlit app that explains Trust, Visibility, Authority, AI Search Readiness, and business impact in plain language. Recommendations change dynamically based on uploaded data and manual inputs.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Cloud

Upload these files to the root of your GitHub repo:

- app.py
- requirements.txt
- README.md

Then reboot the app in Streamlit Cloud.

## Data inputs

Optional CSV uploads:

- Google Search Console
- Google Analytics 4
- LinkedIn
- Social media
- Email marketing

If uploads are missing or unreadable, the app uses manual inputs and clearly marks confidence as medium or low.

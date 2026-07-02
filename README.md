# Trust & Visibility Intelligence Platform 2.0

This is a modular Streamlit app for consulting-style visibility diagnosis.

## What it does

- Reads optional CSV files from Google Search Console, GA4, LinkedIn, social media, and email marketing.
- Uses manual inputs when CSVs are missing or incomplete.
- Calculates Trust Score, Visibility Score, Authority Score, Content Score, AEO/GEO readiness, Social and Email scores.
- Generates a dynamic executive brief based on the data.
- Applies a knowledge/recommendation engine from `knowledge/recommendation_rules.json`.
- Simulates how actions such as articles, FAQs, LinkedIn posts, newsletters, case studies, and referring domains may affect visibility and business impact.
- Produces a 7-day action plan.
- Exports recommendations as CSV.

## How to run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Cloud

Upload all root files and folders to GitHub:

```text
app.py
requirements.txt
README.md
engines/
parsers/
knowledge/
modules/
```

Then reboot the app in Streamlit Cloud.

## Important

This tool is not a ranking guarantee. It is a decision-support tool that helps prioritize actions based on available data and manual assumptions.

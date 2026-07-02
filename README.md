# Trust & Visibility Intelligence Platform v8

Version v8 adds a dynamic recommendation engine.

## What it does
- Reads optional CSV files from GA4, GSC, LinkedIn, Social Media and Email Marketing.
- Accepts manual inputs when data is unavailable.
- Calculates Trust, Visibility, Authority, Content, Social, Email and AEO/GEO scores.
- Detects the main limitations automatically.
- Generates recommendations that change according to the diagnosis.
- Builds a 7-day sprint based on the weakest areas.
- Explains why each action matters and what business impact it may influence.

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit
Upload these files to the root of your GitHub repository:
- app.py
- requirements.txt
- README.md

Then reboot the app in Streamlit Community Cloud.

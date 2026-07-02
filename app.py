import io
import re
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Trust & Visibility Intelligence Platform", page_icon="📈", layout="wide")

APP_VERSION = "v5.0 Trust + Visibility + Social + 7-Day Sprint"

# -----------------------------
# Helpers
# -----------------------------

def clamp(x, low=0, high=100):
    try:
        return max(low, min(high, float(x)))
    except Exception:
        return 0


def safe_div(a, b):
    try:
        if b in [0, None] or pd.isna(b):
            return 0
        return float(a) / float(b)
    except Exception:
        return 0


def normalize_columns(df):
    df = df.copy()
    df.columns = [str(c).strip().lower().replace(" ", "_").replace("-", "_") for c in df.columns]
    return df


def read_any_csv(uploaded_file):
    if uploaded_file is None:
        return None
    raw = uploaded_file.getvalue()
    for enc in ["utf-8", "utf-8-sig", "latin1"]:
        try:
            text = raw.decode(enc)
            break
        except Exception:
            text = None
    if text is None:
        return None

    lines = [ln for ln in text.splitlines() if ln.strip()]
    # Try normal csv first
    for skip in range(0, min(12, len(lines))):
        try:
            df = pd.read_csv(io.StringIO("\n".join(lines[skip:])))
            if df.shape[1] >= 2 and df.shape[0] >= 1:
                return normalize_columns(df)
        except Exception:
            pass
    # fallback comma separated parsing
    try:
        df = pd.read_csv(io.BytesIO(raw), engine="python", on_bad_lines="skip")
        return normalize_columns(df)
    except Exception:
        return None


def find_col(df, candidates):
    if df is None or df.empty:
        return None
    cols = list(df.columns)
    for cand in candidates:
        cand_norm = cand.lower().replace(" ", "_").replace("-", "_")
        if cand_norm in cols:
            return cand_norm
    for col in cols:
        for cand in candidates:
            if cand.lower().replace(" ", "_") in col:
                return col
    return None


def to_num(series):
    if series is None:
        return pd.Series(dtype=float)
    return pd.to_numeric(series.astype(str).str.replace("%", "", regex=False).str.replace(",", "", regex=False), errors="coerce").fillna(0)


def score_from_count(value, target):
    return clamp((safe_div(value, target)) * 100)


def score_from_inverse(value, target_bad):
    return clamp(100 - (safe_div(value, target_bad) * 100))

# -----------------------------
# Sidebar inputs
# -----------------------------

st.sidebar.title("Data Hub")
st.sidebar.caption(APP_VERSION)

website_url = st.sidebar.text_input("Website URL", value="https://www.scalto.com")
company_name = st.sidebar.text_input("Company / Brand", value="Scalto")
industry = st.sidebar.selectbox("Industry", ["B2B Services", "Fintech", "Wealth Management", "SaaS", "Professional Services", "Other"])

st.sidebar.markdown("---")
st.sidebar.subheader("Upload CSVs")
gsc_file = st.sidebar.file_uploader("Google Search Console CSV", type=["csv"], key="gsc")
ga4_file = st.sidebar.file_uploader("Google Analytics 4 CSV", type=["csv"], key="ga4")
linkedin_file = st.sidebar.file_uploader("LinkedIn Analytics CSV", type=["csv"], key="linkedin")
social_file = st.sidebar.file_uploader("Social Media CSV", type=["csv"], key="social")
email_file = st.sidebar.file_uploader("Email Marketing CSV", type=["csv"], key="email")

st.sidebar.markdown("---")
st.sidebar.subheader("Authority Data")
st.sidebar.caption("Use manual values if you cannot export Ahrefs / SEMrush.")
domain_rating = st.sidebar.number_input("Domain Rating / Authority Score", min_value=0, max_value=100, value=22)
referring_domains = st.sidebar.number_input("Referring Domains", min_value=0, value=127)
backlinks = st.sidebar.number_input("Backlinks", min_value=0, value=549)
organic_keywords_manual = st.sidebar.number_input("Organic Keywords", min_value=0, value=4)
organic_traffic_manual = st.sidebar.number_input("Monthly Organic Traffic", min_value=0, value=36)

st.sidebar.markdown("---")
st.sidebar.subheader("Business Model")
visitor_to_lead = st.sidebar.slider("Visitor to Lead Rate", 0.0, 20.0, 1.5, 0.1) / 100
lead_to_opp = st.sidebar.slider("Lead to Opportunity Rate", 0.0, 100.0, 25.0, 1.0) / 100
opp_to_client = st.sidebar.slider("Opportunity to Client Rate", 0.0, 100.0, 20.0, 1.0) / 100
avg_deal_value = st.sidebar.number_input("Average Deal Value / LTV", min_value=0, value=18000, step=500)

# -----------------------------
# Manual audit tabs inputs
# -----------------------------

st.title("Trust & Visibility Intelligence Platform")
st.caption("A strategic simulator for SEO, AEO/GEO, trust signals, social visibility, email impact, and 7-day action planning. No OpenAI API required.")

with st.expander("How to use this app", expanded=False):
    st.write("""
    1. Upload whatever data you have. The app works even if you only enter manual values.
    2. Use the checkboxes and counts to describe the current website and brand presence.
    3. Review the Trust Score, Visibility Score, and Opportunity Engine.
    4. Use the 7-Day Sprint as a practical execution plan.

    Important: this is a strategic projection model, not a guarantee of ranking or revenue. Use it to compare scenarios and prioritize work.
    """)

# Load data
with st.spinner("Reading uploaded files..."):
    gsc = read_any_csv(gsc_file)
    ga4 = read_any_csv(ga4_file)
    linkedin = read_any_csv(linkedin_file)
    social = read_any_csv(social_file)
    email = read_any_csv(email_file)

# Extract metrics
metrics = {}

if gsc is not None:
    clicks_col = find_col(gsc, ["clicks"])
    impressions_col = find_col(gsc, ["impressions"])
    ctr_col = find_col(gsc, ["ctr"])
    position_col = find_col(gsc, ["position", "average_position"])
    query_col = find_col(gsc, ["query", "queries"])
    page_col = find_col(gsc, ["page", "landing_page"])
    metrics["gsc_clicks"] = to_num(gsc[clicks_col]).sum() if clicks_col else 0
    metrics["gsc_impressions"] = to_num(gsc[impressions_col]).sum() if impressions_col else 0
    metrics["gsc_ctr"] = safe_div(metrics["gsc_clicks"], metrics["gsc_impressions"]) * 100
    metrics["gsc_avg_position"] = to_num(gsc[position_col]).replace(0, np.nan).mean() if position_col else 0
    metrics["gsc_queries"] = gsc[query_col].nunique() if query_col else len(gsc)
    metrics["gsc_pages"] = gsc[page_col].nunique() if page_col else 0
else:
    metrics.update({"gsc_clicks": 0, "gsc_impressions": 0, "gsc_ctr": 0, "gsc_avg_position": 0, "gsc_queries": organic_keywords_manual, "gsc_pages": 0})

if ga4 is not None:
    sessions_col = find_col(ga4, ["sessions", "engaged_sessions"])
    users_col = find_col(ga4, ["users", "active_users", "total_users"])
    conversions_col = find_col(ga4, ["conversions", "key_events", "events"])
    metrics["ga4_sessions"] = to_num(ga4[sessions_col]).sum() if sessions_col else organic_traffic_manual
    metrics["ga4_users"] = to_num(ga4[users_col]).sum() if users_col else 0
    metrics["ga4_conversions"] = to_num(ga4[conversions_col]).sum() if conversions_col else 0
else:
    metrics.update({"ga4_sessions": organic_traffic_manual, "ga4_users": 0, "ga4_conversions": 0})

if linkedin is not None:
    li_impressions = find_col(linkedin, ["impressions", "views"])
    li_clicks = find_col(linkedin, ["clicks", "link_clicks"])
    li_eng = find_col(linkedin, ["engagements", "reactions", "likes"])
    metrics["linkedin_impressions"] = to_num(linkedin[li_impressions]).sum() if li_impressions else 0
    metrics["linkedin_clicks"] = to_num(linkedin[li_clicks]).sum() if li_clicks else 0
    metrics["linkedin_engagements"] = to_num(linkedin[li_eng]).sum() if li_eng else 0
else:
    metrics.update({"linkedin_impressions": 0, "linkedin_clicks": 0, "linkedin_engagements": 0})

if social is not None:
    s_impressions = find_col(social, ["impressions", "reach", "views"])
    s_clicks = find_col(social, ["clicks", "link_clicks"])
    s_eng = find_col(social, ["engagements", "likes", "comments", "shares"])
    metrics["social_impressions"] = to_num(social[s_impressions]).sum() if s_impressions else 0
    metrics["social_clicks"] = to_num(social[s_clicks]).sum() if s_clicks else 0
    metrics["social_engagements"] = to_num(social[s_eng]).sum() if s_eng else 0
else:
    metrics.update({"social_impressions": 0, "social_clicks": 0, "social_engagements": 0})

if email is not None:
    sent_col = find_col(email, ["sent", "recipients", "delivered"])
    open_col = find_col(email, ["opens", "open_rate", "opened"])
    click_col = find_col(email, ["clicks", "click_rate", "clicked"])
    metrics["email_sent"] = to_num(email[sent_col]).sum() if sent_col else 0
    metrics["email_opens"] = to_num(email[open_col]).sum() if open_col and "rate" not in open_col else 0
    metrics["email_clicks"] = to_num(email[click_col]).sum() if click_col and "rate" not in click_col else 0
else:
    metrics.update({"email_sent": 0, "email_opens": 0, "email_clicks": 0})

# Main input panel
st.subheader("Current Website & Brand Signals")
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**Content Assets**")
    service_pages = st.number_input("Service Pages", min_value=0, value=8)
    blog_articles = st.number_input("Blog Articles", min_value=0, value=94)
    case_studies = st.number_input("Case Studies", min_value=0, value=7)
    videos = st.number_input("Videos", min_value=0, value=10)
    faq_blocks = st.number_input("FAQ Blocks / Questions", min_value=0, value=22)

with col2:
    st.markdown("**Trust Signals**")
    founders_visible = st.checkbox("Founders visible on website", value=True)
    team_visible = st.checkbox("Team page / people visible", value=True)
    author_bios = st.checkbox("Articles have author bios", value=False)
    testimonials = st.checkbox("Testimonials visible", value=True)
    client_logos = st.checkbox("Client logos visible", value=True)
    credentials = st.checkbox("Credentials / certifications / awards", value=False)
    clear_about = st.checkbox("Clear About page", value=True)

with col3:
    st.markdown("**AEO / GEO Readiness**")
    faq_schema = st.checkbox("FAQ Schema", value=False)
    org_schema = st.checkbox("Organization Schema", value=False)
    article_schema = st.checkbox("Article Schema", value=False)
    person_schema = st.checkbox("Person Schema", value=False)
    breadcrumb_schema = st.checkbox("Breadcrumb Schema", value=False)
    direct_answers = st.checkbox("Direct answers in content", value=True)
    external_citations = st.checkbox("External citations / sources", value=False)
    tables_lists = st.checkbox("Tables, lists, definitions", value=True)

st.subheader("Scenario: Work Planned")
sc1, sc2, sc3, sc4 = st.columns(4)
with sc1:
    pages_to_update = st.slider("Existing pages to update", 0, 50, 6)
    new_pages = st.slider("New pages / pillars", 0, 30, 3)
with sc2:
    new_case_studies = st.slider("New case studies", 0, 10, 1)
    new_faqs = st.slider("New FAQ blocks", 0, 50, 10)
with sc3:
    linkedin_posts = st.slider("LinkedIn posts this month", 0, 50, 8)
    social_posts = st.slider("Other social posts this month", 0, 80, 12)
with sc4:
    newsletters = st.slider("Newsletters this month", 0, 20, 2)
    community_actions = st.slider("Reddit/community actions", 0, 30, 5)

# -----------------------------
# Scores
# -----------------------------

technical_score = np.mean([
    70 if org_schema else 45,
    80 if breadcrumb_schema else 50,
    75 if direct_answers else 45,
    70 if tables_lists else 50,
])

content_score = np.mean([
    score_from_count(service_pages, 10),
    score_from_count(blog_articles, 80),
    score_from_count(case_studies, 8),
    score_from_count(faq_blocks, 40),
    score_from_count(videos, 20),
])

eeat_score = np.mean([
    100 if founders_visible else 40,
    100 if team_visible else 40,
    100 if author_bios else 35,
    100 if clear_about else 50,
    100 if credentials else 45,
])

social_proof_score = np.mean([
    score_from_count(case_studies, 8),
    100 if testimonials else 35,
    100 if client_logos else 35,
    score_from_count(referring_domains, 250),
])

authority_score = np.mean([
    domain_rating,
    score_from_count(referring_domains, 300),
    score_from_count(backlinks, 1000),
    score_from_count(organic_keywords_manual + metrics.get("gsc_queries", 0), 500),
])

aeo_score = np.mean([
    100 if faq_schema else 30,
    100 if org_schema else 40,
    100 if article_schema else 35,
    100 if person_schema else 30,
    100 if direct_answers else 40,
    100 if external_citations else 45,
    100 if tables_lists else 55,
])

social_presence_score = np.mean([
    score_from_count(metrics.get("linkedin_impressions", 0), 50000),
    score_from_count(metrics.get("linkedin_clicks", 0), 1000),
    score_from_count(metrics.get("social_impressions", 0), 50000),
    score_from_count(metrics.get("social_engagements", 0), 2500),
    score_from_count(linkedin_posts + social_posts, 30),
])

email_score = np.mean([
    score_from_count(metrics.get("email_sent", 0), 5000),
    score_from_count(metrics.get("email_clicks", 0), 250),
    score_from_count(newsletters, 4),
])

trust_score = (
    eeat_score * 0.25
    + social_proof_score * 0.20
    + authority_score * 0.20
    + content_score * 0.20
    + aeo_score * 0.15
)

visibility_score = (
    technical_score * 0.15
    + content_score * 0.20
    + authority_score * 0.20
    + aeo_score * 0.20
    + social_presence_score * 0.15
    + email_score * 0.10
)

# Scenario lift
seo_lift = clamp((pages_to_update * 1.2) + (new_pages * 2.2) + (new_faqs * 0.35) + (new_case_studies * 1.8) + (community_actions * 0.4), 0, 60)
aeo_lift = clamp((new_faqs * 0.8) + (new_pages * 1.5) + (faq_schema is False) * 7 + (person_schema is False) * 5 + (external_citations is False) * 4, 0, 55)
social_lift = clamp((linkedin_posts * 1.1) + (social_posts * 0.6) + (community_actions * 1.0), 0, 60)
trust_lift = clamp((new_case_studies * 3) + (new_pages * 1.1) + (pages_to_update * 0.7) + (community_actions * 0.5), 0, 45)
email_lift = clamp(newsletters * 4 + new_case_studies * 2, 0, 35)

projected_trust = clamp(trust_score + trust_lift)
projected_visibility = clamp(visibility_score + (seo_lift * 0.35 + aeo_lift * 0.25 + social_lift * 0.2 + email_lift * 0.1))

base_sessions = max(metrics.get("ga4_sessions", 0), metrics.get("gsc_clicks", 0), organic_traffic_manual)
session_lift_pct = (seo_lift * 0.008) + (social_lift * 0.004) + (email_lift * 0.003)
incremental_sessions = int(base_sessions * session_lift_pct)
incremental_leads = incremental_sessions * visitor_to_lead
incremental_opps = incremental_leads * lead_to_opp
incremental_clients = incremental_opps * opp_to_client
incremental_revenue = incremental_clients * avg_deal_value

# -----------------------------
# Dashboard
# -----------------------------

st.subheader("Executive Dashboard")
a, b, c, d = st.columns(4)
a.metric("Trust Score", f"{trust_score:.0f}/100", f"Projected {projected_trust:.0f}")
b.metric("Visibility Score", f"{visibility_score:.0f}/100", f"Projected {projected_visibility:.0f}")
c.metric("Projected Sessions", f"+{incremental_sessions:,}")
d.metric("Projected Revenue", f"${incremental_revenue:,.0f}")

st.subheader("Score Breakdown")
b1, b2, b3, b4, b5, b6 = st.columns(6)
b1.metric("EEAT", f"{eeat_score:.0f}")
b2.metric("Authority", f"{authority_score:.0f}")
b3.metric("Content", f"{content_score:.0f}")
b4.metric("AEO/GEO", f"{aeo_score:.0f}")
b5.metric("Social", f"{social_presence_score:.0f}")
b6.metric("Email", f"{email_score:.0f}")

# Charts
chart_df = pd.DataFrame({
    "Area": ["Technical SEO", "Content", "Authority", "AEO/GEO", "Social", "Email", "Trust"],
    "Score": [technical_score, content_score, authority_score, aeo_score, social_presence_score, email_score, trust_score]
})
st.bar_chart(chart_df.set_index("Area"))

# Data preview tabs
st.subheader("Uploaded Data Summary")
tab1, tab2, tab3, tab4, tab5 = st.tabs(["GSC", "GA4", "LinkedIn", "Social", "Email"])
for tab, name, df in [(tab1, "Google Search Console", gsc), (tab2, "Google Analytics", ga4), (tab3, "LinkedIn", linkedin), (tab4, "Social Media", social), (tab5, "Email", email)]:
    with tab:
        if df is None:
            st.info(f"No {name} CSV uploaded yet.")
        else:
            st.write(f"{name}: {df.shape[0]} rows, {df.shape[1]} columns")
            st.dataframe(df.head(25), use_container_width=True)

# Opportunity Engine
st.subheader("Opportunity Engine")
opportunities = []

def add_op(title, reason, impact, effort, owner="Marketing"):
    roi = impact / max(effort, 1)
    opportunities.append({"Action": title, "Why it matters": reason, "Impact": impact, "Effort": effort, "ROI Score": round(roi, 2), "Owner": owner})

if not faq_schema:
    add_op("Add FAQ Schema to core service pages", "Improves AEO/GEO readiness and answer extraction.", 9, 2, "SEO/Web")
if not person_schema and (founders_visible or team_visible):
    add_op("Add Person Schema for founders and key experts", "Strengthens EEAT and entity clarity.", 8, 2, "SEO/Web")
if not author_bios:
    add_op("Add author bios to articles", "Improves expertise signals and trust.", 8, 3, "Content")
if case_studies < 5:
    add_op("Publish at least one proof-driven case study", "Improves conversion trust and sales enablement.", 10, 5, "Content/Sales")
if metrics.get("gsc_ctr", 0) < 2 and metrics.get("gsc_impressions", 0) > 0:
    add_op("Rewrite titles and meta descriptions for high-impression pages", "Low CTR means existing visibility is underused.", 9, 3, "SEO/Content")
if domain_rating < 30 or referring_domains < 150:
    add_op("Launch digital PR / partner backlink outreach", "Authority is limiting ranking potential.", 8, 6, "PR/Partnerships")
if linkedin_posts < 8:
    add_op("Increase LinkedIn executive posting cadence", "Supports social proof, trust and referral traffic.", 7, 3, "Social/Leadership")
if community_actions < 5:
    add_op("Monitor and answer relevant Reddit/community questions", "Helps discover demand, language, objections and AEO topics.", 6, 3, "Community")
if newsletters < 2:
    add_op("Send newsletter traffic to new content hubs", "Turns owned audience into website engagement and retargeting signals.", 7, 2, "Email")
if external_citations is False:
    add_op("Add credible external citations to strategic pages", "Improves trust, answer quality and AI-readiness.", 6, 2, "Content")

opp_df = pd.DataFrame(opportunities).sort_values("ROI Score", ascending=False)
st.dataframe(opp_df, use_container_width=True, hide_index=True)

# 7-Day Sprint
st.subheader("7-Day Sprint")
sprint = []
base_actions = opp_df.head(7).to_dict("records")
for i in range(7):
    if i < len(base_actions):
        row = base_actions[i]
        sprint.append({"Day": f"Day {i+1}", "Action": row["Action"], "Expected Outcome": row["Why it matters"], "Owner": row["Owner"]})
    else:
        sprint.append({"Day": f"Day {i+1}", "Action": "Review performance and document learnings", "Expected Outcome": "Keep the next sprint grounded in data.", "Owner": "Marketing"})

sprint_df = pd.DataFrame(sprint)
st.dataframe(sprint_df, use_container_width=True, hide_index=True)

# Exports
st.subheader("Export")
report = {
    "generated_at": datetime.utcnow().isoformat(),
    "company": company_name,
    "website": website_url,
    "industry": industry,
    "trust_score": round(trust_score, 2),
    "projected_trust_score": round(projected_trust, 2),
    "visibility_score": round(visibility_score, 2),
    "projected_visibility_score": round(projected_visibility, 2),
    "incremental_sessions": incremental_sessions,
    "incremental_leads": round(incremental_leads, 2),
    "incremental_opportunities": round(incremental_opps, 2),
    "incremental_clients": round(incremental_clients, 2),
    "incremental_revenue": round(incremental_revenue, 2),
}
report_df = pd.DataFrame([report])

c1, c2, c3 = st.columns(3)
c1.download_button("Download Executive Metrics CSV", report_df.to_csv(index=False).encode("utf-8"), "executive_metrics.csv", "text/csv")
c2.download_button("Download Opportunities CSV", opp_df.to_csv(index=False).encode("utf-8"), "opportunities.csv", "text/csv")
c3.download_button("Download 7-Day Sprint CSV", sprint_df.to_csv(index=False).encode("utf-8"), "seven_day_sprint.csv", "text/csv")

st.caption("Model note: projections are directional. They are designed for prioritization, not guaranteed outcomes.")

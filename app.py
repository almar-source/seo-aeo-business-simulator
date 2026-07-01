import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="SEO + AEO Business Impact Simulator", layout="wide")

st.title("SEO + AEO Business Impact Simulator")
st.caption("Simula cómo mejoras SEO, AEO/GEO y de autoridad pueden impactar visibilidad, leads y revenue estimado.")

# -----------------------------
# Helpers
# -----------------------------
def clamp(value, min_value=0, max_value=100):
    return max(min_value, min(max_value, value))


def calculate_scores(inputs, actions):
    technical = (
        inputs["unique_titles"] * 0.18 +
        inputs["unique_meta"] * 0.14 +
        inputs["clean_h_structure"] * 0.14 +
        inputs["mobile_speed"] * 0.18 +
        inputs["indexability"] * 0.18 +
        inputs["internal_linking"] * 0.18
    )

    content = (
        inputs["service_page_quality"] * 0.25 +
        inputs["pillar_pages"] * 0.22 +
        inputs["case_studies"] * 0.18 +
        inputs["content_depth"] * 0.20 +
        inputs["freshness"] * 0.15
    )

    authority = (
        min(inputs["domain_rating"] * 1.6, 100) * 0.35 +
        min(inputs["ref_domains"] / 2, 100) * 0.35 +
        inputs["brand_mentions"] * 0.15 +
        inputs["linkedin_visibility"] * 0.15
    )

    aeo = (
        inputs["schema"] * 0.22 +
        inputs["faq_direct_answers"] * 0.22 +
        inputs["entity_clarity"] * 0.18 +
        inputs["service_specificity"] * 0.18 +
        inputs["proof_signals"] * 0.20
    )

    action_bonus = {
        "Fix duplicated titles and meta descriptions": {"technical": 8, "content": 2, "aeo": 2, "authority": 0},
        "Add schema markup": {"technical": 3, "content": 0, "aeo": 12, "authority": 0},
        "Add FAQs and direct answers": {"technical": 1, "content": 5, "aeo": 14, "authority": 0},
        "Create or improve pillar pages": {"technical": 1, "content": 14, "aeo": 8, "authority": 3},
        "Improve internal linking": {"technical": 10, "content": 5, "aeo": 4, "authority": 2},
        "Improve mobile speed/Core Web Vitals": {"technical": 12, "content": 0, "aeo": 1, "authority": 0},
        "Publish case studies with proof": {"technical": 0, "content": 8, "aeo": 7, "authority": 5},
        "Earn high-quality backlinks/mentions": {"technical": 0, "content": 2, "aeo": 2, "authority": 16},
        "Clarify positioning and entities": {"technical": 0, "content": 6, "aeo": 11, "authority": 4},
    }

    bonuses = {"technical": 0, "content": 0, "aeo": 0, "authority": 0}
    for action in actions:
        for key, value in action_bonus[action].items():
            bonuses[key] += value

    projected = {
        "Technical SEO": clamp(technical + bonuses["technical"]),
        "Content Quality": clamp(content + bonuses["content"]),
        "Authority": clamp(authority + bonuses["authority"]),
        "AEO/GEO Readiness": clamp(aeo + bonuses["aeo"]),
    }

    current = {
        "Technical SEO": clamp(technical),
        "Content Quality": clamp(content),
        "Authority": clamp(authority),
        "AEO/GEO Readiness": clamp(aeo),
    }

    current_seo = current["Technical SEO"] * 0.34 + current["Content Quality"] * 0.33 + current["Authority"] * 0.33
    projected_seo = projected["Technical SEO"] * 0.34 + projected["Content Quality"] * 0.33 + projected["Authority"] * 0.33

    current_aeo = current["AEO/GEO Readiness"] * 0.55 + current["Content Quality"] * 0.25 + current["Authority"] * 0.20
    projected_aeo = projected["AEO/GEO Readiness"] * 0.55 + projected["Content Quality"] * 0.25 + projected["Authority"] * 0.20

    return current, projected, clamp(current_seo), clamp(projected_seo), clamp(current_aeo), clamp(projected_aeo)


def calculate_business_impact(current_seo, projected_seo, current_aeo, projected_aeo, biz):
    seo_lift = max(projected_seo - current_seo, 0)
    aeo_lift = max(projected_aeo - current_aeo, 0)

    # Conservative heuristic: score lift does not translate 1:1 into traffic.
    visibility_lift_pct = (seo_lift * biz["seo_weight"] + aeo_lift * biz["aeo_weight"]) / 100
    visibility_lift_pct *= biz["execution_confidence"] / 100

    current_sessions = biz["monthly_sessions"]
    projected_sessions = current_sessions * (1 + visibility_lift_pct)

    current_leads = current_sessions * (biz["visit_to_lead"] / 100)
    projected_leads = projected_sessions * (biz["visit_to_lead"] / 100)

    current_opps = current_leads * (biz["lead_to_opp"] / 100)
    projected_opps = projected_leads * (biz["lead_to_opp"] / 100)

    current_clients = current_opps * (biz["opp_to_client"] / 100)
    projected_clients = projected_opps * (biz["opp_to_client"] / 100)

    current_revenue = current_clients * biz["avg_deal_value"]
    projected_revenue = projected_clients * biz["avg_deal_value"]

    return {
        "Visibility lift %": visibility_lift_pct * 100,
        "Monthly sessions": projected_sessions,
        "Monthly leads": projected_leads,
        "Monthly opportunities": projected_opps,
        "Monthly clients": projected_clients,
        "Monthly revenue": projected_revenue,
        "Incremental sessions": projected_sessions - current_sessions,
        "Incremental leads": projected_leads - current_leads,
        "Incremental opportunities": projected_opps - current_opps,
        "Incremental clients": projected_clients - current_clients,
        "Incremental revenue": projected_revenue - current_revenue,
        "Current revenue": current_revenue,
    }

# -----------------------------
# Sidebar inputs
# -----------------------------
st.sidebar.header("Current website inputs")
st.sidebar.caption("Use 0 to 100 where exact data is unavailable.")

inputs = {
    "domain_rating": st.sidebar.number_input("Domain Rating", 0, 100, 19),
    "ref_domains": st.sidebar.number_input("Referring domains", 0, 10000, 127),
    "unique_titles": st.sidebar.slider("Unique titles", 0, 100, 35),
    "unique_meta": st.sidebar.slider("Unique meta descriptions", 0, 100, 35),
    "clean_h_structure": st.sidebar.slider("Clean H1/H2 structure", 0, 100, 45),
    "mobile_speed": st.sidebar.slider("Mobile speed/Core Web Vitals", 0, 100, 55),
    "indexability": st.sidebar.slider("Indexability/canonicals/sitemap", 0, 100, 70),
    "internal_linking": st.sidebar.slider("Internal linking", 0, 100, 45),
    "service_page_quality": st.sidebar.slider("Service page quality", 0, 100, 50),
    "pillar_pages": st.sidebar.slider("Pillar pages", 0, 100, 35),
    "case_studies": st.sidebar.slider("Case studies/proof pages", 0, 100, 55),
    "content_depth": st.sidebar.slider("Content depth", 0, 100, 50),
    "freshness": st.sidebar.slider("Content freshness", 0, 100, 45),
    "schema": st.sidebar.slider("Schema markup", 0, 100, 20),
    "faq_direct_answers": st.sidebar.slider("FAQs/direct answers", 0, 100, 25),
    "entity_clarity": st.sidebar.slider("Entity clarity", 0, 100, 35),
    "service_specificity": st.sidebar.slider("Service specificity", 0, 100, 45),
    "proof_signals": st.sidebar.slider("Proof signals for AI answers", 0, 100, 40),
    "brand_mentions": st.sidebar.slider("Brand mentions", 0, 100, 30),
    "linkedin_visibility": st.sidebar.slider("LinkedIn/executive visibility", 0, 100, 45),
}

st.sidebar.header("Business inputs")
biz = {
    "monthly_sessions": st.sidebar.number_input("Current monthly organic sessions", 0, 1000000, 500),
    "visit_to_lead": st.sidebar.number_input("Visit to lead conversion %", 0.0, 100.0, 1.5, step=0.1),
    "lead_to_opp": st.sidebar.number_input("Lead to opportunity conversion %", 0.0, 100.0, 25.0, step=1.0),
    "opp_to_client": st.sidebar.number_input("Opportunity to client conversion %", 0.0, 100.0, 20.0, step=1.0),
    "avg_deal_value": st.sidebar.number_input("Average deal value / client", 0, 10000000, 15000, step=500),
    "execution_confidence": st.sidebar.slider("Execution confidence", 0, 100, 65),
    "seo_weight": st.sidebar.slider("SEO impact weight", 0.0, 3.0, 1.0, step=0.1),
    "aeo_weight": st.sidebar.slider("AEO/GEO impact weight", 0.0, 3.0, 0.8, step=0.1),
}

# -----------------------------
# Main app
# -----------------------------
actions_list = [
    "Fix duplicated titles and meta descriptions",
    "Add schema markup",
    "Add FAQs and direct answers",
    "Create or improve pillar pages",
    "Improve internal linking",
    "Improve mobile speed/Core Web Vitals",
    "Publish case studies with proof",
    "Earn high-quality backlinks/mentions",
    "Clarify positioning and entities",
]

selected_actions = st.multiselect(
    "Choose the SEO/AEO actions you want to simulate",
    actions_list,
    default=[
        "Fix duplicated titles and meta descriptions",
        "Add schema markup",
        "Add FAQs and direct answers",
        "Create or improve pillar pages",
        "Improve internal linking",
    ]
)

current, projected, current_seo, projected_seo, current_aeo, projected_aeo = calculate_scores(inputs, selected_actions)
impact = calculate_business_impact(current_seo, projected_seo, current_aeo, projected_aeo, biz)

col1, col2, col3, col4 = st.columns(4)
col1.metric("SEO score", f"{projected_seo:.0f}/100", f"+{projected_seo - current_seo:.0f}")
col2.metric("AEO/GEO score", f"{projected_aeo:.0f}/100", f"+{projected_aeo - current_aeo:.0f}")
col3.metric("Visibility lift", f"{impact['Visibility lift %']:.1f}%")
col4.metric("Incremental monthly revenue", f"${impact['Incremental revenue']:,.0f}")

st.divider()

left, right = st.columns(2)

with left:
    st.subheader("Current vs projected scores")
    score_df = pd.DataFrame({
        "Area": list(current.keys()),
        "Current": list(current.values()),
        "Projected": list(projected.values())
    })
    st.dataframe(score_df, use_container_width=True, hide_index=True)

    fig, ax = plt.subplots()
    x = np.arange(len(score_df["Area"]))
    width = 0.35
    ax.bar(x - width/2, score_df["Current"], width, label="Current")
    ax.bar(x + width/2, score_df["Projected"], width, label="Projected")
    ax.set_ylabel("Score")
    ax.set_xticks(x)
    ax.set_xticklabels(score_df["Area"], rotation=25, ha="right")
    ax.legend()
    st.pyplot(fig)

with right:
    st.subheader("Business impact projection")
    impact_df = pd.DataFrame([
        {"Metric": "Monthly sessions", "Current": biz["monthly_sessions"], "Projected": impact["Monthly sessions"], "Incremental": impact["Incremental sessions"]},
        {"Metric": "Monthly leads", "Current": biz["monthly_sessions"] * biz["visit_to_lead"] / 100, "Projected": impact["Monthly leads"], "Incremental": impact["Incremental leads"]},
        {"Metric": "Monthly opportunities", "Current": (biz["monthly_sessions"] * biz["visit_to_lead"] / 100) * biz["lead_to_opp"] / 100, "Projected": impact["Monthly opportunities"], "Incremental": impact["Incremental opportunities"]},
        {"Metric": "Monthly clients", "Current": ((biz["monthly_sessions"] * biz["visit_to_lead"] / 100) * biz["lead_to_opp"] / 100) * biz["opp_to_client"] / 100, "Projected": impact["Monthly clients"], "Incremental": impact["Incremental clients"]},
        {"Metric": "Monthly revenue", "Current": impact["Current revenue"], "Projected": impact["Monthly revenue"], "Incremental": impact["Incremental revenue"]},
    ])
    st.dataframe(impact_df, use_container_width=True, hide_index=True)

    fig2, ax2 = plt.subplots()
    revenue_months = [impact["Current revenue"], impact["Monthly revenue"]]
    ax2.bar(["Current", "Projected"], revenue_months)
    ax2.set_ylabel("Estimated monthly revenue")
    st.pyplot(fig2)

st.divider()

st.subheader("Priority actions")
priority_notes = []
if projected["AEO/GEO Readiness"] < 60:
    priority_notes.append("Strengthen AEO/GEO readiness with schema, FAQs, direct answers, entity clarity and proof signals.")
if projected["Authority"] < 55:
    priority_notes.append("Increase authority through quality backlinks, partner mentions, PR, LinkedIn visibility and case-study citations.")
if projected["Technical SEO"] < 65:
    priority_notes.append("Fix technical issues first: duplicated metadata, H structure, internal linking, mobile speed, indexability and canonicals.")
if projected["Content Quality"] < 65:
    priority_notes.append("Improve service pages and pillar pages so search engines and AI tools can understand exactly what the company does.")
if not priority_notes:
    priority_notes.append("The simulated plan is strong. Next step: validate with actual GA4, GSC, Ahrefs/Semrush and AI citation tracking data.")

for note in priority_notes:
    st.write("- " + note)

st.info("This is a planning simulator, not a guaranteed forecast. It uses transparent scoring rules so you can run scenarios without consuming AI tokens.")

csv = pd.concat([
    score_df.assign(Type="Score"),
    impact_df.rename(columns={"Metric": "Area"}).assign(Type="Business impact")
], ignore_index=True)

st.download_button(
    "Download simulation CSV",
    csv.to_csv(index=False).encode("utf-8"),
    "seo_aeo_business_simulation.csv",
    "text/csv"
)

import io
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="SEO + AEO + Business Impact Simulator", layout="wide")

st.title("SEO + AEO/GEO + Business Impact Simulator")
st.caption("Versión v3.3 con lector robusto para exports irregulares de GA4")
st.caption("Carga datos reales de GSC, GA4, YouTube y Email Marketing. Simula cómo cambios de contenido, acciones offsite y campañas afectan ranking, tráfico, leads y revenue.")

# -----------------------------
# Utility functions
# -----------------------------
def clamp(value, min_value=0, max_value=100):
    return max(min_value, min(max_value, float(value)))


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [
        str(c).strip().lower()
        .replace(" ", "_")
        .replace("%", "pct")
        .replace("/", "_")
        .replace("-", "_")
        for c in df.columns
    ]
    return df




def try_parse_sectioned_csv(raw: bytes) -> pd.DataFrame | None:
    """Parse GA4 exports that contain many small CSV tables in one file.

    Example:
    # Start date...
    Nth week,Active users
    0000,29
    ...

    # Start date...
    Nth week,New users
    0000,27

    Pandas read_csv can fail because the file has repeated headers and sections.
    This function merges those sections into one table using the first column
    as the dimension, usually nth_week, date, channel, source, or page.
    """
    text = None
    for enc in ["utf-8-sig", "utf-8", "latin-1", "cp1252"]:
        try:
            text = raw.decode(enc)
            break
        except Exception:
            continue
    if not text:
        return None

    import csv
    lines = text.splitlines()
    sections = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line or line.startswith("#"):
            i += 1
            continue
        try:
            header = next(csv.reader([line]))
        except Exception:
            i += 1
            continue
        header = [h.strip() for h in header]
        if len(header) < 2:
            i += 1
            continue

        rows = []
        j = i + 1
        while j < len(lines):
            row_line = lines[j].strip()
            if not row_line:
                break
            if row_line.startswith("#"):
                break
            try:
                row = next(csv.reader([row_line]))
            except Exception:
                break
            if len(row) != len(header):
                break
            # A repeated header means a new section starts.
            if [x.strip().lower() for x in row] == [x.strip().lower() for x in header]:
                break
            rows.append([x.strip() for x in row])
            j += 1

        if rows and len(rows) >= 2:
            section = pd.DataFrame(rows, columns=header)
            sections.append(section)
        i = max(j + 1, i + 1)

    if not sections:
        return None

    normalized_sections = []
    for idx, sec in enumerate(sections):
        nsec = normalize_columns(sec)
        if len(nsec.columns) >= 2:
            nsec["_section_number"] = idx + 1
            nsec["_section_dimension"] = nsec.columns[0]
            normalized_sections.append(nsec)

    if not normalized_sections:
        return None

    # Keep all GA4 mini-tables. Outer concat lets ga4_metrics find sessions,
    # users, conversions, channel tables, and page tables even when they were
    # exported as separate blocks in one CSV file.
    combined = pd.concat(normalized_sections, ignore_index=True, sort=False)
    combined = combined.dropna(how="all")
    if len(combined.columns) >= 2 and len(combined) > 0:
        return combined
    return None


def find_col(df: pd.DataFrame, candidates):
    cols = list(df.columns)
    for c in candidates:
        if c in cols:
            return c
    for col in cols:
        for c in candidates:
            if c in col:
                return col
    return None


def to_numeric(series):
    return pd.to_numeric(
        series.astype(str).str.replace(",", "", regex=False).str.replace("%", "", regex=False),
        errors="coerce",
    ).fillna(0)


def read_uploaded_csv(uploaded_file):
    """Read messy CSV exports from GA4, GSC, YouTube, Mailchimp, HubSpot, etc.

    GA4 exports often include metadata rows, notes, different separators, or irregular
    rows. This reader tries multiple encodings, delimiters, and header offsets instead
    of crashing the Streamlit app.
    """
    if uploaded_file is None:
        return None

    raw = uploaded_file.getvalue()
    if not raw:
        return None

    # Remove UTF-8 BOM if present.
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]

    # GA4 Acquisition Overview often exports as multiple small CSV tables in one file.
    # Parse that structure first, because regular read_csv may crash or select only one table.
    sectioned = try_parse_sectioned_csv(raw)
    if sectioned is not None and not sectioned.empty:
        return sectioned

    # First pass: try flexible CSV parsing with multiple encodings and skipped rows.
    encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
    seps = [None, ",", ";", "\t"]
    best_df = None

    for enc in encodings:
        for skiprows in range(0, 20):
            for sep in seps:
                try:
                    df = pd.read_csv(
                        io.BytesIO(raw),
                        encoding=enc,
                        sep=sep,
                        engine="python",
                        skiprows=skiprows,
                        on_bad_lines="skip",
                    )
                    df = df.dropna(how="all")
                    df = df.loc[:, ~df.columns.astype(str).str.contains(r"^Unnamed", case=False, regex=True)]
                    if df.empty or len(df.columns) < 2:
                        continue
                    norm = normalize_columns(df)
                    useful_names = " ".join(norm.columns.astype(str).tolist())
                    signal_words = [
                        "session", "users", "views", "event", "conversion", "revenue",
                        "click", "impression", "query", "page", "opens", "sent", "delivered",
                        "video", "watch", "subscribers"
                    ]
                    score = sum(1 for w in signal_words if w in useful_names) + min(len(norm), 100) / 100
                    if best_df is None or score > best_df[0]:
                        best_df = (score, norm)
                except Exception:
                    continue

    if best_df is not None:
        return best_df[1]

    # Last-resort fallback: make the error visible but do not break the app.
    st.warning(f"No pude leer el archivo {uploaded_file.name}. Revisa que sea CSV exportado como tabla, no PDF/HTML.")
    return None


def gsc_metrics(df):
    if df is None or df.empty:
        return None
    clicks_col = find_col(df, ["clicks", "clics"])
    impressions_col = find_col(df, ["impressions", "impresiones"])
    ctr_col = find_col(df, ["ctr"])
    pos_col = find_col(df, ["position", "posicion", "posición", "avg_position", "average_position"])
    query_col = find_col(df, ["query", "queries", "consulta", "consultas", "keyword", "keywords"])
    page_col = find_col(df, ["page", "pages", "pagina", "página", "landing_page"])

    clicks = to_numeric(df[clicks_col]).sum() if clicks_col else 0
    impressions = to_numeric(df[impressions_col]).sum() if impressions_col else 0
    ctr = (clicks / impressions * 100) if impressions else (to_numeric(df[ctr_col]).mean() if ctr_col else 0)
    avg_pos = to_numeric(df[pos_col]).replace(0, np.nan).mean() if pos_col else 0
    queries = df[query_col].nunique() if query_col else len(df)
    pages = df[page_col].nunique() if page_col else 0

    opportunities = pd.DataFrame()
    if impressions_col and pos_col:
        tmp = df.copy()
        tmp["impressions_num"] = to_numeric(tmp[impressions_col])
        tmp["position_num"] = to_numeric(tmp[pos_col])
        tmp["clicks_num"] = to_numeric(tmp[clicks_col]) if clicks_col else 0
        tmp["ctr_num"] = to_numeric(tmp[ctr_col]) if ctr_col else np.where(tmp["impressions_num"] > 0, tmp["clicks_num"] / tmp["impressions_num"] * 100, 0)
        tmp["opportunity_type"] = np.select(
            [
                (tmp["position_num"].between(4, 12)) & (tmp["impressions_num"] >= tmp["impressions_num"].quantile(0.60)),
                (tmp["position_num"].between(13, 30)) & (tmp["impressions_num"] >= tmp["impressions_num"].quantile(0.60)),
                (tmp["position_num"] <= 10) & (tmp["ctr_num"] < 1.0) & (tmp["impressions_num"] > 100),
            ],
            [
                "Near page-one lift: refresh content and improve internal links",
                "Content gap: expand topical coverage",
                "CTR gap: improve title/meta and snippet promise",
            ],
            default="Monitor",
        )
        visible_cols = [c for c in [query_col, page_col, clicks_col, impressions_col, ctr_col, pos_col, "opportunity_type"] if c]
        opportunities = tmp.sort_values(["impressions_num", "position_num"], ascending=[False, True])[visible_cols].head(30)

    return {"clicks": clicks, "impressions": impressions, "ctr": ctr, "avg_position": avg_pos, "queries": queries, "pages": pages, "opportunities": opportunities}


def ga4_metrics(df):
    if df is None or df.empty:
        return None
    sessions_col = find_col(df, ["sessions", "sesiones"])
    users_col = find_col(df, ["users", "active_users", "usuarios", "total_users"])
    conversions_col = find_col(df, ["conversions", "key_events", "conversiones", "event_count"])
    channel_col = find_col(df, ["session_default_channel_group", "default_channel_group", "channel", "canal"])
    source_col = find_col(df, ["source", "medium", "source_medium", "session_source_medium"])
    page_col = find_col(df, ["landing_page", "page_path", "page", "pagina", "página"])

    sessions = to_numeric(df[sessions_col]).sum() if sessions_col else 0
    users = to_numeric(df[users_col]).sum() if users_col else 0
    conversions = to_numeric(df[conversions_col]).sum() if conversions_col else 0
    cvr = conversions / sessions * 100 if sessions else 0
    top = pd.DataFrame()
    group_col = page_col or channel_col or source_col
    if group_col and sessions_col:
        agg = {sessions_col: "sum"}
        if conversions_col:
            agg[conversions_col] = "sum"
        top = df.groupby(group_col, dropna=False).agg(agg).reset_index().sort_values(sessions_col, ascending=False).head(20)
    return {"sessions": sessions, "users": users, "conversions": conversions, "cvr": cvr, "top": top}


def yt_metrics(df):
    if df is None or df.empty:
        return None
    views_col = find_col(df, ["views", "vistas", "visualizaciones"])
    watch_col = find_col(df, ["watch_time", "watch_time_hours", "tiempo_de_reproducción", "tiempo_de_visualización"])
    impressions_col = find_col(df, ["impressions", "impresiones"])
    ctr_col = find_col(df, ["impressions_ctr", "ctr"])
    title_col = find_col(df, ["video_title", "title", "titulo", "título", "content"])
    views = to_numeric(df[views_col]).sum() if views_col else 0
    watch = to_numeric(df[watch_col]).sum() if watch_col else 0
    impressions = to_numeric(df[impressions_col]).sum() if impressions_col else 0
    ctr = to_numeric(df[ctr_col]).mean() if ctr_col else 0
    top = df.sort_values(views_col, ascending=False).head(15) if title_col and views_col else pd.DataFrame()
    return {"views": views, "watch_time": watch, "impressions": impressions, "ctr": ctr, "top": top}


def email_metrics(df):
    if df is None or df.empty:
        return None
    sent_col = find_col(df, ["sent", "recipients", "envios", "enviados", "delivered"])
    delivered_col = find_col(df, ["delivered", "entregados"])
    opens_col = find_col(df, ["opens", "unique_opens", "open", "aperturas"])
    clicks_col = find_col(df, ["clicks", "unique_clicks", "clics"])
    unsub_col = find_col(df, ["unsubscribed", "unsubscribes", "bajas"])
    campaign_col = find_col(df, ["campaign", "campaign_name", "subject", "email", "name", "campaña"])

    sent = to_numeric(df[sent_col]).sum() if sent_col else 0
    delivered = to_numeric(df[delivered_col]).sum() if delivered_col else sent
    opens = to_numeric(df[opens_col]).sum() if opens_col else 0
    clicks = to_numeric(df[clicks_col]).sum() if clicks_col else 0
    unsub = to_numeric(df[unsub_col]).sum() if unsub_col else 0
    open_rate = opens / delivered * 100 if delivered else 0
    click_rate = clicks / delivered * 100 if delivered else 0
    click_to_open = clicks / opens * 100 if opens else 0
    unsub_rate = unsub / delivered * 100 if delivered else 0
    top = pd.DataFrame()
    if campaign_col:
        cols = [c for c in [campaign_col, sent_col, delivered_col, opens_col, clicks_col, unsub_col] if c]
        top = df[cols].head(20)
    return {"sent": sent, "delivered": delivered, "opens": opens, "clicks": clicks, "open_rate": open_rate, "click_rate": click_rate, "click_to_open": click_to_open, "unsub_rate": unsub_rate, "top": top}


def calculate_content_effect(content_inputs):
    """Estimates ranking movement and visibility lift from content-specific changes."""
    score = 0
    score += content_inputs["pages_refreshed"] * 1.6
    score += content_inputs["new_pages"] * 2.4
    score += content_inputs["faq_blocks"] * 1.1
    score += content_inputs["case_studies_added"] * 2.0
    score += content_inputs["internal_links_added"] * 0.22
    score += content_inputs["content_quality_delta"] * 0.55
    score += content_inputs["topical_coverage_delta"] * 0.65
    score += content_inputs["eeat_proof_delta"] * 0.50
    score *= content_inputs["implementation_quality"] / 100

    estimated_position_gain = min(8.0, score / 10)
    ctr_lift = min(35.0, content_inputs["title_meta_improvement"] * 0.45)
    snippet_aeo_lift = min(45.0, (content_inputs["faq_blocks"] * 2.2 + content_inputs["structured_answer_delta"] * 0.55))
    content_visibility_lift = min(90.0, score * 0.75 + ctr_lift * 0.35 + snippet_aeo_lift * 0.25)

    return {
        "content_action_score": clamp(score),
        "estimated_position_gain": estimated_position_gain,
        "ctr_lift_pct": ctr_lift,
        "snippet_aeo_lift_pct": snippet_aeo_lift,
        "content_visibility_lift_pct": content_visibility_lift,
    }


def calculate_email_effect(email_inputs, email_data):
    list_size = email_inputs["list_size"]
    open_rate = email_data["open_rate"] if email_data and email_data["open_rate"] > 0 else email_inputs["open_rate"]
    click_rate = email_data["click_rate"] if email_data and email_data["click_rate"] > 0 else email_inputs["click_rate"]

    projected_open_rate = min(80, open_rate + email_inputs["subject_line_lift"] + email_inputs["segmentation_lift"] * 0.45)
    projected_click_rate = min(30, click_rate + email_inputs["cta_lift"] + email_inputs["content_relevance_lift"] * 0.35 + email_inputs["segmentation_lift"] * 0.25)
    sends = list_size * email_inputs["campaigns_per_month"]
    current_clicks = sends * click_rate / 100
    projected_clicks = sends * projected_click_rate / 100
    assisted_organic_lift = min(18, (projected_clicks - current_clicks) / max(sends, 1) * 100 * 1.8 + email_inputs["newsletter_to_content"] * 0.25)

    return {
        "current_open_rate": open_rate,
        "projected_open_rate": projected_open_rate,
        "current_click_rate": click_rate,
        "projected_click_rate": projected_click_rate,
        "current_email_clicks": current_clicks,
        "projected_email_clicks": projected_clicks,
        "incremental_email_clicks": projected_clicks - current_clicks,
        "assisted_organic_lift_pct": assisted_organic_lift,
    }


def calculate_scores(inputs, actions, data_signal, content_effect, email_effect):
    technical = (
        inputs["unique_titles"] * 0.18 + inputs["unique_meta"] * 0.14 + inputs["clean_h_structure"] * 0.14 +
        inputs["mobile_speed"] * 0.18 + inputs["indexability"] * 0.18 + inputs["internal_linking"] * 0.18
    )
    content = (
        inputs["service_page_quality"] * 0.22 + inputs["pillar_pages"] * 0.20 + inputs["case_studies"] * 0.16 +
        inputs["content_depth"] * 0.18 + inputs["freshness"] * 0.12 + data_signal["search_demand_score"] * 0.12
    )
    authority = (
        min(inputs["domain_rating"] * 1.6, 100) * 0.32 + min(inputs["ref_domains"] / 2, 100) * 0.30 +
        inputs["brand_mentions"] * 0.14 + inputs["linkedin_visibility"] * 0.12 + data_signal["offsite_signal"] * 0.12
    )
    aeo = (
        inputs["schema"] * 0.20 + inputs["faq_direct_answers"] * 0.20 + inputs["entity_clarity"] * 0.17 +
        inputs["service_specificity"] * 0.16 + inputs["proof_signals"] * 0.17 + data_signal["query_intent_score"] * 0.10
    )

    action_bonus = {
        "Fix duplicated titles and meta descriptions": {"technical": 8, "content": 2, "aeo": 2, "authority": 0, "biz": 0.02},
        "Add schema markup": {"technical": 3, "content": 0, "aeo": 12, "authority": 0, "biz": 0.01},
        "Add FAQs and direct answers": {"technical": 1, "content": 5, "aeo": 14, "authority": 0, "biz": 0.03},
        "Create or improve pillar pages": {"technical": 1, "content": 14, "aeo": 8, "authority": 3, "biz": 0.05},
        "Improve internal linking": {"technical": 10, "content": 5, "aeo": 4, "authority": 2, "biz": 0.02},
        "Improve mobile speed/Core Web Vitals": {"technical": 12, "content": 0, "aeo": 1, "authority": 0, "biz": 0.01},
        "Publish case studies with proof": {"technical": 0, "content": 8, "aeo": 7, "authority": 5, "biz": 0.04},
        "Earn high-quality backlinks/mentions": {"technical": 0, "content": 2, "aeo": 2, "authority": 16, "biz": 0.03},
        "Clarify positioning and entities": {"technical": 0, "content": 6, "aeo": 11, "authority": 4, "biz": 0.03},
        "Reddit / community listening and answer mining": {"technical": 0, "content": 8, "aeo": 9, "authority": 4, "biz": 0.04},
        "YouTube content repurposing into SEO pages": {"technical": 0, "content": 9, "aeo": 6, "authority": 3, "biz": 0.03},
        "LinkedIn executive thought leadership": {"technical": 0, "content": 4, "aeo": 5, "authority": 8, "biz": 0.04},
        "Email nurturing to SEO content hubs": {"technical": 0, "content": 4, "aeo": 2, "authority": 3, "biz": 0.03},
    }
    bonuses = {"technical": 0, "content": 0, "aeo": 0, "authority": 0, "biz": 0}
    for action in actions:
        for key, value in action_bonus[action].items():
            bonuses[key] += value

    bonuses["content"] += content_effect["content_action_score"] * 0.25
    bonuses["aeo"] += content_effect["snippet_aeo_lift_pct"] * 0.16
    bonuses["authority"] += min(8, email_effect["assisted_organic_lift_pct"] * 0.2)
    bonuses["biz"] += content_effect["content_visibility_lift_pct"] / 1000 + email_effect["assisted_organic_lift_pct"] / 1000

    current = {
        "Technical SEO": clamp(technical),
        "Content Quality": clamp(content),
        "Authority": clamp(authority),
        "AEO/GEO Readiness": clamp(aeo),
    }
    projected = {
        "Technical SEO": clamp(technical + bonuses["technical"]),
        "Content Quality": clamp(content + bonuses["content"]),
        "Authority": clamp(authority + bonuses["authority"]),
        "AEO/GEO Readiness": clamp(aeo + bonuses["aeo"]),
    }
    current_seo = current["Technical SEO"] * 0.34 + current["Content Quality"] * 0.33 + current["Authority"] * 0.33
    projected_seo = projected["Technical SEO"] * 0.34 + projected["Content Quality"] * 0.33 + projected["Authority"] * 0.33
    current_aeo = current["AEO/GEO Readiness"] * 0.55 + current["Content Quality"] * 0.25 + current["Authority"] * 0.20
    projected_aeo = projected["AEO/GEO Readiness"] * 0.55 + projected["Content Quality"] * 0.25 + projected["Authority"] * 0.20
    return current, projected, clamp(current_seo), clamp(projected_seo), clamp(current_aeo), clamp(projected_aeo), bonuses["biz"]


def calculate_business_impact(current_seo, projected_seo, current_aeo, projected_aeo, biz, action_biz_bonus, content_effect, email_effect):
    seo_lift = max(projected_seo - current_seo, 0)
    aeo_lift = max(projected_aeo - current_aeo, 0)
    visibility_lift_pct = ((seo_lift * biz["seo_weight"] + aeo_lift * biz["aeo_weight"]) / 100) + action_biz_bonus
    visibility_lift_pct += content_effect["content_visibility_lift_pct"] / 100
    visibility_lift_pct += email_effect["assisted_organic_lift_pct"] / 100
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

    email_leads = email_effect["incremental_email_clicks"] * (biz["visit_to_lead"] / 100)
    email_opps = email_leads * (biz["lead_to_opp"] / 100)
    email_clients = email_opps * (biz["opp_to_client"] / 100)
    email_revenue = email_clients * biz["avg_deal_value"]

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
        "Email incremental revenue": email_revenue,
    }

# -----------------------------
# Data upload section
# -----------------------------
with st.expander("1. Cargar datos reales opcional", expanded=True):
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        gsc_file = st.file_uploader("Google Search Console CSV", type=["csv"], key="gsc")
    with c2:
        ga4_file = st.file_uploader("GA4 CSV", type=["csv"], key="ga4")
    with c3:
        yt_file = st.file_uploader("YouTube Analytics CSV", type=["csv"], key="yt")
    with c4:
        email_file = st.file_uploader("Email marketing CSV", type=["csv"], key="email")
    st.caption("Email CSV puede venir de Mailchimp, HubSpot, Brevo, ActiveCampaign, etc. El simulador intenta detectar columnas como sent, delivered, opens, clicks y unsubscribes.")


gsc = gsc_metrics(read_uploaded_csv(gsc_file))
ga4 = ga4_metrics(read_uploaded_csv(ga4_file))
yt = yt_metrics(read_uploaded_csv(yt_file))
email = email_metrics(read_uploaded_csv(email_file))

search_demand_score = 35
query_intent_score = 35
offsite_signal = 30
monthly_sessions_default = 500
visit_to_lead_default = 1.5
email_list_default = 5000
email_open_default = 30.0
email_click_default = 1.5

if gsc:
    search_demand_score = clamp(np.log1p(gsc["impressions"]) * 8)
    query_intent_score = clamp((100 - min(gsc["avg_position"] or 50, 50) * 2) * 0.4 + min(gsc["queries"], 100) * 0.6)
if ga4:
    monthly_sessions_default = int(max(ga4["sessions"], 1))
    if ga4["cvr"] > 0:
        visit_to_lead_default = round(float(ga4["cvr"]), 2)
if yt:
    offsite_signal = clamp(np.log1p(yt["views"]) * 8 + np.log1p(yt["watch_time"] + 1) * 3)
if email:
    email_list_default = int(max(email["delivered"], 1))
    email_open_default = float(round(email["open_rate"], 2))
    email_click_default = float(round(email["click_rate"], 2))

data_signal = {"search_demand_score": search_demand_score, "query_intent_score": query_intent_score, "offsite_signal": offsite_signal}

if any([gsc, ga4, yt, email]):
    st.subheader("Resumen de datos cargados")
    cards = st.columns(8)
    if gsc:
        cards[0].metric("GSC clicks", f"{gsc['clicks']:,.0f}")
        cards[1].metric("GSC impressions", f"{gsc['impressions']:,.0f}")
        cards[2].metric("Avg position", f"{gsc['avg_position']:.1f}")
    if ga4:
        cards[3].metric("GA4 sessions", f"{ga4['sessions']:,.0f}")
        cards[4].metric("GA4 CVR", f"{ga4['cvr']:.2f}%")
    if yt:
        cards[5].metric("YT views", f"{yt['views']:,.0f}")
    if email:
        cards[6].metric("Email open rate", f"{email['open_rate']:.1f}%")
        cards[7].metric("Email click rate", f"{email['click_rate']:.1f}%")

# -----------------------------
# Sidebar inputs
# -----------------------------
st.sidebar.header("Website inputs")
st.sidebar.caption("Puedes cargar datos reales o ajustar manualmente de 0 a 100.")
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
    "monthly_sessions": st.sidebar.number_input("Current monthly organic sessions", 0, 1000000, monthly_sessions_default),
    "visit_to_lead": st.sidebar.number_input("Visit to lead conversion %", 0.0, 100.0, float(visit_to_lead_default), step=0.1),
    "lead_to_opp": st.sidebar.number_input("Lead to opportunity conversion %", 0.0, 100.0, 25.0, step=1.0),
    "opp_to_client": st.sidebar.number_input("Opportunity to client conversion %", 0.0, 100.0, 20.0, step=1.0),
    "avg_deal_value": st.sidebar.number_input("Average deal value / client", 0, 10000000, 15000, step=500),
    "execution_confidence": st.sidebar.slider("Execution confidence", 0, 100, 65),
    "seo_weight": st.sidebar.slider("SEO impact weight", 0.0, 3.0, 1.0, step=0.1),
    "aeo_weight": st.sidebar.slider("AEO/GEO impact weight", 0.0, 3.0, 0.8, step=0.1),
}

# -----------------------------
# Content and email scenarios
# -----------------------------
st.subheader("2. Simular cambios de contenido y email")
content_tab, email_tab = st.tabs(["Contenido y ranking", "Email y nurturing"])

with content_tab:
    cc1, cc2, cc3, cc4 = st.columns(4)
    content_inputs = {
        "pages_refreshed": cc1.number_input("Páginas existentes a actualizar", 0, 500, 5),
        "new_pages": cc2.number_input("Nuevas páginas/artículos", 0, 500, 3),
        "faq_blocks": cc3.number_input("Bloques FAQ/direct answers", 0, 500, 8),
        "case_studies_added": cc4.number_input("Casos/testimonios nuevos", 0, 200, 2),
        "internal_links_added": cc1.number_input("Links internos agregados", 0, 5000, 30),
        "title_meta_improvement": cc2.slider("Mejora de titles/metas", 0, 100, 35),
        "content_quality_delta": cc3.slider("Mejora de calidad del contenido", 0, 100, 35),
        "topical_coverage_delta": cc4.slider("Mejora de cobertura temática", 0, 100, 30),
        "eeat_proof_delta": cc1.slider("Mejora de pruebas/E-E-A-T", 0, 100, 30),
        "structured_answer_delta": cc2.slider("Mejora de respuestas estructuradas", 0, 100, 35),
        "implementation_quality": cc3.slider("Calidad de implementación", 0, 100, 70),
    }

with email_tab:
    ec1, ec2, ec3, ec4 = st.columns(4)
    email_inputs = {
        "list_size": ec1.number_input("Tamaño de lista", 0, 10000000, email_list_default),
        "campaigns_per_month": ec2.number_input("Campañas por mes", 0, 100, 2),
        "open_rate": ec3.number_input("Open rate actual %", 0.0, 100.0, email_open_default, step=0.1),
        "click_rate": ec4.number_input("Click rate actual %", 0.0, 100.0, email_click_default, step=0.1),
        "subject_line_lift": ec1.slider("Mejora por asuntos/preheaders", 0.0, 20.0, 3.0, step=0.5),
        "cta_lift": ec2.slider("Mejora por CTAs/oferta", 0.0, 10.0, 1.0, step=0.1),
        "segmentation_lift": ec3.slider("Mejora por segmentación", 0.0, 20.0, 4.0, step=0.5),
        "content_relevance_lift": ec4.slider("Mejora por relevancia del contenido", 0.0, 20.0, 4.0, step=0.5),
        "newsletter_to_content": ec1.slider("Uso de email para empujar hubs SEO", 0, 100, 40),
    }

content_effect = calculate_content_effect(content_inputs)
email_effect = calculate_email_effect(email_inputs, email)

mc1, mc2, mc3, mc4 = st.columns(4)
mc1.metric("Ranking gain estimado", f"+{content_effect['estimated_position_gain']:.1f} posiciones")
mc2.metric("CTR lift estimado", f"+{content_effect['ctr_lift_pct']:.1f}%")
mc3.metric("Email clicks incrementales", f"{email_effect['incremental_email_clicks']:,.0f}")
mc4.metric("Lift asistido email", f"+{email_effect['assisted_organic_lift_pct']:.1f}%")

# -----------------------------
# Actions
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
    "Reddit / community listening and answer mining",
    "YouTube content repurposing into SEO pages",
    "LinkedIn executive thought leadership",
    "Email nurturing to SEO content hubs",
]
selected_actions = st.multiselect(
    "3. Selecciona las acciones estratégicas que quieres simular",
    actions_list,
    default=[
        "Fix duplicated titles and meta descriptions",
        "Add schema markup",
        "Add FAQs and direct answers",
        "Create or improve pillar pages",
        "Email nurturing to SEO content hubs",
    ],
)

current, projected, current_seo, projected_seo, current_aeo, projected_aeo, action_biz_bonus = calculate_scores(inputs, selected_actions, data_signal, content_effect, email_effect)
impact = calculate_business_impact(current_seo, projected_seo, current_aeo, projected_aeo, biz, action_biz_bonus, content_effect, email_effect)

# -----------------------------
# Results dashboard
# -----------------------------
st.subheader("4. Resultado proyectado")
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("SEO score", f"{projected_seo:.0f}/100", f"+{projected_seo - current_seo:.0f}")
col2.metric("AEO/GEO score", f"{projected_aeo:.0f}/100", f"+{projected_aeo - current_aeo:.0f}")
col3.metric("Visibility lift", f"{impact['Visibility lift %']:.1f}%")
col4.metric("Incremental monthly revenue", f"${impact['Incremental revenue']:,.0f}")
col5.metric("Email assisted revenue", f"${impact['Email incremental revenue']:,.0f}")

left, right = st.columns(2)
with left:
    score_df = pd.DataFrame({"Area": list(current.keys()), "Current": list(current.values()), "Projected": list(projected.values())})
    st.write("Current vs projected scores")
    st.dataframe(score_df, use_container_width=True, hide_index=True)
    st.bar_chart(score_df.set_index("Area"))

with right:
    business_df = pd.DataFrame({
        "Metric": ["Sessions", "Leads", "Opportunities", "Clients", "Revenue"],
        "Current": [
            biz["monthly_sessions"],
            biz["monthly_sessions"] * biz["visit_to_lead"] / 100,
            biz["monthly_sessions"] * biz["visit_to_lead"] / 100 * biz["lead_to_opp"] / 100,
            biz["monthly_sessions"] * biz["visit_to_lead"] / 100 * biz["lead_to_opp"] / 100 * biz["opp_to_client"] / 100,
            impact["Current revenue"],
        ],
        "Projected": [impact["Monthly sessions"], impact["Monthly leads"], impact["Monthly opportunities"], impact["Monthly clients"], impact["Monthly revenue"]],
    })
    st.write("Business impact")
    st.dataframe(business_df, use_container_width=True, hide_index=True)
    st.bar_chart(business_df.set_index("Metric")[["Current", "Projected"]])

rank_df = pd.DataFrame({
    "Scenario": ["Base", "After content changes"],
    "Avg position estimate": [gsc["avg_position"] if gsc else 20, max(1, (gsc["avg_position"] if gsc else 20) - content_effect["estimated_position_gain"])],
    "CTR estimate %": [gsc["ctr"] if gsc else 1.5, (gsc["ctr"] if gsc else 1.5) * (1 + content_effect["ctr_lift_pct"] / 100)],
})
st.write("Ranking and CTR projection")
st.dataframe(rank_df, use_container_width=True, hide_index=True)

email_df = pd.DataFrame({
    "Metric": ["Open rate", "Click rate", "Monthly email clicks"],
    "Current": [email_effect["current_open_rate"], email_effect["current_click_rate"], email_effect["current_email_clicks"]],
    "Projected": [email_effect["projected_open_rate"], email_effect["projected_click_rate"], email_effect["projected_email_clicks"]],
})
st.write("Email projection")
st.dataframe(email_df, use_container_width=True, hide_index=True)

# -----------------------------
# Recommendations
# -----------------------------
st.subheader("5. Recomendaciones automáticas")
recommendations = []
if gsc and not gsc["opportunities"].empty:
    recommendations.append("Prioriza queries con muchas impresiones y posición 4 a 20. Son las más cercanas a convertirse en tráfico incremental con updates de contenido.")
if content_effect["estimated_position_gain"] >= 3:
    recommendations.append("El plan de contenido tiene potencial de mover rankings. Enfócate en refresh de páginas existentes, FAQs y links internos antes de crear demasiadas páginas nuevas.")
if email_effect["incremental_email_clicks"] > 50:
    recommendations.append("Email puede funcionar como acelerador de distribución: manda tráfico inicial a hubs, casos y páginas pilar para mejorar engagement y señales de demanda.")
if projected_aeo - current_aeo >= projected_seo - current_seo:
    recommendations.append("El mayor upside está en AEO/GEO: FAQs, direct answers, schema, entidades claras y contenido con pruebas concretas.")
if "Reddit / community listening and answer mining" in selected_actions:
    recommendations.append("Usa Reddit y comunidades como fuente de preguntas reales. Convierte patrones en FAQs, comparativas, páginas de problemas y respuestas cortas para AI search.")
if "Email nurturing to SEO content hubs" in selected_actions:
    recommendations.append("Crea secuencias por tema: problema, caso, guía, checklist y CTA. Cada email debe empujar una URL estratégica, no solo informar.")
if impact["Incremental revenue"] < 500:
    recommendations.append("El impacto de negocio parece bajo. Revisa tráfico mensual, conversion rate o deal value para validar si los supuestos son realistas.")

for r in recommendations or ["Carga CSVs de GSC, GA4 o email para generar recomendaciones más específicas."]:
    st.info(r)

if gsc and not gsc["opportunities"].empty:
    st.write("Top oportunidades desde Google Search Console")
    st.dataframe(gsc["opportunities"], use_container_width=True, hide_index=True)
if ga4 and not ga4["top"].empty:
    st.write("Top datos desde GA4")
    st.dataframe(ga4["top"], use_container_width=True, hide_index=True)
if yt and not yt["top"].empty:
    st.write("Top videos / contenidos desde YouTube")
    st.dataframe(yt["top"], use_container_width=True, hide_index=True)
if email and not email["top"].empty:
    st.write("Top campañas de email")
    st.dataframe(email["top"], use_container_width=True, hide_index=True)

# -----------------------------
# Export
# -----------------------------
st.subheader("6. Exportar reporte")
content_df = pd.DataFrame([content_effect]).assign(section="Content Projection")
email_export_df = pd.DataFrame([email_effect]).assign(section="Email Projection")
report = pd.concat([
    score_df.assign(section="Scores"),
    business_df.assign(section="Business"),
    rank_df.assign(section="Ranking"),
    email_df.assign(section="Email"),
    content_df,
    email_export_df,
], ignore_index=True, sort=False)

csv = report.to_csv(index=False).encode("utf-8")
st.download_button("Download CSV report", data=csv, file_name=f"seo_aeo_business_report_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv")

st.caption("Nota: este simulador usa heurísticas para priorización y escenarios. No reemplaza GSC, GA4, Ahrefs/Semrush ni modelos estadísticos avanzados, pero ayuda a explicar impacto potencial sin consumir tokens de AI.")

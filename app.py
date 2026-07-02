import io
import math
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Trust & Visibility Intelligence Platform", layout="wide")

APP_VERSION = "v8.0 - Dynamic recommendation engine"

# -----------------------------
# Helpers
# -----------------------------

def clamp(x, low=0, high=100):
    try:
        return max(low, min(high, float(x)))
    except Exception:
        return 0


def score_from_count(value, good, excellent):
    value = max(0, float(value or 0))
    if value <= good:
        return clamp((value / good) * 60 if good else 0)
    return clamp(60 + ((value - good) / max(excellent - good, 1)) * 40)


def safe_read_csv(uploaded_file):
    if uploaded_file is None:
        return None, "No file"
    raw = uploaded_file.getvalue()
    # Try common encodings and separators.
    attempts = []
    for enc in ["utf-8", "utf-8-sig", "latin-1"]:
        for sep in [",", ";", "\t"]:
            attempts.append((enc, sep))
    for enc, sep in attempts:
        try:
            df = pd.read_csv(io.BytesIO(raw), encoding=enc, sep=sep, engine="python", on_bad_lines="skip")
            if df.shape[1] > 1 and len(df) > 0:
                df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
                return df, None
        except Exception:
            pass
    # Fallback: parse numeric values from text-like CSVs
    try:
        text = raw.decode("utf-8", errors="ignore")
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        rows = [l.split(",") for l in lines]
        df = pd.DataFrame(rows)
        return df, "Irregular CSV read as raw table"
    except Exception as e:
        return None, str(e)


def find_numeric_sum(df, possible_names):
    if df is None or df.empty:
        return 0
    cols = list(df.columns)
    for name in possible_names:
        for c in cols:
            if name in str(c).lower():
                s = pd.to_numeric(df[c].astype(str).str.replace(r"[^0-9.\-]", "", regex=True), errors="coerce")
                if s.notna().sum() > 0:
                    return float(s.fillna(0).sum())
    return 0


def find_numeric_mean(df, possible_names):
    if df is None or df.empty:
        return 0
    for name in possible_names:
        for c in df.columns:
            if name in str(c).lower():
                s = pd.to_numeric(df[c].astype(str).str.replace("%", "", regex=False).str.replace(r"[^0-9.\-]", "", regex=True), errors="coerce")
                if s.notna().sum() > 0:
                    return float(s.dropna().mean())
    return 0


def read_ga4_metrics(df):
    if df is None:
        return {"sessions": 0, "conversions": 0, "engagement_rate": 0}
    sessions = find_numeric_sum(df, ["sessions", "session", "usuarios", "users", "active_users"])
    conversions = find_numeric_sum(df, ["conversions", "key_events", "conversiones", "events"])
    engagement = find_numeric_mean(df, ["engagement_rate", "engagement", "participacion"])
    if engagement > 1 and engagement <= 100:
        engagement = engagement
    elif engagement <= 1:
        engagement = engagement * 100
    return {"sessions": sessions, "conversions": conversions, "engagement_rate": engagement}


def read_gsc_metrics(df):
    if df is None:
        return {"clicks": 0, "impressions": 0, "ctr": 0, "position": 0, "queries": 0}
    clicks = find_numeric_sum(df, ["clicks", "clics"])
    impressions = find_numeric_sum(df, ["impressions", "impresiones"])
    ctr = find_numeric_mean(df, ["ctr"])
    position = find_numeric_mean(df, ["position", "posicion", "posición"])
    queries = len(df) if len(df) else 0
    if ctr <= 1:
        ctr = ctr * 100
    return {"clicks": clicks, "impressions": impressions, "ctr": ctr, "position": position, "queries": queries}


def read_linkedin_metrics(df):
    if df is None:
        return {"impressions": 0, "clicks": 0, "engagement": 0, "followers": 0, "posts": 0}
    impressions = find_numeric_sum(df, ["impressions", "impresiones", "views"])
    clicks = find_numeric_sum(df, ["clicks", "clics"])
    engagement = find_numeric_mean(df, ["engagement", "engagement_rate", "rate"])
    followers = find_numeric_sum(df, ["followers", "seguidores"])
    posts = len(df) if len(df) else 0
    if engagement <= 1:
        engagement = engagement * 100
    return {"impressions": impressions, "clicks": clicks, "engagement": engagement, "followers": followers, "posts": posts}


def read_email_metrics(df):
    if df is None:
        return {"sent": 0, "opens": 0, "clicks": 0, "open_rate": 0, "click_rate": 0}
    sent = find_numeric_sum(df, ["sent", "recipients", "delivered", "enviados"])
    opens = find_numeric_sum(df, ["opens", "opened", "aperturas"])
    clicks = find_numeric_sum(df, ["clicks", "clics"])
    open_rate = find_numeric_mean(df, ["open_rate", "open rate", "apertura"])
    click_rate = find_numeric_mean(df, ["click_rate", "click rate", "ctr"])
    if open_rate <= 1:
        open_rate *= 100
    if click_rate <= 1:
        click_rate *= 100
    if open_rate == 0 and sent > 0:
        open_rate = opens / sent * 100
    if click_rate == 0 and sent > 0:
        click_rate = clicks / sent * 100
    return {"sent": sent, "opens": opens, "clicks": clicks, "open_rate": open_rate, "click_rate": click_rate}


@dataclass
class Recommendation:
    area: str
    title: str
    why: str
    action: str
    impact: str
    effort: str
    timing: str
    metrics: str
    priority: float
    confidence: str


def build_scores(inputs, data):
    authority = (
        score_from_count(inputs["dr"], 40, 70) * 0.35 +
        score_from_count(inputs["ref_domains"], 150, 500) * 0.25 +
        score_from_count(inputs["backlinks"], 800, 3000) * 0.10 +
        score_from_count(inputs["brand_mentions"], 20, 80) * 0.15 +
        score_from_count(inputs["media_mentions"], 8, 30) * 0.15
    )
    content = (
        score_from_count(inputs["service_pages"], 8, 20) * 0.25 +
        score_from_count(inputs["blog_articles"], 30, 120) * 0.25 +
        score_from_count(inputs["case_studies"], 5, 20) * 0.20 +
        score_from_count(inputs["faqs"], 30, 100) * 0.15 +
        score_from_count(inputs["videos"], 10, 50) * 0.15
    )
    eeat = (
        (100 if inputs["founders_visible"] else 25) * 0.20 +
        (100 if inputs["author_bios"] else 30) * 0.20 +
        (100 if inputs["testimonials"] else 25) * 0.20 +
        score_from_count(inputs["case_studies"], 5, 20) * 0.20 +
        (100 if inputs["about_page"] else 30) * 0.20
    )
    aeo = (
        (100 if inputs["faq_schema"] else 25) * 0.25 +
        (100 if inputs["org_schema"] else 40) * 0.20 +
        (100 if inputs["article_schema"] else 35) * 0.15 +
        score_from_count(inputs["faqs"], 25, 100) * 0.25 +
        (100 if inputs["direct_answers"] else 35) * 0.15
    )
    li = data.get("linkedin", {})
    social = (
        score_from_count(inputs["linkedin_followers"] or li.get("followers", 0), 3000, 20000) * 0.30 +
        score_from_count(inputs["weekly_posts"], 3, 7) * 0.25 +
        score_from_count(li.get("impressions", 0), 10000, 100000) * 0.25 +
        score_from_count(li.get("engagement", inputs["social_engagement"]), 2.5, 7) * 0.20
    )
    email_data = data.get("email", {})
    email = (
        score_from_count(inputs["email_list"], 5000, 50000) * 0.25 +
        score_from_count(email_data.get("open_rate", inputs["open_rate"]), 25, 45) * 0.25 +
        score_from_count(email_data.get("click_rate", inputs["click_rate"]), 2, 6) * 0.30 +
        score_from_count(inputs["email_campaigns_month"], 2, 6) * 0.20
    )
    technical = inputs["technical_seo"]
    trust = eeat * 0.25 + authority * 0.20 + content * 0.20 + aeo * 0.15 + social * 0.10 + email * 0.05 + technical * 0.05
    visibility = authority * 0.20 + content * 0.20 + aeo * 0.20 + social * 0.20 + email * 0.10 + technical * 0.10
    return {k: round(clamp(v), 1) for k, v in {
        "Trust": trust, "Visibility": visibility, "Authority": authority, "Content": content,
        "EEAT": eeat, "AEO/GEO": aeo, "Social": social, "Email": email, "Technical SEO": technical
    }.items()}


def diagnose(scores, data, inputs):
    weak = sorted(scores.items(), key=lambda x: x[1])[:3]
    strongest = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:2]
    gsc = data.get("gsc", {})
    ga4 = data.get("ga4", {})
    conditions = []
    if scores["Authority"] < 45:
        conditions.append("authority_low")
    if scores["Content"] < 50:
        conditions.append("content_low")
    if scores["Social"] < 40:
        conditions.append("social_low")
    if scores["Email"] < 45:
        conditions.append("email_low")
    if scores["AEO/GEO"] < 55:
        conditions.append("aeo_low")
    if gsc.get("impressions", 0) > 1000 and gsc.get("ctr", 0) < 2.5:
        conditions.append("gsc_low_ctr")
    if gsc.get("position", 0) > 8:
        conditions.append("gsc_low_positions")
    if ga4.get("sessions", 0) > 0 and ga4.get("conversions", 0) / max(ga4.get("sessions", 1), 1) < 0.01:
        conditions.append("low_cvr")
    return weak, strongest, conditions


def confidence_label(files_loaded):
    if files_loaded >= 4:
        return "Alta: basada en varias fuentes reales cargadas."
    if files_loaded >= 2:
        return "Media: combina datos reales con inputs manuales."
    return "Baja-media: principalmente basada en inputs manuales."


def recommendations(scores, data, inputs, conditions, files_loaded) -> List[Recommendation]:
    conf = "Alta" if files_loaded >= 3 else "Media" if files_loaded >= 1 else "Baja-media"
    recs = []
    def add(area, title, why, action, impact, effort, timing, metrics, priority, confidence=conf):
        recs.append(Recommendation(area, title, why, action, impact, effort, timing, metrics, priority, confidence))

    if "authority_low" in conditions:
        add("Authority", "Conseguir señales externas de confianza", "La autoridad está limitando la capacidad del sitio para competir y ser citado por buscadores e IA.", "Identifica 10 partners, asociaciones, podcasts o medios nicho y prepara 3 pitches para conseguir menciones o enlaces.", "Alto", "Medio", "2 a 8 semanas", "Authority, Trust, Visibility", 95)
    if "content_low" in conditions:
        add("Content", "Actualizar páginas comerciales antes de crear demasiado contenido nuevo", "El contenido actual no está dando suficientes señales de profundidad, cobertura temática o conversión.", "Actualiza 3 a 5 páginas de servicios con mejores H1/H2, FAQs, casos, CTA y respuestas directas.", "Muy alto", "Medio", "1 a 4 semanas", "Content, SEO, Trust, Leads", 92)
    if "aeo_low" in conditions:
        add("AEO/GEO", "Agregar FAQs y respuestas directas para AI Search", "Los motores de IA favorecen contenido que responde preguntas claras y estructuradas.", "Agrega 5 preguntas frecuentes y una sección de direct answers en cada página prioritaria.", "Alto", "Bajo", "1 a 3 semanas", "AEO/GEO, AI Readiness, Visibility", 90)
    if "social_low" in conditions:
        add("Social", "Activar LinkedIn como canal de autoridad", "La presencia social baja reduce señales de marca, búsquedas de marca y tráfico referido.", "Publica 3 posts esta semana: 1 insight, 1 caso/aprendizaje, 1 post educativo conectado a una página del sitio.", "Alto", "Bajo", "1 a 4 semanas", "Social, Trust, Brand Searches", 88)
    if "email_low" in conditions:
        add("Email", "Usar email para alimentar el flywheel de visibilidad", "El email no mejora SEO directamente, pero puede llevar tráfico recurrente y mejorar engagement del contenido.", "Envía una newsletter breve con 1 idea, 1 link a contenido clave y 1 CTA a reunión o recurso.", "Medio", "Bajo", "Inmediato a 2 semanas", "Email, Engagement, Leads", 82)
    if "gsc_low_ctr" in conditions:
        add("SEO", "Reescribir titles y metas con más intención comercial", "Hay impresiones, pero pocos clics. El problema puede estar en el mensaje del resultado de búsqueda.", "Filtra las páginas con más impresiones y bajo CTR. Reescribe 10 titles/metas con beneficio claro y palabra clave principal.", "Muy alto", "Bajo", "1 a 3 semanas", "CTR, Clicks, Organic Traffic", 94, "Alta")
    if "gsc_low_positions" in conditions:
        add("SEO", "Empujar keywords cercanas al top 10", "Las posiciones medias indican que Google ya entiende el tema, pero falta profundidad o autoridad interna.", "Actualiza las URLs en posiciones 8 a 20 con secciones nuevas, enlaces internos y FAQs.", "Muy alto", "Medio", "2 a 8 semanas", "Rankings, Clicks, Visibility", 93, "Alta")
    if "low_cvr" in conditions:
        add("Business", "Mejorar conversión de páginas con tráfico", "El tráfico por sí solo no genera negocio si las páginas no convierten.", "Agrega CTA visibles, prueba de confianza y formularios más simples en las landing pages principales.", "Alto", "Bajo", "1 a 2 semanas", "CVR, Leads, Revenue", 89, "Alta")

    # Always include integrated flywheel recommendation if not enough recs
    add("Integrated", "Crear una campaña de 7 días conectando website, LinkedIn y email", "Las acciones aisladas suelen generar impacto limitado. La combinación aumenta alcance, tráfico y señales de confianza.", "Publica 1 pieza de contenido, distribúyela en LinkedIn y envíala por email con CTA a una página de servicio.", "Alto", "Medio", "7 días", "Visibility, Trust, Leads", 75)

    # Sort and return top 8
    return sorted(recs, key=lambda r: r.priority, reverse=True)[:8]


def scenario_impact(base_scores, actions, inputs):
    articles = actions["articles"]
    service_updates = actions["service_updates"]
    linkedin_posts = actions["linkedin_posts"]
    emails = actions["emails"]
    faqs = actions["faqs"]
    cases = actions["cases"]
    ref_domains = actions["ref_domains"]

    deltas = {
        "Content": articles * 1.4 + service_updates * 2.2 + cases * 1.8 + faqs * 0.6,
        "AEO/GEO": faqs * 1.5 + articles * 0.8 + service_updates * 0.9,
        "Social": linkedin_posts * 2.5,
        "Email": emails * 2.3,
        "Authority": ref_domains * 0.8 + cases * 0.4,
        "Trust": service_updates * 1.0 + cases * 1.8 + ref_domains * 0.5 + faqs * 0.4 + linkedin_posts * 0.4,
        "Visibility": articles * 1.2 + service_updates * 1.1 + linkedin_posts * 0.9 + emails * 0.5 + faqs * 0.8 + ref_domains * 0.7,
    }
    projected = dict(base_scores)
    for k, v in deltas.items():
        if k in projected:
            projected[k] = round(clamp(projected[k] + v), 1)
    monthly_sessions = max(inputs["manual_sessions"], 1)
    visitor_to_lead = inputs["visitor_to_lead"] / 100
    lead_to_client = inputs["lead_to_client"] / 100
    avg_contract = inputs["avg_contract"]
    visibility_lift = max(0, projected["Visibility"] - base_scores["Visibility"]) / 100
    trust_lift = max(0, projected["Trust"] - base_scores["Trust"]) / 100
    incremental_sessions = round(monthly_sessions * (visibility_lift * 0.9 + trust_lift * 0.25))
    leads = incremental_sessions * visitor_to_lead
    clients = leads * lead_to_client
    revenue = clients * avg_contract
    return projected, deltas, incremental_sessions, leads, clients, revenue


# -----------------------------
# Sidebar inputs
# -----------------------------

st.sidebar.title("Inputs del negocio")
st.sidebar.caption("Usa datos reales si los tienes. Si no, ingresa estimados manuales.")
website = st.sidebar.text_input("Website", "https://www.scalto.com")

st.sidebar.header("Autoridad manual")
dr = st.sidebar.number_input("Domain Rating / Authority externa", 0, 100, 22)
ref_domains = st.sidebar.number_input("Referring domains", 0, 100000, 127)
backlinks = st.sidebar.number_input("Backlinks", 0, 1000000, 549)
organic_keywords = st.sidebar.number_input("Organic keywords", 0, 1000000, 4)
brand_mentions = st.sidebar.number_input("Brand mentions estimadas", 0, 100000, 5)
media_mentions = st.sidebar.number_input("Apariciones en medios", 0, 10000, 1)

st.sidebar.header("Contenido y confianza")
service_pages = st.sidebar.number_input("Service pages", 0, 500, 6)
blog_articles = st.sidebar.number_input("Blog/articles", 0, 5000, 25)
case_studies = st.sidebar.number_input("Case studies", 0, 500, 3)
videos = st.sidebar.number_input("Videos", 0, 1000, 5)
faqs = st.sidebar.number_input("FAQs existentes", 0, 1000, 15)
technical_seo = st.sidebar.slider("Technical SEO health", 0, 100, 57)

founders_visible = st.sidebar.checkbox("Fundadores visibles", True)
author_bios = st.sidebar.checkbox("Autores con bio", False)
testimonials = st.sidebar.checkbox("Testimonios / logos", True)
about_page = st.sidebar.checkbox("Página About clara", True)

st.sidebar.header("AEO/GEO")
faq_schema = st.sidebar.checkbox("FAQ Schema", False)
org_schema = st.sidebar.checkbox("Organization Schema", True)
article_schema = st.sidebar.checkbox("Article Schema", False)
direct_answers = st.sidebar.checkbox("Direct answers en páginas clave", False)

st.sidebar.header("Social / Email")
linkedin_followers = st.sidebar.number_input("LinkedIn followers", 0, 10000000, 0)
weekly_posts = st.sidebar.number_input("Posts por semana", 0, 50, 0)
social_engagement = st.sidebar.number_input("Engagement social estimado %", 0.0, 100.0, 0.0)
email_list = st.sidebar.number_input("Email list size", 0, 10000000, 0)
email_campaigns_month = st.sidebar.number_input("Campañas email / mes", 0, 50, 0)
open_rate = st.sidebar.number_input("Open rate %", 0.0, 100.0, 0.0)
click_rate = st.sidebar.number_input("Click rate %", 0.0, 100.0, 0.0)

st.sidebar.header("Negocio")
manual_sessions = st.sidebar.number_input("Sesiones mensuales estimadas", 0, 10000000, 1000)
visitor_to_lead = st.sidebar.number_input("Visitante a lead %", 0.0, 100.0, 1.0)
lead_to_client = st.sidebar.number_input("Lead a cliente %", 0.0, 100.0, 10.0)
avg_contract = st.sidebar.number_input("Valor promedio contrato USD", 0, 10000000, 15000)

inputs = locals().copy()

# -----------------------------
# Main app
# -----------------------------

st.title("Trust & Visibility Intelligence Platform")
st.caption(APP_VERSION)
st.write("La herramienta cambia sus recomendaciones según los datos cargados y los inputs manuales. No promete resultados exactos: prioriza acciones con mayor probabilidad de impacto.")

with st.expander("1. Cargar datos reales opcional", expanded=True):
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        gsc_file = st.file_uploader("Google Search Console CSV", type=["csv"], key="gsc")
    with c2:
        ga4_file = st.file_uploader("GA4 CSV", type=["csv"], key="ga4")
    with c3:
        linkedin_file = st.file_uploader("LinkedIn CSV", type=["csv"], key="li")
    with c4:
        social_file = st.file_uploader("Social Media CSV", type=["csv"], key="social")
    with c5:
        email_file = st.file_uploader("Email Marketing CSV", type=["csv"], key="email")
    st.info("No necesitas cargar todo. Si una plataforma no tiene data, el motor usa inputs manuales y baja el nivel de confianza.")

files = {"gsc": gsc_file, "ga4": ga4_file, "linkedin": linkedin_file, "social": social_file, "email": email_file}
loaded_dfs = {}
file_warnings = []
for name, f in files.items():
    df, err = safe_read_csv(f) if f is not None else (None, None)
    loaded_dfs[name] = df
    if f is not None and err:
        file_warnings.append(f"{name.upper()}: {err}")

if file_warnings:
    st.warning("Algunos archivos tienen formato irregular. El simulador intentó leerlos, pero puede usar inputs manuales. " + " | ".join(file_warnings))

data = {
    "ga4": read_ga4_metrics(loaded_dfs["ga4"]),
    "gsc": read_gsc_metrics(loaded_dfs["gsc"]),
    "linkedin": read_linkedin_metrics(loaded_dfs["linkedin"]),
    "email": read_email_metrics(loaded_dfs["email"]),
}
files_loaded = sum(1 for f in files.values() if f is not None)

scores = build_scores(inputs, data)
weak, strongest, conditions = diagnose(scores, data, inputs)
recs = recommendations(scores, data, inputs, conditions, files_loaded)
conf_text = confidence_label(files_loaded)

st.header("1. Executive Brief")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Trust Score", f"{scores['Trust']:.0f}/100")
m2.metric("Visibility Score", f"{scores['Visibility']:.0f}/100")
m3.metric("AI Search Readiness", f"{scores['AEO/GEO']:.0f}/100")
m4.metric("Authority Score", f"{scores['Authority']:.0f}/100", f"DR input: {dr}")

main_limitation = weak[0]
main_strength = strongest[0]
st.subheader("¿Qué significa esto?")
level = "bajo" if scores["Trust"] < 50 else "medio" if scores["Trust"] < 75 else "alto"
vis_level = "baja" if scores["Visibility"] < 50 else "media" if scores["Visibility"] < 75 else "alta"
st.write(f"Tu Trust Score está en nivel **{level}** y tu visibilidad está en nivel **{vis_level}**. La señal más fuerte ahora es **{main_strength[0]} ({main_strength[1]:.0f}/100)**. La principal limitación es **{main_limitation[0]} ({main_limitation[1]:.0f}/100)**.")
if main_limitation[0] == "Authority":
    st.write("Esto sugiere que el contenido puede existir, pero todavía faltan señales externas: menciones, enlaces, partnerships, PR o presencia de terceros que validen la marca.")
elif main_limitation[0] == "Content":
    st.write("Esto sugiere que la web necesita más profundidad comercial y temática: páginas de servicios, artículos, FAQs, casos y recursos que respondan preguntas reales del comprador.")
elif main_limitation[0] == "Social":
    st.write("Esto sugiere que la marca no está generando suficientes señales sociales o de presencia ejecutiva. LinkedIn puede ayudar a crear búsquedas de marca, tráfico referido y confianza.")
elif main_limitation[0] == "Email":
    st.write("Esto sugiere que la base de contactos no está alimentando suficientemente el tráfico y el engagement del contenido.")
elif main_limitation[0] == "AEO/GEO":
    st.write("Esto sugiere que el contenido todavía no está bien preparado para respuestas de IA: faltan preguntas, respuestas directas, schema o estructura clara.")
else:
    st.write("Esto sugiere que hay una oportunidad técnica o estructural que puede estar frenando la visibilidad.")
st.caption(f"Nivel de confianza del diagnóstico: {conf_text}")

with st.expander("Ver cómo se calculan los scores", expanded=False):
    st.write("**Trust Score** combina EEAT, Authority, Content, AEO/GEO, Social, Email y Technical SEO.")
    st.write("**Authority Score** no es lo mismo que Domain Rating. Usa DR, referring domains, backlinks, menciones de marca y apariciones en medios.")
    st.write("**Visibility Score** estima qué tan fuerte es la presencia combinada en Google, AI Search, social, email y autoridad externa.")
    breakdown = pd.DataFrame({"Score": scores}).reset_index().rename(columns={"index": "Area"})
    st.dataframe(breakdown, use_container_width=True, hide_index=True)

st.subheader("Score breakdown")
chart_df = pd.DataFrame({"Area": list(scores.keys()), "Score": list(scores.values())})
fig = px.bar(chart_df, x="Area", y="Score", text="Score", range_y=[0, 100])
st.plotly_chart(fig, use_container_width=True)

st.header("2. Qué pasa si hago esta acción")
c1, c2, c3 = st.columns(3)
with c1:
    articles = st.slider("Artículos nuevos", 0, 20, 2)
    service_updates = st.slider("Páginas de servicio actualizadas", 0, 20, 3)
with c2:
    linkedin_posts_action = st.slider("Posts de LinkedIn esta semana", 0, 10, 3)
    emails_action = st.slider("Newsletters este mes", 0, 6, 1)
with c3:
    faqs_action = st.slider("Bloques FAQ / direct answers", 0, 50, 10)
    cases_action = st.slider("Casos de estudio nuevos", 0, 10, 1)
    ref_domains_action = st.slider("Nuevos referring domains", 0, 50, 5)

actions = {"articles": articles, "service_updates": service_updates, "linkedin_posts": linkedin_posts_action, "emails": emails_action, "faqs": faqs_action, "cases": cases_action, "ref_domains": ref_domains_action}
projected, deltas, inc_sessions, leads, clients, revenue = scenario_impact(scores, actions, inputs)

p1, p2, p3, p4 = st.columns(4)
p1.metric("Trust proyectado", f"{projected['Trust']:.0f}/100", f"+{projected['Trust']-scores['Trust']:.1f}")
p2.metric("Visibility proyectado", f"{projected['Visibility']:.0f}/100", f"+{projected['Visibility']-scores['Visibility']:.1f}")
p3.metric("Sesiones incrementales", f"+{inc_sessions:,.0f}")
p4.metric("Revenue estimado", f"${revenue:,.0f}")

st.markdown("### Efecto en cadena")
if articles + service_updates + faqs_action > linkedin_posts_action + emails_action:
    st.write("Más contenido y FAQs → mayor cobertura temática → más keywords y respuestas directas → mayor probabilidad de aparecer en Google y AI Search → más visitas → más oportunidades.")
elif linkedin_posts_action > 0:
    st.write("Más LinkedIn → mayor alcance y presencia ejecutiva → más visitas al perfil y al sitio → más búsquedas de marca → más confianza → mejor conversión.")
elif emails_action > 0:
    st.write("Más email → tráfico recurrente hacia contenido clave → mayor engagement → más leads de una audiencia que ya conoce la marca.")
else:
    st.write("Selecciona acciones para ver cómo se conectan con visibilidad, confianza y negocio.")

st.header("3. Motor de recomendaciones dinámicas")
st.write("Estas recomendaciones cambian según los datos cargados, los inputs manuales y los scores más débiles.")
for i, r in enumerate(recs, start=1):
    with st.container(border=True):
        cols = st.columns([2, 1, 1, 1])
        cols[0].markdown(f"### Prioridad #{i}: {r.title}")
        cols[1].metric("Impacto", r.impact)
        cols[2].metric("Esfuerzo", r.effort)
        cols[3].metric("Tiempo", r.timing)
        st.write(f"**Por qué aparece:** {r.why}")
        st.write(f"**Acción inmediata:** {r.action}")
        st.write(f"**Mejora:** {r.metrics} | **Confianza:** {r.confidence}")

st.header("4. Plan de 7 días")
# Build sprint from top recs
days = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
for idx, day in enumerate(days):
    rec = recs[idx % len(recs)]
    with st.container(border=True):
        st.markdown(f"**{day}**")
        st.write(rec.action)
        st.caption(f"Objetivo: mejorar {rec.metrics}. Impacto: {rec.impact}. Esfuerzo: {rec.effort}.")

st.header("5. Exportar recomendaciones")
export_df = pd.DataFrame([r.__dict__ for r in recs])
st.download_button("Descargar recomendaciones CSV", export_df.to_csv(index=False).encode("utf-8"), "dynamic_recommendations.csv", "text/csv")

st.caption("Nota: las proyecciones son estimaciones para priorización. No son promesas de ranking, tráfico o revenue.")

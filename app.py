import io
import re
from typing import Dict, Tuple, List
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Trust & Visibility Intelligence Platform", layout="wide")

# -------------------------
# Helpers
# -------------------------
def clamp(x, low=0, high=100):
    return max(low, min(high, float(x)))

def safe_num(x, default=0):
    try:
        if pd.isna(x):
            return default
        if isinstance(x, str):
            x = x.replace(",", "").replace("%", "").strip()
        return float(x)
    except Exception:
        return default

def normalize_columns(df):
    df = df.copy()
    df.columns = [str(c).strip().lower().replace(" ", "_").replace("-", "_") for c in df.columns]
    return df

def robust_csv(uploaded_file):
    if uploaded_file is None:
        return None, "No file"
    raw = uploaded_file.getvalue()
    encodings = ["utf-8-sig", "utf-8", "latin-1", "cp1252"]
    seps = [",", ";", "\t"]
    best = None
    best_score = -1
    last_error = ""
    for enc in encodings:
        for sep in seps:
            try:
                text = raw.decode(enc, errors="ignore")
                # GA4 sometimes contains metadata rows before the real header.
                lines = text.splitlines()
                candidate_starts = list(range(min(25, len(lines))))
                for start in candidate_starts:
                    sample = "\n".join(lines[start:])
                    df = pd.read_csv(io.StringIO(sample), sep=sep, engine="python", on_bad_lines="skip")
                    df = df.dropna(how="all")
                    if df.shape[0] == 0 or df.shape[1] <= 1:
                        continue
                    score = df.shape[0] * df.shape[1]
                    if score > best_score:
                        best = normalize_columns(df)
                        best_score = score
            except Exception as e:
                last_error = str(e)
    if best is not None:
        return best, "ok"
    return None, last_error or "Could not parse file"

def find_col(df, options):
    if df is None:
        return None
    cols = list(df.columns)
    for opt in options:
        optn = opt.lower().replace(" ", "_").replace("-", "_")
        for c in cols:
            if c == optn or optn in c:
                return c
    return None

def sum_col(df, options):
    c = find_col(df, options)
    if c is None:
        return 0
    return float(pd.to_numeric(df[c].astype(str).str.replace(",", "", regex=False).str.replace("%", "", regex=False), errors="coerce").fillna(0).sum())

def avg_col(df, options):
    c = find_col(df, options)
    if c is None:
        return 0
    s = pd.to_numeric(df[c].astype(str).str.replace(",", "", regex=False).str.replace("%", "", regex=False), errors="coerce").dropna()
    return float(s.mean()) if len(s) else 0

# -------------------------
# Sidebar inputs
# -------------------------
st.sidebar.title("Inputs del negocio")
st.sidebar.caption("Puedes usar datos reales o estimados. La herramienta indica el nivel de confianza.")
website = st.sidebar.text_input("Website", "https://www.scalto.com")

st.sidebar.header("Autoridad manual")
dr = st.sidebar.number_input("Domain Rating / Authority externa", 0, 100, 22)
ref_domains = st.sidebar.number_input("Referring domains", 0, 100000, 127)
backlinks = st.sidebar.number_input("Backlinks", 0, 1000000, 549)
organic_keywords_manual = st.sidebar.number_input("Organic keywords", 0, 100000, 4)
brand_mentions = st.sidebar.number_input("Brand mentions estimadas", 0, 10000, 5)
media_mentions = st.sidebar.number_input("Apariciones en medios", 0, 10000, 1)

st.sidebar.header("Contenido y confianza")
service_pages = st.sidebar.number_input("Service pages", 0, 500, 8)
blog_articles = st.sidebar.number_input("Blog articles", 0, 5000, 94)
case_studies = st.sidebar.number_input("Case studies", 0, 500, 7)
testimonials = st.sidebar.number_input("Testimonials / logos", 0, 500, 8)
founders_visible = st.sidebar.checkbox("Founders visibles", True)
author_bios = st.sidebar.checkbox("Autores con bio", False)
about_page = st.sidebar.checkbox("Página About clara", True)
certifications = st.sidebar.checkbox("Certificaciones / credenciales", False)

st.sidebar.header("SEO técnico / AEO")
technical_seo = st.sidebar.slider("Technical SEO readiness", 0, 100, 57)
faq_schema = st.sidebar.checkbox("FAQ Schema", False)
org_schema = st.sidebar.checkbox("Organization Schema", True)
article_schema = st.sidebar.checkbox("Article Schema", False)
person_schema = st.sidebar.checkbox("Person Schema", False)
direct_answers = st.sidebar.checkbox("Direct answers en contenido", True)

st.sidebar.header("Business model")
avg_contract = st.sidebar.number_input("Average contract value", 0, 10000000, 18000)
visitor_to_lead = st.sidebar.slider("Visitor to lead rate (%)", 0.0, 20.0, 1.0, 0.1)
lead_to_customer = st.sidebar.slider("Lead to customer rate (%)", 0.0, 50.0, 10.0, 0.5)

# -------------------------
# Header
# -------------------------
st.title("Trust & Visibility Intelligence Platform")
st.caption("v7.0 - Dynamic executive guidance based on data, gaps, and actions")
st.write("La herramienta no solo muestra scores. Explica qué significan, qué los limita y cómo acciones específicas pueden impactar visibilidad, confianza y negocio.")

# -------------------------
# Uploads
# -------------------------
with st.expander("1. Cargar datos reales opcional", expanded=True):
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        gsc_file = st.file_uploader("Google Search Console CSV", type=["csv"], key="gsc")
    with col2:
        ga4_file = st.file_uploader("GA4 CSV", type=["csv"], key="ga4")
    with col3:
        linkedin_file = st.file_uploader("LinkedIn CSV", type=["csv"], key="li")
    with col4:
        social_file = st.file_uploader("Social Media CSV", type=["csv"], key="social")
    with col5:
        email_file = st.file_uploader("Email Marketing CSV", type=["csv"], key="email")
    st.info("No necesitas cargar todo. Si una plataforma no tiene data, el simulador usa inputs manuales y reduce el nivel de confianza.")

gsc, gsc_status = robust_csv(gsc_file)
ga4, ga4_status = robust_csv(ga4_file)
li, li_status = robust_csv(linkedin_file)
social, social_status = robust_csv(social_file)
email, email_status = robust_csv(email_file)

# -------------------------
# Extract metrics
# -------------------------
gsc_clicks = sum_col(gsc, ["clicks", "clics"])
gsc_impressions = sum_col(gsc, ["impressions", "impresiones"])
gsc_ctr = avg_col(gsc, ["ctr"])
gsc_position = avg_col(gsc, ["position", "posicion", "posición"])
gsc_queries = len(gsc) if gsc is not None else organic_keywords_manual

ga4_sessions = sum_col(ga4, ["sessions", "sesiones"])
ga4_users = sum_col(ga4, ["users", "usuarios", "active_users"])
ga4_conversions = sum_col(ga4, ["conversions", "conversiones", "key_events", "events"])
if ga4_sessions == 0 and ga4 is not None:
    # fallback for GA4 overview exports with metric rows
    numeric_total = 0
    for c in ga4.columns:
        vals = pd.to_numeric(ga4[c].astype(str).str.replace(",", "", regex=False), errors="coerce")
        if vals.notna().sum() > 0:
            numeric_total = max(numeric_total, float(vals.fillna(0).sum()))
    ga4_sessions = numeric_total if numeric_total < 10000000 else 0

li_impressions = sum_col(li, ["impressions", "impresiones"])
li_clicks = sum_col(li, ["clicks", "clics"])
li_engagement = avg_col(li, ["engagement_rate", "engagement", "interactions"])

social_impressions = sum_col(social, ["impressions", "reach", "alcance"])
social_engagement = sum_col(social, ["engagement", "interactions", "likes", "comments"])

email_sent = sum_col(email, ["sent", "recipients", "delivered", "envios", "enviados"])
email_opens = sum_col(email, ["opens", "open", "abiertos"])
email_clicks = sum_col(email, ["clicks", "clics"])
email_ctr = (email_clicks / email_sent * 100) if email_sent else 0

# Confidence
real_sources = sum([gsc is not None, ga4 is not None, li is not None, social is not None, email is not None])
confidence = "Alta" if real_sources >= 3 else "Media" if real_sources >= 1 else "Baja"

# -------------------------
# Scores
# -------------------------
def score_authority():
    dr_score = dr
    rd_score = clamp(np.log1p(ref_domains) / np.log1p(1000) * 100)
    backlinks_score = clamp(np.log1p(backlinks) / np.log1p(10000) * 100)
    brand_score = clamp(np.log1p(brand_mentions) / np.log1p(100) * 100)
    media_score = clamp(np.log1p(media_mentions) / np.log1p(50) * 100)
    return clamp(dr_score*.35 + rd_score*.25 + backlinks_score*.10 + brand_score*.15 + media_score*.15)

def score_content():
    service_score = clamp(service_pages / 12 * 100)
    blog_score = clamp(blog_articles / 120 * 100)
    case_score = clamp(case_studies / 12 * 100)
    topical = clamp((service_pages*4 + blog_articles*.4 + case_studies*3) / 100 * 100)
    return clamp(service_score*.25 + blog_score*.25 + case_score*.25 + topical*.25)

def score_eeat():
    s = 0
    s += 18 if founders_visible else 0
    s += 15 if author_bios else 0
    s += 12 if about_page else 0
    s += 12 if certifications else 0
    s += clamp(case_studies / 10 * 20)
    s += clamp(testimonials / 10 * 15)
    s += 8 if person_schema else 0
    return clamp(s)

def score_aeo():
    s = 0
    s += 20 if faq_schema else 0
    s += 18 if org_schema else 0
    s += 16 if article_schema else 0
    s += 14 if person_schema else 0
    s += 18 if direct_answers else 0
    s += clamp(blog_articles/100*14)
    return clamp(s)

def score_social():
    if li is None and social is None:
        return 10
    li_score = clamp(np.log1p(li_impressions + li_clicks*10) / np.log1p(100000) * 100)
    soc_score = clamp(np.log1p(social_impressions + social_engagement*5) / np.log1p(100000) * 100)
    return clamp(max(li_score, soc_score))

def score_email():
    if email is None:
        return 25
    ctr_score = clamp(email_ctr / 5 * 100)
    volume_score = clamp(np.log1p(email_sent) / np.log1p(50000) * 100)
    return clamp(ctr_score*.60 + volume_score*.40)

authority = score_authority()
content = score_content()
eeat = score_eeat()
aeo = score_aeo()
social = score_social()
email_score = score_email()
seo = clamp(technical_seo*.55 + content*.25 + authority*.20)
trust = clamp(eeat*.25 + authority*.20 + content*.20 + aeo*.15 + social*.10 + email_score*.10)
visibility = clamp(seo*.30 + authority*.20 + aeo*.20 + social*.20 + email_score*.10)
ai_ready = aeo

# -------------------------
# Dynamic narrative engine
# -------------------------
def level(score):
    if score >= 75: return "alto"
    if score >= 50: return "medio"
    return "bajo"

def emoji_level(score):
    if score >= 75: return "🟢"
    if score >= 50: return "🟡"
    return "🔴"

components = {
    "Technical SEO": technical_seo,
    "Authority": authority,
    "Content": content,
    "EEAT": eeat,
    "AEO/GEO": aeo,
    "Social": social,
    "Email": email_score,
}
weakest = sorted(components.items(), key=lambda x: x[1])[:3]
strongest = sorted(components.items(), key=lambda x: x[1], reverse=True)[:2]

def executive_story():
    story = []
    story.append(f"{emoji_level(trust)} Trust está en nivel {level(trust)} y {emoji_level(visibility)} Visibility está en nivel {level(visibility)}.")
    story.append(f"La señal más fuerte ahora es **{strongest[0][0]} ({strongest[0][1]:.0f}/100)**. La principal limitación es **{weakest[0][0]} ({weakest[0][1]:.0f}/100)**.")
    if weakest[0][0] == "Social":
        story.append("Esto no significa necesariamente que la marca no tenga redes. Significa que no cargaste data social o que la presencia social no está aportando suficiente señal de visibilidad.")
    if weakest[0][0] == "Authority":
        story.append("El sitio puede tener buen contenido, pero Google y los motores de IA necesitan más señales externas: menciones, enlaces, partners, medios y referencias de terceros.")
    if weakest[0][0] == "Content":
        story.append("La limitación principal está en cobertura temática. Publicar más contenido útil y actualizar páginas clave debería tener impacto directo en visibilidad.")
    if weakest[0][0] == "AEO/GEO":
        story.append("El contenido necesita estar más preparado para respuestas de IA: FAQs, schema, preguntas directas, definiciones, tablas y entidades claras.")
    return "\n\n".join(story)

def action_impact(articles, page_updates, linkedin_posts, newsletters, faqs, cases, new_ref_domains):
    d_content = clamp(articles*2.2 + page_updates*1.4 + faqs*.7 + cases*1.0, 0, 35)
    d_aeo = clamp(faqs*2.0 + articles*1.2 + page_updates*.5, 0, 35)
    d_social = clamp(linkedin_posts*3.0, 0, 30)
    d_email = clamp(newsletters*4.0, 0, 25)
    d_auth = clamp(new_ref_domains*1.3 + cases*.8 + linkedin_posts*.4, 0, 35)
    projected_trust = clamp(trust + d_content*.2 + d_aeo*.15 + d_social*.1 + d_email*.1 + d_auth*.2)
    projected_visibility = clamp(visibility + d_content*.25 + d_aeo*.2 + d_social*.2 + d_email*.08 + d_auth*.25)
    projected_ai = clamp(ai_ready + d_aeo)
    base_sessions = ga4_sessions if ga4_sessions else max(100, gsc_clicks, organic_keywords_manual*25)
    session_lift_pct = clamp((projected_visibility - visibility) * 1.1, 0, 80)
    projected_sessions = int(base_sessions * session_lift_pct / 100)
    incremental_leads = projected_sessions * (visitor_to_lead/100)
    incremental_customers = incremental_leads * (lead_to_customer/100)
    revenue = incremental_customers * avg_contract
    return {
        "Trust": projected_trust,
        "Visibility": projected_visibility,
        "AI Search": projected_ai,
        "Session Lift %": session_lift_pct,
        "Incremental Sessions": projected_sessions,
        "Incremental Leads": incremental_leads,
        "Incremental Customers": incremental_customers,
        "Revenue": revenue,
        "d_content": d_content,
        "d_aeo": d_aeo,
        "d_social": d_social,
        "d_email": d_email,
        "d_auth": d_auth,
    }

def explain_actions(articles, page_updates, linkedin_posts, newsletters, faqs, cases, refs):
    notes = []
    if articles > 0:
        notes.append(f"Publicar **{articles} artículos** aumenta cobertura temática. Eso puede generar más keywords, más oportunidades de aparecer en AI Search y más tráfico orgánico a mediano plazo.")
    if page_updates > 0:
        notes.append(f"Actualizar **{page_updates} páginas existentes** suele ser una acción de alto ROI porque mejora URLs que ya existen y pueden recuperar ranking más rápido que una página nueva.")
    if linkedin_posts > 0:
        notes.append(f"Publicar **{linkedin_posts} veces en LinkedIn** fortalece presencia ejecutiva, alcance, búsquedas de marca y tráfico referido. No es SEO directo, pero alimenta señales de confianza.")
    if newsletters > 0:
        notes.append(f"Enviar **{newsletters} newsletters** puede generar tráfico inmediato hacia contenido clave, mejorar engagement y convertir audiencias existentes en oportunidades comerciales.")
    if faqs > 0:
        notes.append(f"Agregar **{faqs} bloques FAQ/direct answers** mejora AEO/GEO porque facilita que Google AI, ChatGPT, Perplexity y Gemini extraigan respuestas claras.")
    if cases > 0:
        notes.append(f"Publicar **{cases} casos de estudio** impacta principalmente confianza y conversión. Puede no traer mucho tráfico, pero ayuda a transformar visitantes en leads.")
    if refs > 0:
        notes.append(f"Conseguir **{refs} nuevos referring domains** mejora autoridad. Esta es una de las señales más fuertes para competir por rankings y ser citado por terceros.")
    if not notes:
        notes.append("Selecciona acciones para ver cómo podrían impactar visibilidad, confianza y negocio.")
    return notes

# -------------------------
# Executive brief
# -------------------------
st.header("1. Executive Brief")
cols = st.columns(4)
cols[0].metric("Trust Score", f"{trust:.0f}/100", f"Nivel {level(trust)}")
cols[1].metric("Visibility Score", f"{visibility:.0f}/100", f"Nivel {level(visibility)}")
cols[2].metric("AI Search Readiness", f"{ai_ready:.0f}/100", f"Nivel {level(ai_ready)}")
cols[3].metric("Confidence", confidence, f"{real_sources} fuentes reales")

st.subheader("¿Qué significa esto?")
st.markdown(executive_story())

with st.expander("Ver cómo se calculan los scores"):
    st.markdown("""
**Trust Score** combina EEAT, autoridad, contenido, AEO/GEO, social y email.  
**Visibility Score** combina SEO técnico, autoridad, AEO/GEO, social y email.  
**Authority Score** no es lo mismo que Domain Rating. Usa DR como input, pero también considera referring domains, backlinks, menciones de marca y apariciones en medios.
""")
    score_df = pd.DataFrame({"Component": list(components.keys()), "Score": list(components.values())})
    st.dataframe(score_df, use_container_width=True, hide_index=True)
    fig = px.bar(score_df.sort_values("Score"), x="Score", y="Component", orientation="h", title="Score breakdown")
    st.plotly_chart(fig, use_container_width=True)

# Data status
with st.expander("Estado de datos cargados"):
    status = pd.DataFrame([
        ["GSC", "Leído" if gsc is not None else "No cargado/no leído", gsc_status],
        ["GA4", "Leído" if ga4 is not None else "No cargado/no leído", ga4_status],
        ["LinkedIn", "Leído" if li is not None else "No cargado/no leído", li_status],
        ["Social", "Leído" if social is not None else "No cargado/no leído", social_status],
        ["Email", "Leído" if email is not None else "No cargado/no leído", email_status],
    ], columns=["Fuente", "Estado", "Detalle"])
    st.dataframe(status, use_container_width=True, hide_index=True)

# -------------------------
# What if simulator
# -------------------------
st.header("2. ¿Qué pasa si hago estas acciones?")
st.caption("Mueve las acciones y la explicación cambia automáticamente según tus datos actuales.")

c1, c2, c3 = st.columns(3)
with c1:
    articles = st.slider("Artículos nuevos esta etapa", 0, 20, 2)
    page_updates = st.slider("Páginas existentes a actualizar", 0, 30, 5)
    faqs = st.slider("Bloques FAQ/direct answers", 0, 50, 8)
with c2:
    linkedin_posts = st.slider("Posts de LinkedIn por semana", 0, 10, 3)
    newsletters = st.slider("Newsletters al mes", 0, 8, 2)
    cases = st.slider("Casos de estudio nuevos", 0, 10, 1)
with c3:
    new_ref_domains = st.slider("Nuevos referring domains", 0, 50, 5)
    timeframe = st.selectbox("Horizonte de evaluación", ["7 días", "30 días", "90 días"], index=2)

impact = action_impact(articles, page_updates, linkedin_posts, newsletters, faqs, cases, new_ref_domains)

st.subheader("Impacto estimado")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Trust", f"{impact['Trust']:.0f}/100", f"+{impact['Trust']-trust:.1f}")
m2.metric("Visibility", f"{impact['Visibility']:.0f}/100", f"+{impact['Visibility']-visibility:.1f}")
m3.metric("AI Search", f"{impact['AI Search']:.0f}/100", f"+{impact['AI Search']-ai_ready:.1f}")
m4.metric("Revenue estimado", f"${impact['Revenue']:,.0f}", f"{impact['Incremental Leads']:.1f} leads")

st.subheader("La herramienta interpreta el escenario así")
for n in explain_actions(articles, page_updates, linkedin_posts, newsletters, faqs, cases, new_ref_domains):
    st.markdown(f"- {n}")

st.info(f"Nivel de confianza de la proyección: **{confidence}**. Aumenta cuando cargas más datos reales de GA4, GSC, LinkedIn, social o email.")

# -------------------------
# Flywheel
# -------------------------
st.header("3. Efecto en cadena")
flywheel = []
if articles or page_updates:
    flywheel.append("Contenido mejorado")
if linkedin_posts:
    flywheel.append("Distribución en LinkedIn")
if newsletters:
    flywheel.append("Tráfico desde email")
if faqs:
    flywheel.append("Respuestas claras para AI Search")
if cases:
    flywheel.append("Más prueba social")
if new_ref_domains:
    flywheel.append("Más autoridad externa")
flywheel += ["Más visibilidad", "Más confianza", "Más leads", "Más oportunidades"]
st.markdown(" → ".join([f"**{x}**" for x in flywheel]))

# -------------------------
# Opportunity engine
# -------------------------
st.header("4. Qué deberías priorizar ahora")
recommendations = []
if authority < 45:
    recommendations.append(["Aumentar autoridad externa", "Conseguir menciones, partners o referring domains", "Muy alto", "Medio", "+Authority, +Visibility", "Alta" if ref_domains else "Media"])
if content < 50:
    recommendations.append(["Actualizar contenido clave", "Reescribir páginas de servicios y crear contenido evergreen", "Muy alto", "Medio", "+Content, +SEO, +AI", "Media"])
if aeo < 60:
    recommendations.append(["Agregar FAQs y direct answers", "Optimizar páginas para preguntas y respuestas concretas", "Alto", "Bajo", "+AEO/GEO", "Alta"])
if social < 40:
    recommendations.append(["Activar LinkedIn", "Publicar 3 veces por semana y conectar posts con páginas clave", "Alto", "Bajo", "+Social, +Trust", "Media"])
if email_score < 45:
    recommendations.append(["Usar email para distribución", "Enviar contenido nuevo a audiencias existentes", "Medio", "Bajo", "+Engagement, +Leads", "Media"])
if eeat < 70:
    recommendations.append(["Fortalecer EEAT", "Agregar autores, bios, credenciales, founders y casos", "Alto", "Medio", "+Trust", "Alta"])

rec_df = pd.DataFrame(recommendations, columns=["Prioridad", "Acción", "Impacto", "Esfuerzo", "Mejora", "Confianza"])
st.dataframe(rec_df, use_container_width=True, hide_index=True)

# -------------------------
# 7-day sprint
# -------------------------
st.header("5. Plan recomendado para los próximos 7 días")
plan = []
if aeo < 60:
    plan.append(["Día 1", "Agregar FAQ/direct answers a 2 páginas de servicio", "AEO/GEO", "2-3 horas"])
if content < 60:
    plan.append(["Día 2", "Actualizar 2 páginas con mejor title, H1, CTA y enlaces internos", "SEO + Conversión", "3-4 horas"])
if social < 50:
    plan.append(["Día 3", "Publicar 1 post de LinkedIn desde fundador enlazando a una página clave", "Executive Presence", "45 min"])
if authority < 50:
    plan.append(["Día 4", "Identificar 10 partners/directorios/asociaciones para menciones o enlaces", "Authority", "2 horas"])
if eeat < 75:
    plan.append(["Día 5", "Agregar bios, credenciales o prueba social a páginas clave", "Trust", "2-3 horas"])
if email_score < 50:
    plan.append(["Día 6", "Enviar newsletter llevando tráfico al contenido actualizado", "Engagement + Leads", "2 horas"])
plan.append(["Día 7", "Revisar métricas y ajustar prioridades", "Learning loop", "1 hora"])
st.dataframe(pd.DataFrame(plan, columns=["Día", "Acción", "Impacto principal", "Tiempo estimado"]), use_container_width=True, hide_index=True)

# -------------------------
# Export
# -------------------------
st.header("6. Exportar resultados")
export = pd.DataFrame({
    "metric": ["trust", "visibility", "ai_ready", "authority", "content", "eeat", "social", "email", "projected_trust", "projected_visibility", "projected_revenue", "confidence"],
    "value": [trust, visibility, ai_ready, authority, content, eeat, social, email_score, impact["Trust"], impact["Visibility"], impact["Revenue"], confidence]
})
st.download_button("Descargar resumen CSV", export.to_csv(index=False).encode("utf-8"), "trust_visibility_summary.csv", "text/csv")

st.caption("Nota: este modelo es una simulación estratégica, no una promesa de resultados. Los outputs deben usarse para priorización, planificación y discusión ejecutiva.")

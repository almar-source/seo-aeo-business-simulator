import math
from io import StringIO
from typing import Dict, List, Tuple

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

st.set_page_config(page_title="Trust & Visibility Intelligence v6", layout="wide")

APP_VERSION = "v6.0 - Executive clarity + action impact simulator"

# -----------------------------
# Helpers
# -----------------------------
def clamp(x, low=0, high=100):
    try:
        return max(low, min(high, float(x)))
    except Exception:
        return low


def safe_num(x, default=0):
    try:
        if pd.isna(x):
            return default
        if isinstance(x, str):
            x = x.replace(",", "").replace("%", "").strip()
        return float(x)
    except Exception:
        return default


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().lower().replace(" ", "_").replace("-", "_") for c in df.columns]
    return df


def robust_read_csv(uploaded_file):
    if uploaded_file is None:
        return None
    raw = uploaded_file.getvalue()
    for enc in ["utf-8-sig", "utf-8", "latin-1"]:
        for sep in [",", ";", "\t"]:
            try:
                text = raw.decode(enc, errors="ignore")
                # Find the first likely header row, useful for GA4 exports with preamble blocks
                lines = [ln for ln in text.splitlines() if ln.strip()]
                header_idx = 0
                header_keywords = ["session", "users", "query", "click", "impression", "page", "title", "post", "sent", "open"]
                for i, line in enumerate(lines[:40]):
                    low = line.lower()
                    if sum(k in low for k in header_keywords) >= 2:
                        header_idx = i
                        break
                cleaned = "\n".join(lines[header_idx:])
                df = pd.read_csv(StringIO(cleaned), sep=sep, engine="python", on_bad_lines="skip")
                if df.shape[1] >= 2 and len(df) > 0:
                    return normalize_columns(df)
            except Exception:
                continue
    st.warning(f"No pude leer {uploaded_file.name}. Puedes ingresar los datos manualmente.")
    return None


def col_contains(df, options):
    if df is None:
        return None
    cols = list(df.columns)
    for opt in options:
        for c in cols:
            if opt in c:
                return c
    return None


def sum_col(df, options):
    c = col_contains(df, options)
    if c is None:
        return 0
    return sum(safe_num(v) for v in df[c])


def avg_col(df, options):
    c = col_contains(df, options)
    if c is None:
        return 0
    vals = [safe_num(v, None) for v in df[c]]
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals) if vals else 0


def score_level(score):
    if score >= 75:
        return "Fuerte", "🟢"
    if score >= 50:
        return "Medio", "🟡"
    return "Bajo", "🔴"


def bar_chart(data: Dict[str, float], title: str):
    fig, ax = plt.subplots(figsize=(9, 3.8))
    labels = list(data.keys())
    vals = list(data.values())
    ax.bar(labels, vals)
    ax.set_ylim(0, 100)
    ax.set_title(title)
    ax.set_ylabel("Score")
    ax.tick_params(axis="x", rotation=35)
    st.pyplot(fig)


def estimate_technical_score(unique_titles, unique_metas, h_structure, speed, indexability, internal_linking):
    return clamp(unique_titles * .18 + unique_metas * .14 + h_structure * .16 + speed * .18 + indexability * .22 + internal_linking * .12)


def authority_score(dr, referring_domains, backlinks, organic_keywords, brand_mentions, media_mentions, linkedin_followers):
    rd_score = clamp(math.log10(max(referring_domains, 1)) * 28)
    backlink_score = clamp(math.log10(max(backlinks, 1)) * 18)
    kw_score = clamp(math.log10(max(organic_keywords, 1)) * 24)
    mention_score = clamp(brand_mentions * 2.5)
    media_score = clamp(media_mentions * 5)
    li_score = clamp(math.log10(max(linkedin_followers, 1)) * 16)
    return clamp(dr * .30 + rd_score * .20 + backlink_score * .10 + kw_score * .15 + mention_score * .10 + media_score * .10 + li_score * .05)


def eeat_score(founders_visible, author_bios, about_page, case_studies, testimonials, certifications, contact_info, client_logos):
    return clamp(
        founders_visible * 14 + author_bios * 14 + about_page * 10 + min(case_studies, 8) * 4 + testimonials * 12 + certifications * 10 + contact_info * 10 + client_logos * 8
    )


def content_score(service_pages, blog_articles, case_studies, faq_blocks, topic_coverage, updated_pages):
    return clamp(min(service_pages, 10)*4 + min(blog_articles, 80)*.25 + min(case_studies, 8)*3 + min(faq_blocks, 40)*.7 + topic_coverage*.25 + min(updated_pages, 20)*1.2)


def aeo_score(faq_schema, org_schema, article_schema, person_schema, breadcrumbs, direct_answers, tables_lists, external_citations):
    return clamp(faq_schema*18 + org_schema*14 + article_schema*12 + person_schema*10 + breadcrumbs*8 + direct_answers*18 + tables_lists*10 + external_citations*10)


def social_score(linkedin_impressions, linkedin_engagement, linkedin_followers, posts_per_month, other_social_engagement):
    imp = clamp(math.log10(max(linkedin_impressions, 1))*18)
    fol = clamp(math.log10(max(linkedin_followers, 1))*16)
    eng = clamp(linkedin_engagement*8)
    posts = clamp(posts_per_month*4)
    other = clamp(other_social_engagement*6)
    return clamp(imp*.25 + fol*.20 + eng*.25 + posts*.20 + other*.10)


def email_score(sent, open_rate, click_rate):
    volume = clamp(math.log10(max(sent, 1))*18)
    opens = clamp(open_rate*2.5)
    clicks = clamp(click_rate*10)
    return clamp(volume*.25 + opens*.35 + clicks*.40)


def business_projection(base_sessions, cvr, close_rate, avg_deal, session_lift_pct, conversion_lift_pct=0):
    incremental_sessions = max(0, int(base_sessions * session_lift_pct / 100))
    effective_cvr = max(0, cvr + conversion_lift_pct)
    leads = incremental_sessions * effective_cvr / 100
    customers = leads * close_rate / 100
    revenue = customers * avg_deal
    return incremental_sessions, leads, customers, revenue


def action_impacts(actions):
    # Returns impact deltas for each dimension
    articles = actions["new_articles"]
    service_updates = actions["service_updates"]
    faqs = actions["faq_blocks"]
    cases = actions["case_studies"]
    li_posts = actions["linkedin_posts"]
    newsletters = actions["newsletters"]
    backlinks = actions["new_ref_domains"]
    titles = actions["title_meta_updates"]
    videos = actions["videos"]

    return {
        "SEO": clamp(articles*2.2 + service_updates*1.8 + backlinks*.9 + titles*.8 + videos*.7, 0, 35),
        "AI Search": clamp(articles*2.4 + faqs*1.6 + service_updates*1.2 + videos*.8, 0, 35),
        "Trust": clamp(cases*4.5 + service_updates*1.1 + li_posts*.5 + backlinks*.7 + newsletters*.4, 0, 30),
        "Social": clamp(li_posts*3.2 + videos*2.2 + newsletters*.5, 0, 35),
        "Conversion": clamp(cases*3.8 + service_updates*1.4 + newsletters*.8 + faqs*.4, 0, 25),
        "Sessions Lift %": clamp(articles*2.8 + service_updates*1.7 + li_posts*.7 + newsletters*1.2 + backlinks*.6 + titles*.5 + videos*1.1, 0, 45),
        "Conversion Lift %": clamp(cases*.18 + service_updates*.08 + faqs*.04 + newsletters*.05, 0, 2.0),
    }


def explain_action(action_name, qty):
    explanations = {
        "new_articles": ("Publicar artículos", "Más cobertura temática → más keywords potenciales → más opciones de aparecer en Google y respuestas de IA → más tráfico calificado."),
        "service_updates": ("Actualizar páginas de servicios", "Mejora la claridad comercial → Google entiende mejor la oferta → los visitantes entienden más rápido el valor → sube la conversión."),
        "faq_blocks": ("Agregar FAQs/direct answers", "Convierte dudas reales en respuestas claras → aumenta la preparación para AI Search, snippets y búsquedas conversacionales."),
        "case_studies": ("Publicar casos de estudio", "Aumenta prueba social y EEAT → no siempre sube mucho tráfico, pero mejora confianza y conversión."),
        "linkedin_posts": ("Publicar en LinkedIn", "Más alcance ejecutivo → más visitas al perfil y al sitio → más búsquedas de marca → mejores señales de confianza."),
        "newsletters": ("Enviar newsletters", "Genera tráfico recurrente hacia contenido clave → mejora engagement → apoya conversión y nurturing."),
        "new_ref_domains": ("Conseguir referring domains", "Más sitios enlazando al dominio → más autoridad → mayor capacidad de posicionar contenido competitivo."),
        "title_meta_updates": ("Optimizar titles/metas", "Mejor alineación con intención de búsqueda → puede mejorar CTR desde Google sin crear páginas nuevas."),
        "videos": ("Crear videos o clips", "Aumenta presencia multicanal → mejora tiempo de consumo y reutilización en LinkedIn, YouTube y email."),
    }
    label, why = explanations[action_name]
    if qty <= 0:
        return None
    return {"Acción": label, "Cantidad": qty, "Por qué impacta": why}


def seven_day_plan(scores, actions):
    plan = []
    if scores["Content"] < 55 or actions["service_updates"] > 0:
        plan.append(("Día 1", "Actualizar 2 páginas de servicio", "Mejora claridad, SEO on-page y conversión", "Alto"))
    if scores["AEO/GEO"] < 60 or actions["faq_blocks"] > 0:
        plan.append(("Día 2", "Agregar FAQs y respuestas directas", "Mejora preparación para AI Search", "Muy alto"))
    if actions["new_articles"] > 0:
        plan.append(("Día 3", "Publicar 1 artículo optimizado", "Aumenta cobertura temática y keywords", "Alto"))
    if scores["Social"] < 45 or actions["linkedin_posts"] > 0:
        plan.append(("Día 4", "Publicar 2 posts en LinkedIn", "Refuerza presencia ejecutiva y búsquedas de marca", "Alto"))
    if scores["Trust"] < 65 or actions["case_studies"] > 0:
        plan.append(("Día 5", "Preparar un caso o testimonio", "Aumenta confianza y conversión", "Muy alto"))
    if actions["newsletters"] > 0:
        plan.append(("Día 6", "Enviar newsletter hacia contenido clave", "Activa tráfico recurrente y nurturing", "Medio"))
    plan.append(("Día 7", "Medir resultados y ajustar prioridades", "Revisar GSC, GA4, LinkedIn y email", "Alto"))
    return plan[:7]

# -----------------------------
# Sidebar inputs
# -----------------------------
st.sidebar.title("Inputs del negocio")
st.sidebar.caption("Usa datos reales si los tienes. Si no, ingresa estimados manuales.")

website = st.sidebar.text_input("Website", "https://www.scalto.com")

st.sidebar.subheader("Autoridad manual")
dr = st.sidebar.number_input("Domain Rating / Authority externa", min_value=0, max_value=100, value=22)
ref_domains = st.sidebar.number_input("Referring domains", min_value=0, value=127)
backlinks = st.sidebar.number_input("Backlinks", min_value=0, value=549)
organic_keywords = st.sidebar.number_input("Organic keywords", min_value=0, value=4)
brand_mentions = st.sidebar.number_input("Brand mentions estimadas", min_value=0, value=5)
media_mentions = st.sidebar.number_input("Apariciones en medios", min_value=0, value=1)

st.sidebar.subheader("Contenido y confianza")
service_pages = st.sidebar.number_input("Service pages", min_value=0, value=6)
blog_articles = st.sidebar.number_input("Blog/articles", min_value=0, value=20)
case_studies_current = st.sidebar.number_input("Casos de estudio actuales", min_value=0, value=3)
faq_blocks_current = st.sidebar.number_input("Bloques FAQ actuales", min_value=0, value=8)
topic_coverage = st.sidebar.slider("Cobertura temática", 0, 100, 35)
updated_pages = st.sidebar.number_input("Páginas actualizadas últimos 90 días", min_value=0, value=4)

founders_visible = st.sidebar.checkbox("Founders/equipo visible", value=True)
author_bios = st.sidebar.checkbox("Autores con bio", value=False)
about_page = st.sidebar.checkbox("Página About clara", value=True)
testimonials = st.sidebar.checkbox("Testimonios", value=True)
certifications = st.sidebar.checkbox("Certificaciones/premios", value=False)
contact_info = st.sidebar.checkbox("Contacto visible", value=True)
client_logos = st.sidebar.checkbox("Logos de clientes/partners", value=True)

st.sidebar.subheader("Técnico")
unique_titles = st.sidebar.slider("Titles únicos", 0, 100, 55)
unique_metas = st.sidebar.slider("Metas únicas", 0, 100, 50)
h_structure = st.sidebar.slider("Estructura H1/H2", 0, 100, 60)
speed = st.sidebar.slider("Mobile speed / CWV", 0, 100, 55)
indexability = st.sidebar.slider("Indexabilidad/canonicals/sitemap", 0, 100, 70)
internal_linking = st.sidebar.slider("Internal linking", 0, 100, 45)

st.sidebar.subheader("AEO/GEO")
faq_schema = st.sidebar.checkbox("FAQ Schema", value=False)
org_schema = st.sidebar.checkbox("Organization Schema", value=True)
article_schema = st.sidebar.checkbox("Article Schema", value=False)
person_schema = st.sidebar.checkbox("Person Schema", value=False)
breadcrumbs = st.sidebar.checkbox("Breadcrumb Schema", value=True)
direct_answers = st.sidebar.checkbox("Direct answers", value=True)
tables_lists = st.sidebar.checkbox("Tablas/listas", value=True)
external_citations = st.sidebar.checkbox("Citas externas", value=False)

st.sidebar.subheader("Modelo de negocio")
avg_deal = st.sidebar.number_input("Valor promedio por cliente", min_value=0, value=12000, step=500)
visitor_to_lead = st.sidebar.number_input("Visitor to lead %", min_value=0.0, max_value=100.0, value=1.2, step=.1)
lead_to_customer = st.sidebar.number_input("Lead to customer %", min_value=0.0, max_value=100.0, value=15.0, step=.5)

# -----------------------------
# Main app
# -----------------------------
st.title("Trust & Visibility Intelligence Platform")
st.caption(APP_VERSION)
st.write("La herramienta explica cómo acciones de contenido, SEO, LinkedIn, social media y email pueden impactar visibilidad, confianza y negocio.")

with st.expander("1. Cargar datos reales opcional", expanded=False):
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
    st.info("No necesitas cargar todo. Si una plataforma no tiene data, el simulador usa los inputs manuales.")

gsc = robust_read_csv(gsc_file)
ga4 = robust_read_csv(ga4_file)
li = robust_read_csv(linkedin_file)
social = robust_read_csv(social_file)
email = robust_read_csv(email_file)

# Extract metrics from uploaded data
base_sessions = int(sum_col(ga4, ["session", "sessions"]) or 1000)
ga4_conversions = sum_col(ga4, ["conversion", "key_event", "event_count"])
if ga4 is not None and base_sessions > 0 and ga4_conversions > 0:
    visitor_to_lead_effective = min(100, (ga4_conversions / base_sessions) * 100)
else:
    visitor_to_lead_effective = visitor_to_lead

gsc_clicks = sum_col(gsc, ["click"])
gsc_impressions = sum_col(gsc, ["impression"])
gsc_ctr = (gsc_clicks / gsc_impressions * 100) if gsc_impressions else 0

li_impressions = sum_col(li, ["impression", "views"])
li_clicks = sum_col(li, ["click"])
li_engagement = avg_col(li, ["engagement_rate", "engagement"])
linkedin_followers = int(sum_col(li, ["followers", "follower"]) or 1200)
posts_per_month = int(len(li) if li is not None else 0)

other_social_engagement = avg_col(social, ["engagement", "engagement_rate"])

email_sent = sum_col(email, ["sent", "delivered", "recipients"])
email_opens = sum_col(email, ["open", "opens"])
email_clicks = sum_col(email, ["click", "clicks"])
email_open_rate = (email_opens / email_sent * 100) if email_sent else 25
email_click_rate = (email_clicks / email_sent * 100) if email_sent else 2.5

technical = estimate_technical_score(unique_titles, unique_metas, h_structure, speed, indexability, internal_linking)
authority = authority_score(dr, ref_domains, backlinks, organic_keywords, brand_mentions, media_mentions, linkedin_followers)
eeat = eeat_score(int(founders_visible), int(author_bios), int(about_page), case_studies_current, int(testimonials), int(certifications), int(contact_info), int(client_logos))
content = content_score(service_pages, blog_articles, case_studies_current, faq_blocks_current, topic_coverage, updated_pages)
aeo = aeo_score(int(faq_schema), int(org_schema), int(article_schema), int(person_schema), int(breadcrumbs), int(direct_answers), int(tables_lists), int(external_citations))
social_s = social_score(li_impressions, li_engagement, linkedin_followers, posts_per_month, other_social_engagement)
email_s = email_score(email_sent or 1000, email_open_rate, email_click_rate)

trust = clamp(eeat*.25 + authority*.20 + content*.20 + aeo*.15 + social_s*.10 + technical*.10)
visibility = clamp(technical*.20 + authority*.22 + content*.18 + aeo*.20 + social_s*.15 + email_s*.05)

scores = {"Trust": trust, "Visibility": visibility, "Technical SEO": technical, "Authority": authority, "Content": content, "AEO/GEO": aeo, "Social": social_s, "Email": email_s, "EEAT": eeat}

# -----------------------------
# Executive brief
# -----------------------------
st.header("1. Executive Brief")
trust_level, trust_icon = score_level(trust)
vis_level, vis_icon = score_level(visibility)
aeo_level, aeo_icon = score_level(aeo)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Trust Score", f"{trust:.0f}/100", trust_level)
m2.metric("Visibility Score", f"{visibility:.0f}/100", vis_level)
m3.metric("AI Search Readiness", f"{aeo:.0f}/100", aeo_level)
m4.metric("Authority Score", f"{authority:.0f}/100", f"DR input: {dr}")

weakest = min({k: v for k, v in scores.items() if k in ["Authority", "Content", "AEO/GEO", "Social", "Technical SEO", "Email"]}.items(), key=lambda x: x[1])
strongest = max({k: v for k, v in scores.items() if k in ["Authority", "Content", "AEO/GEO", "Social", "Technical SEO", "Email"]}.items(), key=lambda x: x[1])

st.markdown(f"""
### ¿Qué significa esto?
**{trust_icon} Trust está en nivel {trust_level.lower()}** y **{vis_icon} Visibility está en nivel {vis_level.lower()}**.  
La señal más fuerte ahora es **{strongest[0]} ({strongest[1]:.0f}/100)**. La principal limitación es **{weakest[0]} ({weakest[1]:.0f}/100)**.

En lenguaje simple: la herramienta está evaluando si la empresa no solo tiene contenido, sino si ese contenido puede ser encontrado, citado por IA, respaldado por autoridad y convertido en oportunidades comerciales.
""")

with st.expander("Ver cómo se calculan los scores"):
    st.markdown("""
**Trust Score** = EEAT 25% + Authority 20% + Content 20% + AEO/GEO 15% + Social 10% + Technical SEO 10%.  
**Visibility Score** = Technical SEO 20% + Authority 22% + Content 18% + AEO/GEO 20% + Social 15% + Email 5%.

**Domain Rating** es un input externo. **Authority Score** es un score calculado por la app usando DR, referring domains, backlinks, keywords, menciones, medios y LinkedIn.
""")
    bar_chart({k: scores[k] for k in ["EEAT", "Authority", "Content", "AEO/GEO", "Social", "Email", "Technical SEO"]}, "Score breakdown")

# -----------------------------
# What-if simulator
# -----------------------------
st.header("2. ¿Qué pasa si hago esta acción?")
st.write("Mueve las acciones que piensas ejecutar. La herramienta explica qué mejora, por qué y cómo puede impactar negocio.")

c1, c2, c3 = st.columns(3)
with c1:
    new_articles = st.number_input("Artículos nuevos", min_value=0, max_value=30, value=2)
    service_updates = st.number_input("Páginas de servicio a actualizar", min_value=0, max_value=30, value=3)
    faq_blocks = st.number_input("FAQs/direct answers nuevos", min_value=0, max_value=80, value=6)
with c2:
    case_studies_new = st.number_input("Casos/testimonios nuevos", min_value=0, max_value=10, value=1)
    linkedin_posts = st.number_input("Posts de LinkedIn esta semana", min_value=0, max_value=20, value=3)
    newsletters = st.number_input("Newsletters/campañas", min_value=0, max_value=10, value=1)
with c3:
    new_ref_domains = st.number_input("Nuevos referring domains objetivo", min_value=0, max_value=100, value=5)
    title_meta_updates = st.number_input("Titles/metas a optimizar", min_value=0, max_value=200, value=10)
    videos = st.number_input("Videos/clips nuevos", min_value=0, max_value=20, value=1)

actions = {
    "new_articles": new_articles,
    "service_updates": service_updates,
    "faq_blocks": faq_blocks,
    "case_studies": case_studies_new,
    "linkedin_posts": linkedin_posts,
    "newsletters": newsletters,
    "new_ref_domains": new_ref_domains,
    "title_meta_updates": title_meta_updates,
    "videos": videos,
}
impacts = action_impacts(actions)
projected_trust = clamp(trust + impacts["Trust"])
projected_visibility = clamp(visibility + (impacts["SEO"]*.25 + impacts["AI Search"]*.25 + impacts["Social"]*.18 + impacts["Trust"]*.12 + impacts["Conversion"]*.05))
inc_sessions, inc_leads, inc_customers, inc_revenue = business_projection(base_sessions, visitor_to_lead_effective, lead_to_customer, avg_deal, impacts["Sessions Lift %"], impacts["Conversion Lift %"])

p1, p2, p3, p4 = st.columns(4)
p1.metric("Trust proyectado", f"{projected_trust:.0f}/100", f"+{projected_trust-trust:.0f}")
p2.metric("Visibility proyectado", f"{projected_visibility:.0f}/100", f"+{projected_visibility-visibility:.0f}")
p3.metric("Sesiones incrementales", f"+{inc_sessions:,}")
p4.metric("Revenue estimado", f"${inc_revenue:,.0f}")

st.subheader("Impacto por dimensión")
bar_chart({"SEO": impacts["SEO"], "AI Search": impacts["AI Search"], "Trust": impacts["Trust"], "Social": impacts["Social"], "Conversion": impacts["Conversion"]}, "Impacto estimado de las acciones seleccionadas")

st.subheader("Explicación de impacto")
explanations = [explain_action(k, v) for k, v in actions.items()]
explanations = [e for e in explanations if e]
if explanations:
    for e in explanations:
        with st.container(border=True):
            st.markdown(f"**{e['Acción']}** | Cantidad: **{e['Cantidad']}**")
            st.write(e["Por qué impacta"])
else:
    st.info("Selecciona al menos una acción para ver la explicación.")

st.subheader("Efecto en cadena")
st.markdown("""
**Contenido / casos / LinkedIn / email no funcionan aislados.**  
La lógica del modelo es:

Acción → más señales de autoridad → más visibilidad → más tráfico calificado → más confianza → más leads → más oportunidades comerciales.
""")

# -----------------------------
# Opportunity engine + 7 day plan
# -----------------------------
st.header("3. Qué hacer primero")

opportunities = []
if authority < 50:
    opportunities.append(("Aumentar autoridad", "Conseguir 5-10 menciones o referring domains relevantes", "Muy alto", "Media", "+Authority / +Visibility"))
if content < 55:
    opportunities.append(("Mejorar contenido", "Actualizar páginas de servicios y crear 2 artículos estratégicos", "Muy alto", "Media", "+SEO / +AI Search"))
if aeo < 60:
    opportunities.append(("Optimizar para AI Search", "Agregar FAQs, direct answers y schema", "Muy alto", "Baja", "+AEO/GEO"))
if social_s < 45:
    opportunities.append(("Activar LinkedIn", "Publicar 3 posts ejecutivos con links a contenido clave", "Alto", "Baja", "+Social / +Brand Search"))
if trust < 65:
    opportunities.append(("Fortalecer confianza", "Publicar caso, testimonios o logos de clientes", "Alto", "Media", "+Trust / +Conversion"))
if technical < 65:
    opportunities.append(("SEO técnico rápido", "Corregir titles, metas, H1/H2 e internal links", "Alto", "Baja", "+Technical SEO"))

opp_df = pd.DataFrame(opportunities, columns=["Prioridad", "Acción recomendada", "Impacto", "Esfuerzo", "Mejora esperada"])
st.dataframe(opp_df, use_container_width=True, hide_index=True)

st.subheader("Plan recomendado para los próximos 7 días")
plan = seven_day_plan(scores, actions)
plan_df = pd.DataFrame(plan, columns=["Día", "Acción", "Por qué", "Impacto"])
st.dataframe(plan_df, use_container_width=True, hide_index=True)

# -----------------------------
# Data summary + export
# -----------------------------
st.header("4. Datos cargados y proyección")
d1, d2, d3, d4, d5 = st.columns(5)
d1.metric("GA4 sessions", f"{base_sessions:,}")
d2.metric("GSC clicks", f"{int(gsc_clicks):,}")
d3.metric("GSC CTR", f"{gsc_ctr:.2f}%")
d4.metric("LinkedIn impressions", f"{int(li_impressions):,}")
d5.metric("Email CTR", f"{email_click_rate:.2f}%")

export = pd.DataFrame([
    {"Metric": "Trust Score", "Current": trust, "Projected": projected_trust},
    {"Metric": "Visibility Score", "Current": visibility, "Projected": projected_visibility},
    {"Metric": "Authority", "Current": authority, "Projected": authority + impacts["SEO"]*.1 + impacts["Trust"]*.1},
    {"Metric": "Content", "Current": content, "Projected": content + impacts["SEO"]*.2},
    {"Metric": "AEO/GEO", "Current": aeo, "Projected": aeo + impacts["AI Search"]*.4},
    {"Metric": "Social", "Current": social_s, "Projected": social_s + impacts["Social"]*.4},
    {"Metric": "Incremental Sessions", "Current": 0, "Projected": inc_sessions},
    {"Metric": "Incremental Leads", "Current": 0, "Projected": inc_leads},
    {"Metric": "Incremental Customers", "Current": 0, "Projected": inc_customers},
    {"Metric": "Estimated Revenue", "Current": 0, "Projected": inc_revenue},
])
st.download_button("Descargar reporte CSV", data=export.to_csv(index=False), file_name="trust_visibility_report.csv", mime="text/csv")

st.caption("Nota: las proyecciones son estimaciones direccionales, no predicciones garantizadas. Sirven para priorizar acciones y explicar impacto potencial.")

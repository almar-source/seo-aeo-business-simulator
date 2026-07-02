import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from parsers.csv_parsers import parse_upload, extract_metrics
from engines.scoring import compute_scores, label
from engines.diagnosis import executive_brief, strongest_and_weakest
from engines.recommendations import get_recommendations, seven_day_plan
from engines.simulation import simulate, action_explanation

st.set_page_config(page_title="Trust & Visibility Intelligence Platform", layout="wide")

st.title("Trust & Visibility Intelligence Platform 2.0")
st.caption("Arquitectura modular: datos, diagnóstico, conocimiento, recomendaciones, simulación y negocio.")
st.write("La plataforma no promete resultados exactos. Explica qué puede estar frenando la visibilidad y prioriza acciones con mayor probabilidad de impacto.")

with st.sidebar:
    st.header("Inputs del negocio")
    website = st.text_input("Website", "https://www.scalto.com")

    st.subheader("Autoridad manual")
    domain_rating = st.number_input("Domain Rating / Authority externa", 0, 100, 22)
    referring_domains = st.number_input("Referring domains", 0, 100000, 127)
    backlinks = st.number_input("Backlinks", 0, 1000000, 549)
    organic_keywords = st.number_input("Organic keywords", 0, 1000000, 4)
    brand_mentions = st.number_input("Brand mentions estimadas", 0, 100000, 5)
    media_mentions = st.number_input("Apariciones en medios", 0, 100000, 1)

    st.subheader("Contenido y confianza")
    service_pages = st.number_input("Service pages", 0, 500, 8)
    blog_articles = st.number_input("Blog articles", 0, 2000, 25)
    case_studies = st.number_input("Case studies", 0, 500, 4)
    faqs = st.number_input("FAQs / direct answers", 0, 1000, 12)
    content_quality = st.slider("Calidad percibida del contenido", 0, 100, 55)
    technical_seo = st.slider("Technical SEO", 0, 100, 57)
    direct_answers = st.slider("Direct answer readiness", 0, 100, 40)

    st.subheader("EEAT y pruebas de confianza")
    founders_visible = st.checkbox("Fundadores/equipo visible", True)
    about_page = st.checkbox("Página About clara", True)
    author_bios = st.checkbox("Autores con biografía", False)
    testimonials = st.checkbox("Testimonios/logos", True)
    certifications = st.checkbox("Certificaciones/premios", False)

    st.subheader("Schema/AEO")
    faq_schema = st.checkbox("FAQ Schema", False)
    organization_schema = st.checkbox("Organization Schema", True)
    article_schema = st.checkbox("Article Schema", False)
    person_schema = st.checkbox("Person Schema", False)

    st.subheader("Datos manuales si no hay CSV")
    manual_social_score = st.slider("Social Score manual", 0, 100, 10)
    manual_email_score = st.slider("Email Score manual", 0, 100, 20)

    st.subheader("Business model")
    monthly_sessions = st.number_input("Sesiones mensuales base", 0, 10000000, 1000)
    visitor_to_lead = st.number_input("Visitante a lead (%)", 0.0, 100.0, 1.0, step=0.1)
    lead_to_customer = st.number_input("Lead a cliente (%)", 0.0, 100.0, 10.0, step=0.5)
    avg_deal_value = st.number_input("Ticket promedio / deal value", 0, 10000000, 18000)

inputs = {
    'domain_rating': domain_rating, 'referring_domains': referring_domains, 'backlinks': backlinks,
    'organic_keywords': organic_keywords, 'brand_mentions': brand_mentions, 'media_mentions': media_mentions,
    'service_pages': service_pages, 'blog_articles': blog_articles, 'case_studies': case_studies,
    'faqs': faqs, 'content_quality': content_quality, 'technical_seo': technical_seo,
    'direct_answers': direct_answers, 'founders_visible': founders_visible, 'about_page': about_page,
    'author_bios': author_bios, 'testimonials': testimonials, 'certifications': certifications,
    'faq_schema': faq_schema, 'organization_schema': organization_schema, 'article_schema': article_schema,
    'person_schema': person_schema, 'manual_social_score': manual_social_score, 'manual_email_score': manual_email_score
}

business = {'monthly_sessions': monthly_sessions, 'visitor_to_lead': visitor_to_lead, 'lead_to_customer': lead_to_customer, 'avg_deal_value': avg_deal_value}

with st.expander("1. Cargar datos reales opcional", expanded=True):
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: gsc_file = st.file_uploader("Google Search Console CSV", type=["csv"])
    with c2: ga4_file = st.file_uploader("GA4 CSV", type=["csv"])
    with c3: linkedin_file = st.file_uploader("LinkedIn CSV", type=["csv"])
    with c4: social_file = st.file_uploader("Social Media CSV", type=["csv"])
    with c5: email_file = st.file_uploader("Email Marketing CSV", type=["csv"])
    st.info("No necesitas cargar todo. Si una plataforma no tiene data, el motor usa inputs manuales y baja el nivel de confianza.")

data_sources = []
warnings = []

gsc, w = parse_upload(gsc_file); warnings.append(('GSC', w)) if w else None
ga4, w = parse_upload(ga4_file); warnings.append(('GA4', w)) if w else None
linkedin, w = parse_upload(linkedin_file); warnings.append(('LinkedIn', w)) if w else None
social, w = parse_upload(social_file); warnings.append(('Social', w)) if w else None
email, w = parse_upload(email_file); warnings.append(('Email', w)) if w else None

for name, df in [('GSC', gsc), ('GA4', ga4), ('LinkedIn', linkedin), ('Social', social), ('Email', email)]:
    if df is not None and not df.empty:
        data_sources.append(name)

if warnings:
    st.warning("Algunos archivos tienen formato irregular. El motor intentó leerlos y usará inputs manuales cuando falten columnas: " + "; ".join([f"{n}: {w}" for n,w in warnings]))

metrics = extract_metrics(gsc, ga4, linkedin, social, email)
scores = compute_scores(inputs, metrics)
recs = get_recommendations(scores, metrics)

st.header("1. Executive Brief")
cols = st.columns(4)
summary_metrics = [('Trust Score', scores['trust']), ('Visibility Score', scores['visibility']), ('AI Search Readiness', scores['aeo']), ('Authority Score', scores['authority'])]
for col, (name, value) in zip(cols, summary_metrics):
    col.metric(name, f"{value}/100", label(value))

st.subheader("Qué significa esto")
for line in executive_brief(scores, metrics, data_sources):
    st.write("• " + line)

strongest, weakest = strongest_and_weakest(scores)
st.subheader("Diagnóstico principal")
st.write(f"**Cuello de botella actual:** {weakest.replace('_',' ').title()}.")
st.write(f"**Fortaleza actual:** {strongest.replace('_',' ').title()}.")

with st.expander("Ver cómo se calculan los scores", expanded=False):
    st.write("**Trust Score** = EEAT, Authority, Content, AEO/GEO, Social, Email y Technical SEO.")
    st.write("**Visibility Score** = Authority, Content, Technical SEO, AEO/GEO, Social y Email.")
    st.write("**Authority Score** no es igual a DR. Usa DR, referring domains, backlinks, brand mentions y menciones en medios.")
    breakdown = pd.DataFrame({
        'Factor': ['EEAT','Authority','Content','Technical SEO','AEO/GEO','Social','Email'],
        'Score': [scores['eeat'], scores['authority'], scores['content'], scores['technical_seo'], scores['aeo'], scores['social'], scores['email']]
    })
    fig = go.Figure(go.Bar(x=breakdown['Factor'], y=breakdown['Score']))
    fig.update_layout(yaxis_range=[0,100], height=360)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(breakdown, use_container_width=True)

st.header("2. Recomendaciones dinámicas")
st.write("Estas recomendaciones cambian según los datos cargados y los inputs manuales.")
if not recs:
    st.success("No se detectaron cuellos de botella críticos. Recomendación: mantener ejecución y medir evolución semanal.")
else:
    for i, r in enumerate(recs[:6], start=1):
        with st.container(border=True):
            st.subheader(f"Prioridad {i}: {r['title']}")
            st.write(f"**Por qué aparece:** {r['trigger']}.")
            st.write(r['why'])
            st.write("**Acciones inmediatas:**")
            for a in r['actions']:
                st.write("- " + a)
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Impacto", r['impact'])
            m2.metric("Esfuerzo", r['effort'])
            m3.metric("Tiempo", r['time_to_impact'])
            m4.metric("Confianza", r['confidence'])
            st.caption("Mejora: " + ", ".join(r['improves']))

st.header("3. Qué pasa si hago esto")
st.write("Mueve las acciones y la herramienta explica el posible impacto en visibilidad, confianza y negocio.")
sc1, sc2, sc3, sc4 = st.columns(4)
with sc1:
    sim_articles = st.slider("Artículos nuevos", 0, 20, 2)
    sim_pages = st.slider("Páginas actualizadas", 0, 20, 4)
with sc2:
    sim_faqs = st.slider("FAQs/direct answers", 0, 50, 8)
    sim_cases = st.slider("Casos nuevos", 0, 10, 1)
with sc3:
    sim_linkedin = st.slider("Posts LinkedIn/semana", 0, 10, 3)
    sim_newsletters = st.slider("Newsletters/mes", 0, 8, 2)
with sc4:
    sim_ref_domains = st.slider("Nuevos referring domains", 0, 50, 5)

actions = {'articles': sim_articles, 'pages': sim_pages, 'faqs': sim_faqs, 'case_studies': sim_cases, 'linkedin_posts': sim_linkedin, 'newsletters': sim_newsletters, 'referring_domains': sim_ref_domains}
projected, biz = simulate(scores, actions, business)

pcols = st.columns(5)
pcols[0].metric("Trust", f"{scores['trust']} → {projected['trust']}")
pcols[1].metric("Visibility", f"{scores['visibility']} → {projected['visibility']}")
pcols[2].metric("AI Search", f"{scores['aeo']} → {projected['aeo']}")
pcols[3].metric("Added leads", biz['added_leads'])
pcols[4].metric("Revenue estimado", f"${biz['projected_revenue']:,}")

st.subheader("Explicación del efecto")
for line in action_explanation(actions):
    st.write("• " + line)

st.header("4. Plan recomendado para los próximos 7 días")
plan = seven_day_plan(recs)
plan_df = pd.DataFrame(plan, columns=['Día', 'Acción recomendada'])
st.dataframe(plan_df, use_container_width=True, hide_index=True)

st.header("5. Export")
export_rows = []
for r in recs:
    export_rows.append({
        'recommendation': r['title'], 'trigger': r['trigger'], 'impact': r['impact'], 'effort': r['effort'], 'time_to_impact': r['time_to_impact'], 'why': r['why']
    })
export_df = pd.DataFrame(export_rows) if export_rows else pd.DataFrame([{'recommendation': 'No critical recommendations', 'trigger': '', 'impact': '', 'effort': '', 'time_to_impact': '', 'why': ''}])
st.download_button("Descargar recomendaciones CSV", data=export_df.to_csv(index=False).encode('utf-8'), file_name='tvip_recommendations.csv', mime='text/csv')

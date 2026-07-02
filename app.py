import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from parsers.csv_parsers import parse_upload, extract_metrics
from engines.scoring import compute_scores, label
from engines.diagnosis import executive_brief, strongest_and_weakest
from engines.recommendations import get_recommendations, seven_day_plan
from engines.simulation import simulate, action_explanation
from engines.content_analyzer import analyze_article, read_articles_csv, analyze_articles_dataframe

st.set_page_config(page_title="Trust & Visibility Intelligence Platform", layout="wide")

# ---------- helpers ----------
def status_text(score):
    if score >= 75:
        return "Fuerte"
    if score >= 55:
        return "En progreso"
    if score >= 40:
        return "Necesita atención"
    return "Prioridad inmediata"

def metric_card(col, title, value, note=""):
    col.metric(title, f"{int(value)}/100", status_text(value))
    if note:
        col.caption(note)

def simple_action_from_rec(rec):
    title = rec.get("title", "Acción recomendada")
    improves = ", ".join(rec.get("improves", [])[:3])
    actions = rec.get("actions", [])
    first_action = actions[0] if actions else title
    return {
        "Acción": first_action,
        "Mejora": improves or "Visibilidad",
        "Impacto": rec.get("impact", "Medio"),
        "Esfuerzo": rec.get("effort", "Medio"),
        "Cuándo se ve": rec.get("time_to_impact", "2 a 8 semanas"),
        "Por qué aparece": rec.get("trigger", "Detectado por los datos")
    }

def explain_if_action(action_key, value):
    if value <= 0:
        return None
    explanations = {
        "articles": f"Publicar {value} artículos puede aumentar cobertura temática, keywords potenciales y probabilidad de aparecer en respuestas de IA.",
        "pages": f"Actualizar {value} páginas ayuda a mejorar conversiones, claridad comercial y relevancia para Google.",
        "faqs": f"Agregar {value} FAQs/direct answers facilita que Google y motores de IA entiendan respuestas específicas.",
        "case_studies": f"Publicar {value} casos fortalece confianza, EEAT y conversión, aunque no siempre genere tráfico inmediato.",
        "linkedin_posts": f"Publicar {value} veces por semana en LinkedIn aumenta distribución, búsquedas de marca y presencia ejecutiva.",
        "newsletters": f"Enviar {value} newsletters al mes genera tráfico recurrente hacia el contenido y mejora engagement.",
        "referring_domains": f"Conseguir {value} nuevos referring domains aumenta señales externas de autoridad y puede apoyar rankings.",
    }
    return explanations.get(action_key)

# ---------- sidebar inputs ----------
with st.sidebar:
    st.header("Inputs del negocio")
    st.caption("Usa datos reales si los tienes. Si no, ingresa estimados manuales.")
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

st.title("Trust & Visibility Intelligence Platform 2.3")
st.caption("Visual first + acciones dinámicas + Article Analyzer BLUF")
st.write("La herramienta muestra primero dónde está el negocio y luego traduce los datos en acciones concretas.")

# ---------- uploads ----------
with st.expander("Cargar datos reales opcional", expanded=False):
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: gsc_file = st.file_uploader("Google Search Console CSV", type=["csv"])
    with c2: ga4_file = st.file_uploader("GA4 CSV", type=["csv"])
    with c3: linkedin_file = st.file_uploader("LinkedIn CSV", type=["csv"])
    with c4: social_file = st.file_uploader("Social Media CSV", type=["csv"])
    with c5: email_file = st.file_uploader("Email Marketing CSV", type=["csv"])
    st.info("No necesitas cargar todo. Si falta data, la app usa los inputs manuales y baja la confianza del diagnóstico.")

data_sources, warnings = [], []
gsc, w = parse_upload(gsc_file)
if w: warnings.append(('GSC', w))
ga4, w = parse_upload(ga4_file)
if w: warnings.append(('GA4', w))
linkedin, w = parse_upload(linkedin_file)
if w: warnings.append(('LinkedIn', w))
social, w = parse_upload(social_file)
if w: warnings.append(('Social', w))
email, w = parse_upload(email_file)
if w: warnings.append(('Email', w))

for name, df in [('GSC', gsc), ('GA4', ga4), ('LinkedIn', linkedin), ('Social', social), ('Email', email)]:
    if df is not None and not df.empty:
        data_sources.append(name)

metrics = extract_metrics(gsc, ga4, linkedin, social, email)
scores = compute_scores(inputs, metrics)
recs = get_recommendations(scores, metrics)
strongest, weakest = strongest_and_weakest(scores)

# ---------- VISUAL FIRST ----------
st.header("1. Estado visual del negocio")

m1, m2, m3, m4 = st.columns(4)
metric_card(m1, "Trust Score", scores['trust'], "Confianza que transmite la marca")
metric_card(m2, "Visibility Score", scores['visibility'], "Capacidad de ser encontrada")
metric_card(m3, "AI Search Readiness", scores['aeo'], "Preparación para respuestas de IA")
metric_card(m4, "Authority Score", scores['authority'], f"DR usado como input: {domain_rating}")

breakdown = pd.DataFrame({
    'Factor': ['EEAT','Authority','Content','Technical SEO','AEO/GEO','Social','Email'],
    'Score': [scores['eeat'], scores['authority'], scores['content'], scores['technical_seo'], scores['aeo'], scores['social'], scores['email']]
})

chart_col, story_col = st.columns([1.35, 1])
with chart_col:
    fig = go.Figure(go.Bar(x=breakdown['Factor'], y=breakdown['Score'], text=breakdown['Score'], textposition='outside'))
    fig.update_layout(yaxis_range=[0,100], height=390, margin=dict(l=20,r=20,t=40,b=20), title="Score breakdown")
    st.plotly_chart(fig, use_container_width=True)
with story_col:
    st.subheader("Lectura simple")
    weak_row = breakdown.sort_values('Score').iloc[0]
    strong_row = breakdown.sort_values('Score', ascending=False).iloc[0]
    st.write(f"**Mayor fortaleza:** {strong_row['Factor']} ({int(strong_row['Score'])}/100).")
    st.write(f"**Mayor limitación:** {weak_row['Factor']} ({int(weak_row['Score'])}/100).")
    if weak_row['Factor'] == 'Social':
        st.warning("La prioridad no es solo crear contenido. Falta distribución y presencia fuera del sitio.")
    elif weak_row['Factor'] == 'Authority':
        st.warning("El cuello de botella es autoridad: faltan señales externas como menciones, backlinks y partnerships.")
    elif weak_row['Factor'] == 'Content':
        st.warning("La oportunidad principal está en mejorar o ampliar contenido comercial y educativo.")
    elif weak_row['Factor'] == 'Email':
        st.warning("Hay oportunidad de activar mejor la base existente con newsletters y nurturing.")
    elif weak_row['Factor'] == 'AEO/GEO':
        st.warning("La marca necesita más respuestas directas, FAQs y estructura para AI Search.")
    else:
        st.warning("La prioridad está en corregir la base antes de acelerar distribución.")

    st.caption("Los scores no son promesas. Son una forma de priorizar qué hacer primero.")

st.subheader("Datos cargados")
s1, s2, s3, s4 = st.columns(4)
s1.metric("Fuentes cargadas", f"{len(data_sources)}/5")
s2.metric("Sesiones detectadas", f"{int(metrics.get('sessions', 0)):,}")
s3.metric("GSC clicks", f"{int(metrics.get('gsc_clicks', 0)):,}")
s4.metric("GSC impressions", f"{int(metrics.get('gsc_impressions', 0)):,}")
if warnings:
    st.info("Algunos CSV tienen formato irregular. La app usará lo que pueda leer y completará con inputs manuales: " + '; '.join([f'{n}: {w}' for n,w in warnings]))

# ---------- SIMPLE DYNAMIC RECOMMENDATIONS ----------
st.header("2. Acciones recomendadas")
st.write("Estas acciones cambian según los datos e inputs. Están escritas para ejecución, no como auditoría técnica.")

simple_recs = [simple_action_from_rec(r) for r in recs[:5]]
if simple_recs:
    rec_df = pd.DataFrame(simple_recs)
    st.dataframe(rec_df, use_container_width=True, hide_index=True)
else:
    st.success("No se detectó una limitación crítica. Mantén ejecución semanal y mide evolución.")

if recs:
    with st.expander("Ver explicación de cada recomendación", expanded=False):
        for i, r in enumerate(recs[:5], start=1):
            st.markdown(f"### {i}. {r['title']}")
            st.write(f"**Por qué aparece:** {r['trigger']}")
            st.write(r['why'])
            st.write("**Acciones inmediatas:**")
            for a in r.get('actions', [])[:3]:
                st.write("- " + a)
            st.caption("Mejora: " + ", ".join(r.get('improves', [])))

# ---------- SCENARIO SIMULATOR ----------
st.header("3. Qué pasaría si hago estas acciones")
st.write("Mueve los controles. La herramienta explica qué puede mejorar y muestra el impacto estimado en negocio.")

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

p1, p2, p3, p4, p5 = st.columns(5)
p1.metric("Trust", f"{scores['trust']} → {projected['trust']}")
p2.metric("Visibility", f"{scores['visibility']} → {projected['visibility']}")
p3.metric("AI Search", f"{scores['aeo']} → {projected['aeo']}")
p4.metric("Leads adicionales", biz['added_leads'])
p5.metric("Revenue estimado", f"${biz['projected_revenue']:,}")

explanations = [explain_if_action(k, v) for k, v in actions.items()]
explanations = [e for e in explanations if e]
with st.container(border=True):
    st.subheader("Explicación en lenguaje simple")
    for e in explanations:
        st.write("• " + e)

# ---------- PLAN ----------
st.header("4. Plan de 7 días")
plan = seven_day_plan(recs)
plan_df = pd.DataFrame(plan, columns=['Día', 'Acción recomendada'])
st.dataframe(plan_df, use_container_width=True, hide_index=True)


# ---------- ARTICLE ANALYZER ----------
st.header("5. Article Analyzer: BLUF + SEO/AEO")
st.write("Este módulo revisa si un artículo abre con la idea principal, si está estructurado para SEO/AEO y si ayuda a convertir.")

article_tabs = st.tabs(["Analizar un artículo", "Analizar CSV de artículos"] )

with article_tabs[0]:
    at1, at2 = st.columns([1, 1])
    with at1:
        article_title = st.text_input("Título del artículo", "")
        article_url = st.text_input("URL opcional", "")
    with at2:
        st.caption("Pega el contenido del artículo. Puede ser texto, HTML o markdown exportado de Webflow.")
    article_text = st.text_area("Contenido del artículo", height=260, placeholder="Pega aquí el artículo completo...")
    if article_text.strip():
        analysis = analyze_article(article_text, article_title, article_url)
        st.subheader("Resultado del artículo")
        a1, a2, a3, a4, a5, a6 = st.columns(6)
        a1.metric("Overall", f"{analysis['overall']}/100")
        a2.metric("BLUF", f"{analysis['bluf']}/100")
        a3.metric("SEO", f"{analysis['seo']}/100")
        a4.metric("AEO/GEO", f"{analysis['aeo']}/100")
        a5.metric("Trust", f"{analysis['trust']}/100")
        a6.metric("Conversión", f"{analysis['conversion']}/100")

        article_breakdown = pd.DataFrame({
            'Factor': ['BLUF','Estructura','SEO','AEO/GEO','Trust','Conversión'],
            'Score': [analysis['bluf'], analysis['structure'], analysis['seo'], analysis['aeo'], analysis['trust'], analysis['conversion']]
        })
        fig_article = go.Figure(go.Bar(x=article_breakdown['Factor'], y=article_breakdown['Score'], text=article_breakdown['Score'], textposition='outside'))
        fig_article.update_layout(yaxis_range=[0,100], height=330, margin=dict(l=20,r=20,t=30,b=20))
        st.plotly_chart(fig_article, use_container_width=True)

        col_left, col_right = st.columns(2)
        with col_left:
            st.markdown("### Lectura simple")
            if analysis['bluf'] < 70:
                st.warning("El artículo tarda en llegar a la idea principal. Conviene abrir con una conclusión clara en las primeras líneas.")
            else:
                st.success("El artículo tiene una apertura relativamente clara y orientada a BLUF.")
            st.write(f"Palabras: **{analysis['word_count']}** | Subtítulos detectados: **{analysis['headings']}** | Promedio palabras/párrafo: **{analysis['avg_paragraph_words']}**")
            with st.expander("Notas BLUF", expanded=False):
                for note in analysis['bluf_notes']:
                    st.write("• " + note)
        with col_right:
            st.markdown("### Acciones recomendadas")
            for action in analysis['actions']:
                st.write("• " + action)

with article_tabs[1]:
    articles_file = st.file_uploader("CSV de artículos", type=["csv"], key="articles_csv")
    st.caption("Columnas ideales: title, url, content. También intenta detectar body, text, article, contenido o description.")
    if articles_file is not None:
        df_articles = read_articles_csv(articles_file)
        batch_results, missing_cols = analyze_articles_dataframe(df_articles)
        if missing_cols:
            st.error("No encontré una columna de contenido. Columnas detectadas: " + ", ".join(missing_cols))
        else:
            st.subheader("Resumen de artículos")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Artículos analizados", len(batch_results))
            c2.metric("BLUF promedio", int(batch_results['BLUF'].mean()))
            c3.metric("AEO/GEO promedio", int(batch_results['AEO/GEO'].mean()))
            c4.metric("Conversión promedio", int(batch_results['Conversion'].mean()))
            fig_batch = go.Figure(go.Bar(x=['Overall','BLUF','SEO','AEO/GEO','Trust','Conversion'], y=[batch_results['Overall'].mean(), batch_results['BLUF'].mean(), batch_results['SEO'].mean(), batch_results['AEO/GEO'].mean(), batch_results['Trust'].mean(), batch_results['Conversion'].mean()]))
            fig_batch.update_layout(yaxis_range=[0,100], height=330, margin=dict(l=20,r=20,t=30,b=20), title="Promedios del contenido")
            st.plotly_chart(fig_batch, use_container_width=True)
            st.dataframe(batch_results.sort_values('Overall'), use_container_width=True, hide_index=True)
            st.download_button("Descargar análisis de artículos CSV", data=batch_results.to_csv(index=False).encode('utf-8'), file_name='article_bluf_analysis.csv', mime='text/csv')

# ---------- TECH DETAILS BELOW ----------
with st.expander("Detalles técnicos y fórmula de scores", expanded=False):
    st.write("**Authority Score** no es igual a DR. Combina DR, referring domains, backlinks, brand mentions y menciones en medios.")
    st.write("**Trust Score** combina EEAT, Authority, Content, AEO/GEO, Social, Email y Technical SEO.")
    st.write("**Visibility Score** combina Authority, Content, Technical SEO, AEO/GEO, Social y Email.")
    st.dataframe(breakdown, use_container_width=True, hide_index=True)

st.header("6. Export")
export_rows = []
for r in recs:
    export_rows.append({
        'recommendation': r['title'], 'trigger': r['trigger'], 'impact': r['impact'], 'effort': r['effort'], 'time_to_impact': r['time_to_impact'], 'why': r['why']
    })
export_df = pd.DataFrame(export_rows) if export_rows else pd.DataFrame([{'recommendation': 'No critical recommendations', 'trigger': '', 'impact': '', 'effort': '', 'time_to_impact': '', 'why': ''}])
st.download_button("Descargar recomendaciones CSV", data=export_df.to_csv(index=False).encode('utf-8'), file_name='tvip_recommendations.csv', mime='text/csv')

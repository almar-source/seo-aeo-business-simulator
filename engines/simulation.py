from engines.scoring import clamp

def simulate(scores, actions, business):
    articles = actions.get('articles', 0)
    pages = actions.get('pages', 0)
    faqs = actions.get('faqs', 0)
    linkedin = actions.get('linkedin_posts', 0)
    newsletters = actions.get('newsletters', 0)
    cases = actions.get('case_studies', 0)
    referring = actions.get('referring_domains', 0)

    projected = dict(scores)
    projected['content'] = round(clamp(scores['content'] + articles*2.2 + pages*2.5 + cases*1.5))
    projected['aeo'] = round(clamp(scores['aeo'] + faqs*1.8 + pages*.8 + articles*.7))
    projected['social'] = round(clamp(scores['social'] + linkedin*3.5))
    projected['email'] = round(clamp(scores['email'] + newsletters*4))
    projected['authority'] = round(clamp(scores['authority'] + referring*0.75 + cases*.7))
    projected['eeat'] = round(clamp(scores['eeat'] + cases*2.5 + pages*.5))
    projected['trust'] = round(clamp(projected['eeat']*.25 + projected['authority']*.22 + projected['content']*.2 + projected['aeo']*.15 + projected['social']*.08 + projected['email']*.05 + scores['technical_seo']*.05))
    projected['visibility'] = round(clamp(projected['authority']*.25 + projected['content']*.2 + scores['technical_seo']*.15 + projected['aeo']*.2 + projected['social']*.12 + projected['email']*.08))

    visibility_lift = max(0, projected['visibility'] - scores['visibility'])
    sessions_base = business.get('monthly_sessions', 1000)
    lead_rate = business.get('visitor_to_lead', 1.0) / 100
    close_rate = business.get('lead_to_customer', 10.0) / 100
    avg_deal = business.get('avg_deal_value', 10000)
    added_sessions = round(sessions_base * (visibility_lift / 100) * 0.65)
    added_leads = added_sessions * lead_rate
    added_customers = added_leads * close_rate
    revenue = added_customers * avg_deal
    return projected, {
        'visibility_lift': round(visibility_lift),
        'added_sessions': round(added_sessions),
        'added_leads': round(added_leads, 1),
        'added_customers': round(added_customers, 2),
        'projected_revenue': round(revenue)
    }

def action_explanation(actions):
    lines = []
    if actions.get('articles',0):
        lines.append(f"Publicar {actions['articles']} artículos aumenta cobertura temática, keywords potenciales y probabilidad de aparecer en AI Search. El efecto suele verse en 4 a 8 semanas.")
    if actions.get('pages',0):
        lines.append(f"Actualizar {actions['pages']} páginas comerciales mejora intención de búsqueda, CTAs, confianza y conversión.")
    if actions.get('faqs',0):
        lines.append(f"Agregar {actions['faqs']} bloques FAQ/direct answers ayuda a que Google y motores de IA entiendan y citen respuestas concretas.")
    if actions.get('linkedin_posts',0):
        lines.append(f"Publicar {actions['linkedin_posts']} veces en LinkedIn no mejora SEO directamente, pero aumenta presencia ejecutiva, búsquedas de marca y tráfico referido.")
    if actions.get('newsletters',0):
        lines.append(f"Enviar {actions['newsletters']} newsletters lleva tráfico a contenido estratégico y puede acelerar leads desde audiencias existentes.")
    if actions.get('referring_domains',0):
        lines.append(f"Conseguir {actions['referring_domains']} referring domains fortalece autoridad externa, que suele ser clave cuando el DR es bajo.")
    if actions.get('case_studies',0):
        lines.append(f"Publicar {actions['case_studies']} casos mejora trust, EEAT y conversión, aunque no siempre genere tráfico inmediato.")
    return lines

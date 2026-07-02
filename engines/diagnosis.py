from engines.scoring import label

def strongest_and_weakest(scores):
    keys = ['authority','content','technical_seo','eeat','aeo','social','email']
    vals = {k: scores.get(k,0) for k in keys}
    weakest = min(vals, key=vals.get)
    strongest = max(vals, key=vals.get)
    return strongest, weakest

def executive_brief(scores, metrics, data_sources):
    strongest, weakest = strongest_and_weakest(scores)
    trust = scores['trust']; visibility = scores['visibility']; aeo = scores['aeo']
    lines = []
    lines.append(f"Trust está en nivel {label(trust).lower()} y Visibility está en nivel {label(visibility).lower()}.")
    lines.append(f"La señal más fuerte ahora es {strongest.replace('_',' ').title()} ({scores[strongest]}/100).")
    lines.append(f"La principal limitación es {weakest.replace('_',' ').title()} ({scores[weakest]}/100).")
    if scores['authority'] < 45 and scores['content'] >= 55:
        lines.append("No recomendamos crear contenido en volumen antes de fortalecer autoridad. El sitio puede tener contenido útil, pero necesita más señales externas para ganar visibilidad.")
    elif scores['content'] < 50:
        lines.append("La prioridad es mejorar cobertura temática y páginas comerciales. Hoy faltan suficientes respuestas, casos o páginas que conecten la demanda con el negocio.")
    if aeo < 55:
        lines.append("AI Search Readiness todavía necesita trabajo. FAQs, schema y respuestas directas pueden aumentar la probabilidad de aparecer en motores de IA.")
    if metrics.get('conversion_rate',0) and metrics.get('conversion_rate',0) < 1:
        lines.append("Hay señales de baja conversión. Antes de buscar más tráfico, conviene revisar CTAs, formularios, casos y páginas de servicio.")
    if len(data_sources) < 3:
        lines.append("Nivel de confianza: medio/bajo, porque faltan fuentes reales. La herramienta usa inputs manuales cuando no hay CSV cargado.")
    else:
        lines.append("Nivel de confianza: mayor, porque hay varias fuentes reales cargadas.")
    return lines

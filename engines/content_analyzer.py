import re
import pandas as pd

QUESTION_WORDS = [
    'what', 'why', 'how', 'when', 'where', 'who', 'which',
    'qué', 'por qué', 'como', 'cómo', 'cuándo', 'dónde', 'quién', 'cuál'
]
CTA_WORDS = [
    'contact', 'schedule', 'book', 'download', 'subscribe', 'learn more', 'request',
    'contacto', 'agenda', 'descarga', 'suscríbete', 'conoce más', 'solicita', 'hablemos'
]
BLUF_SIGNALS = [
    'bottom line', 'in short', 'key takeaway', 'the main point', 'summary', 'executive summary',
    'en resumen', 'la idea principal', 'lo más importante', 'conclusión', 'punto clave'
]


def clean_text(text):
    if text is None:
        return ''
    text = str(text)
    text = re.sub(r'<script.*?</script>', ' ', text, flags=re.I | re.S)
    text = re.sub(r'<style.*?</style>', ' ', text, flags=re.I | re.S)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def split_paragraphs(raw):
    raw = '' if raw is None else str(raw)
    parts = re.split(r'\n\s*\n|</p>|<br\s*/?>', raw, flags=re.I)
    cleaned = [clean_text(p) for p in parts]
    return [p for p in cleaned if len(p) > 20]


def word_count(text):
    return len(re.findall(r"\b[\wáéíóúñüÁÉÍÓÚÑÜ'-]+\b", clean_text(text)))


def count_headings(raw):
    raw = '' if raw is None else str(raw)
    html_h = len(re.findall(r'<h[2-3][^>]*>', raw, flags=re.I))
    md_h = len(re.findall(r'^\s*#{2,3}\s+', raw, flags=re.M))
    return html_h + md_h


def has_faq(raw):
    text = clean_text(raw).lower()
    q_marks = text.count('?') + text.count('¿')
    faq_words = any(x in text for x in ['faq', 'frequently asked', 'preguntas frecuentes'])
    question_words = sum(1 for w in QUESTION_WORDS if w in text)
    return faq_words or q_marks >= 3 or question_words >= 5


def has_cta(text):
    lower = clean_text(text).lower()
    return any(w in lower for w in CTA_WORDS)


def has_bibliographic_trust(text):
    lower = clean_text(text).lower()
    return any(w in lower for w in ['source:', 'sources:', 'according to', 'report', 'study', 'research', 'fuente:', 'según', 'estudio', 'reporte'])


def calculate_bluf(raw):
    text = clean_text(raw)
    wc = word_count(text)
    first_80 = ' '.join(text.split()[:80]).lower()
    first_150 = ' '.join(text.split()[:150]).lower()
    first_para = split_paragraphs(raw)[0] if split_paragraphs(raw) else first_150

    score = 0
    notes = []

    if wc == 0:
        return 0, ['No hay texto suficiente para evaluar BLUF.']

    if len(first_para.split()) <= 80:
        score += 20
        notes.append('El primer bloque es corto y fácil de leer.')
    else:
        notes.append('El primer bloque es largo. Conviene abrir con una conclusión breve.')

    if any(s in first_150 for s in BLUF_SIGNALS):
        score += 25
        notes.append('Incluye una señal clara de resumen o conclusión al inicio.')
    else:
        notes.append('No se detecta una frase tipo resumen ejecutivo o conclusión al inicio.')

    if any(v in first_80 for v in ['should', 'need', 'must', 'recommend', 'means', 'is that', 'debería', 'necesita', 'recomendamos', 'significa', 'es que']):
        score += 20
        notes.append('La introducción parece presentar una postura o recomendación.')
    else:
        notes.append('La introducción podría ser más directa sobre la recomendación principal.')

    if '?' in first_150 or '¿' in first_150:
        score += 10
        notes.append('El inicio plantea una pregunta que puede guiar la respuesta.')

    if wc >= 500:
        score += 10
    if count_headings(raw) >= 3:
        score += 15
        notes.append('La estructura con subtítulos ayuda a escanear el contenido.')
    else:
        notes.append('Faltan subtítulos H2/H3 para hacer el contenido más escaneable.')

    return min(100, score), notes


def analyze_article(raw_text, title='', url=''):
    raw_text = '' if raw_text is None else str(raw_text)
    text = clean_text(raw_text)
    wc = word_count(text)
    headings = count_headings(raw_text)
    paragraphs = split_paragraphs(raw_text)
    avg_para_words = int(sum(len(p.split()) for p in paragraphs) / max(1, len(paragraphs)))
    links = len(re.findall(r'https?://|href=', raw_text, flags=re.I))

    bluf_score, bluf_notes = calculate_bluf(raw_text)

    structure_score = 0
    if wc >= 700: structure_score += 20
    if headings >= 3: structure_score += 25
    if avg_para_words <= 90: structure_score += 20
    if has_faq(raw_text): structure_score += 20
    if links >= 2: structure_score += 15
    structure_score = min(100, structure_score)

    seo_score = 0
    title_len = len(str(title or '').strip())
    if 35 <= title_len <= 70: seo_score += 25
    elif title_len > 0: seo_score += 12
    if wc >= 900: seo_score += 25
    elif wc >= 500: seo_score += 15
    if headings >= 3: seo_score += 20
    if links >= 2: seo_score += 15
    if has_faq(raw_text): seo_score += 15
    seo_score = min(100, seo_score)

    aeo_score = 0
    if bluf_score >= 70: aeo_score += 25
    if has_faq(raw_text): aeo_score += 30
    if '?' in text or '¿' in text: aeo_score += 10
    if headings >= 4: aeo_score += 15
    if any(x in text.lower() for x in ['definition', 'means', 'how to', 'qué es', 'significa', 'cómo']): aeo_score += 20
    aeo_score = min(100, aeo_score)

    trust_score = 0
    if has_bibliographic_trust(raw_text): trust_score += 25
    if links >= 2: trust_score += 20
    if any(x in text.lower() for x in ['case study', 'example', 'client', 'testimonial', 'caso', 'ejemplo', 'cliente', 'testimonio']): trust_score += 25
    if any(x in text.lower() for x in ['author', 'by ', 'written by', 'autor', 'escrito por']): trust_score += 15
    if wc >= 900: trust_score += 15
    trust_score = min(100, trust_score)

    conversion_score = 0
    if has_cta(raw_text): conversion_score += 35
    if any(x in text.lower() for x in ['service', 'solution', 'product', 'servicio', 'solución']): conversion_score += 20
    if any(x in text.lower() for x in ['case study', 'client', 'testimonial', 'caso', 'cliente', 'testimonio']): conversion_score += 25
    if links >= 2: conversion_score += 20
    conversion_score = min(100, conversion_score)

    overall = int(round((bluf_score * .25) + (structure_score * .15) + (seo_score * .2) + (aeo_score * .2) + (trust_score * .1) + (conversion_score * .1)))

    actions = []
    if bluf_score < 70:
        actions.append('Agregar un BLUF al inicio: 2 o 3 líneas con la conclusión principal.')
    if headings < 3:
        actions.append('Agregar H2/H3 claros para que el artículo sea escaneable.')
    if not has_faq(raw_text):
        actions.append('Agregar 3 a 5 FAQs o respuestas directas para mejorar AEO/GEO.')
    if not has_cta(raw_text):
        actions.append('Agregar un CTA hacia servicio, contacto, descarga o newsletter.')
    if links < 2:
        actions.append('Agregar enlaces internos a páginas de servicio y artículos relacionados.')
    if trust_score < 50:
        actions.append('Agregar ejemplos, fuentes, datos, autor o señales de confianza.')
    if not actions:
        actions.append('El artículo tiene una base sólida. La prioridad sería actualizarlo con datos recientes y distribuirlo.')

    return {
        'title': title or 'Artículo sin título',
        'url': url or '',
        'word_count': wc,
        'headings': headings,
        'avg_paragraph_words': avg_para_words,
        'overall': overall,
        'bluf': int(bluf_score),
        'structure': int(structure_score),
        'seo': int(seo_score),
        'aeo': int(aeo_score),
        'trust': int(trust_score),
        'conversion': int(conversion_score),
        'actions': actions[:5],
        'bluf_notes': bluf_notes[:4]
    }


def read_articles_csv(uploaded_file):
    if uploaded_file is None:
        return pd.DataFrame()
    try:
        df = pd.read_csv(uploaded_file)
    except Exception:
        uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file, encoding='latin-1')
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df


def analyze_articles_dataframe(df):
    if df is None or df.empty:
        return pd.DataFrame(), []
    title_col = next((c for c in df.columns if c in ['title','name','post title','titulo','título']), None)
    url_col = next((c for c in df.columns if c in ['url','link','slug','page']), None)
    content_col = next((c for c in df.columns if c in ['content','body','text','article','post body','contenido','copy','description']), None)
    if content_col is None:
        return pd.DataFrame(), list(df.columns)
    rows = []
    for _, row in df.head(200).iterrows():
        result = analyze_article(row.get(content_col, ''), title=row.get(title_col, '') if title_col else '', url=row.get(url_col, '') if url_col else '')
        rows.append({
            'Title': result['title'],
            'URL': result['url'],
            'Overall': result['overall'],
            'BLUF': result['bluf'],
            'SEO': result['seo'],
            'AEO/GEO': result['aeo'],
            'Trust': result['trust'],
            'Conversion': result['conversion'],
            'Words': result['word_count'],
            'Top action': result['actions'][0]
        })
    return pd.DataFrame(rows), []

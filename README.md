# Trust & Visibility Intelligence Platform 2.3

Versión modular con dashboard visual, recomendaciones dinámicas y nuevo módulo **Article Analyzer / BLUF Checker**.

## Incluye
- Trust Score, Visibility Score, AI Search Readiness y Authority Score.
- Recomendaciones simples que cambian según los datos.
- Simulador de acciones: artículos, páginas, FAQs, LinkedIn, email y referring domains.
- Plan de 7 días.
- Carga opcional de GSC, GA4, LinkedIn, Social Media y Email.
- Nuevo módulo para analizar artículos por:
  - BLUF
  - estructura
  - SEO
  - AEO/GEO
  - trust
  - conversión
- Análisis individual pegando texto.
- Análisis masivo subiendo CSV de artículos.

## CSV de artículos recomendado
Columnas ideales:
- `title`
- `url`
- `content`

También intenta detectar: `body`, `text`, `article`, `contenido`, `description`.

## Deploy
Sube todo a GitHub en la raíz:
- `app.py`
- `requirements.txt`
- `engines/`
- `parsers/`
- `knowledge/`
- `modules/`

Luego reinicia Streamlit.

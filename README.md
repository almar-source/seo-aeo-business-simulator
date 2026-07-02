# SEO + AEO/GEO + Business Impact Simulator v3

Simulador en Streamlit para proyectar impacto SEO, AEO/GEO, contenido, email marketing y negocio.

## Qué incluye

- Carga de CSV de Google Search Console
- Carga de CSV de GA4
- Carga de CSV de YouTube Analytics
- Carga de CSV de Email Marketing
- Simulación de cambios de contenido:
  - páginas actualizadas
  - nuevas páginas/artículos
  - FAQs/direct answers
  - casos/testimonios
  - links internos
  - mejoras en title/meta
  - cobertura temática
  - pruebas/E-E-A-T
- Simulación de email:
  - tamaño de lista
  - campañas por mes
  - open rate
  - click rate
  - mejoras por asunto, CTA, segmentación y relevancia
- Proyección de:
  - ranking promedio
  - CTR
  - sesiones
  - leads
  - oportunidades
  - clientes
  - revenue mensual incremental
- Export de reporte CSV

## Instalación local

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy en Streamlit

Sube estos archivos al repositorio de GitHub conectado a Streamlit:

- `app.py`
- `requirements.txt`
- `README.md`

Streamlit hará redeploy automático.

## Nota

No usa OpenAI API ni consume tokens. Las proyecciones son heurísticas para planificación, priorización y explicación de impacto de negocio.

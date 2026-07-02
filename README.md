# Trust & Visibility Intelligence Platform v6

App de Streamlit para explicar cómo acciones de contenido, SEO, AEO/GEO, LinkedIn, social media y email pueden impactar visibilidad, confianza y negocio.

## Cómo correr localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Cómo subir a Streamlit Cloud

1. Sube `app.py`, `requirements.txt` y `README.md` a la raíz del repositorio de GitHub.
2. En Streamlit Cloud, selecciona el repo y `app.py` como main file.
3. Haz Reboot app.

## Datos soportados

Puedes usar inputs manuales o subir CSVs de:

- Google Search Console
- GA4
- LinkedIn Analytics
- Social Media
- Email Marketing

La app usa lector robusto para CSVs con separadores y encabezados irregulares.

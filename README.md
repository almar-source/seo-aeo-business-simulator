# SEO + AEO/GEO + Business Impact Simulator v4

Versión v4 con:

- Google Search Console CSV
- GA4 CSV con lector robusto para exports irregulares
- YouTube Analytics CSV
- Email marketing CSV
- Ahrefs CSV
- Trust Score
- Proyección SEO, AEO/GEO, contenido, email y revenue

## Cómo correr localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Cómo subir Ahrefs

Exporta uno o varios reportes desde Ahrefs en CSV y súbelos en el campo `Ahrefs CSV`.

Reportes recomendados:

1. Site Explorer > Overview > Export CSV
2. Site Explorer > Backlinks > Export CSV
3. Site Explorer > Referring domains > Export CSV
4. Site Explorer > Top pages > Export CSV
5. Site Explorer > Organic keywords > Export CSV

El simulador intenta detectar columnas como:

- Domain Rating / DR
- URL Rating / UR
- Referring domains
- Backlinks
- Dofollow
- Organic traffic
- Anchor text
- Target URL

Si tienes varios exports, súbelos uno por uno y usa el que mejor represente la métrica que quieres analizar.

## Trust Score

El Trust Score combina señales de:

- Content Quality
- Authority
- AEO/GEO Readiness
- Proof signals
- Case studies
- Entity clarity
- LinkedIn / executive visibility

No es una métrica oficial de Google. Es un índice propio para priorizar acciones de confianza, autoridad y conversión.

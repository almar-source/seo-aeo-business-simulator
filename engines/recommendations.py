import json
from pathlib import Path

RULES_PATH = Path(__file__).resolve().parents[1] / 'knowledge' / 'recommendation_rules.json'

def _load_rules():
    with open(RULES_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def _matches(value, operator, threshold):
    if operator == '<': return value < threshold
    if operator == '<=': return value <= threshold
    if operator == '>': return value > threshold
    if operator == '>=': return value >= threshold
    return False

def build_context(scores, metrics):
    ctx = dict(scores)
    ctx.update(metrics)
    return ctx

def get_recommendations(scores, metrics):
    rules = _load_rules()
    ctx = build_context(scores, metrics)
    recs = []
    for rule in rules:
        metric = rule.get('condition_metric')
        value = ctx.get(metric, 0)
        if _matches(value, rule.get('operator'), rule.get('threshold')):
            recs.append(rule)
    impact_order = {'Muy alto': 0, 'Alto': 1, 'Medio': 2, 'Bajo': 3}
    recs.sort(key=lambda r: impact_order.get(r.get('impact'), 9))
    return recs

def seven_day_plan(recs):
    default = [
        ('Lunes', 'Revisar datos cargados y confirmar el principal cuello de botella.'),
        ('Martes', 'Actualizar una página comercial prioritaria con FAQs, CTA y prueba social.'),
        ('Miércoles', 'Publicar un post de LinkedIn derivado del contenido principal.'),
        ('Jueves', 'Optimizar titles/metas o respuestas directas en páginas clave.'),
        ('Viernes', 'Enviar newsletter o distribución social hacia la página optimizada.'),
        ('Sábado', 'Buscar 3 oportunidades de menciones, partners o backlinks.'),
        ('Domingo', 'Medir cambios iniciales y ajustar prioridades para la semana siguiente.')
    ]
    if not recs:
        return default
    actions = []
    for r in recs[:4]:
        for a in r.get('actions', [])[:2]:
            actions.append((r['title'], a, r['impact']))
    days = ['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo']
    plan = []
    for i, day in enumerate(days):
        if i < len(actions):
            title, action, impact = actions[i]
            plan.append((day, f"{action} ({title}, impacto {impact.lower()})."))
        else:
            plan.append(default[i])
    return plan

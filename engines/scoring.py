import math

def clamp(x, lo=0, hi=100):
    return max(lo, min(hi, float(x)))

def scale_log(value, max_ref):
    value = max(0, float(value or 0))
    if value <= 0:
        return 0
    return clamp(math.log1p(value) / math.log1p(max_ref) * 100)

def compute_scores(inputs, metrics):
    dr = inputs.get('domain_rating', 0)
    rd = inputs.get('referring_domains', 0)
    backlinks = inputs.get('backlinks', 0)
    mentions = inputs.get('brand_mentions', 0)
    media = inputs.get('media_mentions', 0)

    authority = clamp(dr * 0.45 + scale_log(rd, 500) * 0.25 + scale_log(backlinks, 5000) * 0.1 + scale_log(mentions, 50) * 0.1 + scale_log(media, 25) * 0.1)

    service_pages = inputs.get('service_pages', 0)
    blog_articles = inputs.get('blog_articles', 0)
    case_studies = inputs.get('case_studies', 0)
    faqs = inputs.get('faqs', 0)
    content = clamp(scale_log(service_pages, 20)*.25 + scale_log(blog_articles, 120)*.25 + scale_log(case_studies, 20)*.2 + scale_log(faqs, 80)*.2 + inputs.get('content_quality', 50)*.1)

    tech = clamp(inputs.get('technical_seo', 60))
    eeat = clamp((20 if inputs.get('founders_visible') else 0) + (15 if inputs.get('about_page') else 0) + (15 if inputs.get('author_bios') else 0) + scale_log(case_studies, 20)*.25 + (15 if inputs.get('testimonials') else 0) + (10 if inputs.get('certifications') else 0))

    aeo = clamp((20 if inputs.get('faq_schema') else 0) + (20 if inputs.get('organization_schema') else 0) + (15 if inputs.get('article_schema') else 0) + (15 if inputs.get('person_schema') else 0) + scale_log(faqs, 80)*.2 + inputs.get('direct_answers', 40)*.1)

    social = clamp(scale_log(metrics.get('linkedin_impressions', 0) + metrics.get('social_impressions', 0), 100000) * .55 + scale_log(metrics.get('linkedin_clicks', 0), 5000) * .25 + metrics.get('linkedin_engagement', 0) * 5)
    if social == 0:
        social = inputs.get('manual_social_score', 10)

    email = clamp(metrics.get('email_open_rate', 0)*1.3 + metrics.get('email_click_rate', 0)*8)
    if email == 0:
        email = inputs.get('manual_email_score', 20)

    trust = clamp(eeat*.25 + authority*.22 + content*.2 + aeo*.15 + social*.08 + email*.05 + tech*.05)
    visibility = clamp(authority*.25 + content*.2 + tech*.15 + aeo*.2 + social*.12 + email*.08)

    return {
        'authority': round(authority), 'content': round(content), 'technical_seo': round(tech),
        'eeat': round(eeat), 'aeo': round(aeo), 'social': round(social), 'email': round(email),
        'trust': round(trust), 'visibility': round(visibility),
        'conversion_rate': round(metrics.get('conversion_rate', 0), 2)
    }

def label(score):
    if score >= 75: return 'Fuerte'
    if score >= 55: return 'Medio'
    if score >= 40: return 'Bajo'
    return 'Crítico'

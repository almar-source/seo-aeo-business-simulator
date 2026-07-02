import io
import pandas as pd


def _read_any_csv(uploaded_file):
    if uploaded_file is None:
        return None, None
    try:
        uploaded_file.seek(0)
        return pd.read_csv(uploaded_file), None
    except Exception:
        pass
    try:
        uploaded_file.seek(0)
        raw = uploaded_file.read()
        if isinstance(raw, bytes):
            text = raw.decode('utf-8', errors='ignore')
        else:
            text = str(raw)
        lines = [line for line in text.splitlines() if line.strip()]
        # Find the first line that looks like a header row
        header_idx = 0
        for i, line in enumerate(lines[:50]):
            lower = line.lower()
            if any(k in lower for k in ['session', 'click', 'impression', 'query', 'page', 'users', 'opens', 'followers']):
                header_idx = i
                break
        cleaned = '\n'.join(lines[header_idx:])
        return pd.read_csv(io.StringIO(cleaned), engine='python', on_bad_lines='skip'), 'Irregular CSV read as raw table'
    except Exception as e:
        return None, str(e)


def normalize_columns(df):
    if df is None:
        return None
    df = df.copy()
    df.columns = [str(c).strip().lower().replace(' ', '_').replace('-', '_') for c in df.columns]
    return df


def parse_upload(uploaded_file):
    df, warning = _read_any_csv(uploaded_file)
    return normalize_columns(df), warning


def safe_sum(df, candidates):
    if df is None or df.empty:
        return 0
    for c in candidates:
        if c in df.columns:
            return float(pd.to_numeric(df[c], errors='coerce').fillna(0).sum())
    return 0


def safe_mean(df, candidates):
    if df is None or df.empty:
        return 0
    for c in candidates:
        if c in df.columns:
            vals = pd.to_numeric(df[c].astype(str).str.replace('%','', regex=False), errors='coerce').dropna()
            if len(vals):
                return float(vals.mean())
    return 0


def extract_metrics(gsc=None, ga4=None, linkedin=None, social=None, email=None):
    metrics = {}
    metrics['gsc_clicks'] = safe_sum(gsc, ['clicks', 'click'])
    metrics['gsc_impressions'] = safe_sum(gsc, ['impressions', 'impression'])
    metrics['gsc_ctr'] = safe_mean(gsc, ['ctr'])
    metrics['gsc_position'] = safe_mean(gsc, ['position', 'avg_position', 'average_position'])

    metrics['sessions'] = safe_sum(ga4, ['sessions', 'session_start', 'total_users', 'users', 'active_users'])
    metrics['conversions'] = safe_sum(ga4, ['conversions', 'key_events', 'events', 'form_submits'])
    metrics['engagement_rate'] = safe_mean(ga4, ['engagement_rate', 'engaged_sessions'])

    metrics['linkedin_impressions'] = safe_sum(linkedin, ['impressions', 'impression'])
    metrics['linkedin_clicks'] = safe_sum(linkedin, ['clicks', 'click'])
    metrics['linkedin_engagement'] = safe_mean(linkedin, ['engagement_rate', 'engagement'])

    metrics['social_impressions'] = safe_sum(social, ['impressions', 'reach', 'views'])
    metrics['social_engagement'] = safe_mean(social, ['engagement_rate', 'engagement'])

    metrics['email_sent'] = safe_sum(email, ['sent', 'delivered', 'recipients'])
    metrics['email_opens'] = safe_sum(email, ['opens', 'open'])
    metrics['email_clicks'] = safe_sum(email, ['clicks', 'click'])
    if metrics['email_sent']:
        metrics['email_open_rate'] = metrics['email_opens'] / metrics['email_sent'] * 100
        metrics['email_click_rate'] = metrics['email_clicks'] / metrics['email_sent'] * 100
    else:
        metrics['email_open_rate'] = 0
        metrics['email_click_rate'] = 0

    if metrics['sessions']:
        metrics['conversion_rate'] = metrics['conversions'] / metrics['sessions'] * 100
    else:
        metrics['conversion_rate'] = 0
    return metrics

import io
import re
import pandas as pd


def _to_text(uploaded_file):
    if uploaded_file is None:
        return ""
    try:
        uploaded_file.seek(0)
        raw = uploaded_file.read()
        if isinstance(raw, bytes):
            return raw.decode('utf-8-sig', errors='ignore')
        return str(raw)
    except Exception:
        return ""


def _read_any_csv(uploaded_file):
    if uploaded_file is None:
        return None, None
    text = _to_text(uploaded_file)
    try:
        uploaded_file.seek(0)
        df = pd.read_csv(io.StringIO(text), engine='python', on_bad_lines='skip')
        df.attrs['raw_text'] = text
        return df, None
    except Exception:
        pass
    try:
        lines = [line for line in text.splitlines() if line.strip()]
        header_idx = 0
        for i, line in enumerate(lines[:80]):
            lower = line.lower()
            if any(k in lower for k in ['session', 'click', 'impression', 'query', 'page', 'users', 'opens', 'followers', 'active users']):
                header_idx = i
                break
        cleaned = '\n'.join(lines[header_idx:])
        df = pd.read_csv(io.StringIO(cleaned), engine='python', on_bad_lines='skip')
        df.attrs['raw_text'] = text
        return df, 'loaded_partial'
    except Exception as e:
        df = pd.DataFrame()
        df.attrs['raw_text'] = text
        return df, f'raw_only: {e}'


def normalize_columns(df):
    if df is None:
        return None
    df = df.copy()
    df.columns = [str(c).strip().lower().replace(' ', '_').replace('-', '_').replace('(', '').replace(')', '') for c in df.columns]
    return df


def parse_upload(uploaded_file):
    df, warning = _read_any_csv(uploaded_file)
    raw = df.attrs.get('raw_text', '') if df is not None else ''
    df = normalize_columns(df)
    if df is not None:
        df.attrs['raw_text'] = raw
    return df, warning


def _num(x):
    return pd.to_numeric(str(x).replace('%','').replace(',','').replace('$',''), errors='coerce')


def safe_sum(df, candidates):
    if df is None or df.empty:
        return 0
    for c in candidates:
        if c in df.columns:
            vals = pd.to_numeric(df[c].astype(str).str.replace('%','', regex=False).str.replace(',','', regex=False), errors='coerce').fillna(0)
            return float(vals.sum())
    return 0


def safe_mean(df, candidates):
    if df is None or df.empty:
        return 0
    for c in candidates:
        if c in df.columns:
            vals = pd.to_numeric(df[c].astype(str).str.replace('%','', regex=False).str.replace(',','', regex=False), errors='coerce').dropna()
            if len(vals):
                return float(vals.mean())
    return 0


def _sum_ga4_section(raw_text, header_contains, value_col_name):
    """Reads GA4 overview exports that contain many mini tables in one CSV."""
    if not raw_text:
        return 0
    lines = raw_text.splitlines()
    total = 0.0
    capture = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if capture:
                break
            continue
        lower = stripped.lower()
        if lower.startswith('#'):
            if capture:
                break
            continue
        if (header_contains.lower() in lower) and (value_col_name.lower() in lower):
            capture = True
            continue
        if capture:
            parts = [p.strip() for p in stripped.split(',')]
            if len(parts) >= 2:
                val = _num(parts[-1])
                if pd.notna(val):
                    total += float(val)
            else:
                break
    return total


def _ga4_metrics_from_raw(df):
    raw = df.attrs.get('raw_text', '') if df is not None else ''
    sessions = _sum_ga4_section(raw, 'Session primary channel group', 'Sessions')
    active_users = _sum_ga4_section(raw, 'Nth week', 'Active users')
    new_users = _sum_ga4_section(raw, 'Nth week', 'New users')
    conversions = _sum_ga4_section(raw, 'Key event', 'Key events') or _sum_ga4_section(raw, 'Event name', 'Key events')
    if sessions == 0:
        sessions = safe_sum(df, ['sessions', 'session_start'])
    if sessions == 0:
        sessions = safe_sum(df, ['active_users', 'users', 'total_users']) or active_users or new_users
    return sessions, conversions


def extract_metrics(gsc=None, ga4=None, linkedin=None, social=None, email=None):
    metrics = {}
    metrics['gsc_clicks'] = safe_sum(gsc, ['clicks', 'click'])
    metrics['gsc_impressions'] = safe_sum(gsc, ['impressions', 'impression'])
    metrics['gsc_ctr'] = safe_mean(gsc, ['ctr'])
    metrics['gsc_position'] = safe_mean(gsc, ['position', 'avg_position', 'average_position'])

    ga4_sessions, ga4_conversions = _ga4_metrics_from_raw(ga4)
    metrics['sessions'] = ga4_sessions
    metrics['conversions'] = ga4_conversions or safe_sum(ga4, ['conversions', 'key_events', 'events', 'form_submits'])
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

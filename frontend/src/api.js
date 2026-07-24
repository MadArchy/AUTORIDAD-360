/** Cliente API canónico Autoridad 360 (Fases 1–7).
 * Docker:     VITE_API_URL=http://127.0.0.1:8000/api/v1
 * Piloto local (uvicorn --port 8012): default abajo
 */
const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8012/api/v1';

const ORG_KEY = 'org_slug';
const TOKEN_KEY = 'jwt_token';
const USER_KEY = 'auth_user';

function tokenStore() {
  try {
    return typeof sessionStorage !== 'undefined' ? sessionStorage : localStorage;
  } catch {
    return null;
  }
}

function clearBadToken() {
  try {
    const store = tokenStore();
    store?.removeItem(TOKEN_KEY);
    if (typeof localStorage !== 'undefined') {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
    }
    if (typeof sessionStorage !== 'undefined') {
      sessionStorage.removeItem(USER_KEY);
    }
  } catch {
    /* ignore */
  }
}

export function getOrgSlug() {
  try {
    return localStorage.getItem(ORG_KEY) || 'agencia-piloto';
  } catch {
    return 'agencia-piloto';
  }
}

export function setOrgSlug(slug) {
  try {
    localStorage.setItem(ORG_KEY, slug || 'agencia-piloto');
  } catch {
    /* ignore */
  }
}

export function getStoredToken() {
  try {
    const store = tokenStore();
    return store?.getItem(TOKEN_KEY) || localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function getStoredUser() {
  try {
    const raw =
      sessionStorage.getItem(USER_KEY) || localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function isAuthenticated() {
  return Boolean(getStoredToken());
}

export async function login(email, password, orgSlug = 'agencia-piloto') {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    let detail = '';
    try {
      detail = await res.text();
    } catch {
      detail = res.statusText;
    }
    throw new Error(detail || `Login ${res.status}`);
  }
  const data = await res.json();
  const store = tokenStore();
  store?.setItem(TOKEN_KEY, data.access_token);
  const userPayload = JSON.stringify({
    email: data.email,
    user_id: data.user_id,
    roles_by_org: data.roles_by_org || {},
  });
  store?.setItem(USER_KEY, userPayload);
  setOrgSlug(orgSlug);
  return data;
}

export async function refreshAccessToken() {
  const res = await fetch(`${API_BASE}/auth/refresh`, {
    method: 'POST',
    credentials: 'include',
  });
  if (!res.ok) return null;
  const data = await res.json();
  const store = tokenStore();
  store?.setItem(TOKEN_KEY, data.access_token);
  store?.setItem(
    USER_KEY,
    JSON.stringify({
      email: data.email,
      user_id: data.user_id,
      roles_by_org: data.roles_by_org || {},
    })
  );
  return data;
}

export async function logout() {
  try {
    await fetch(`${API_BASE}/auth/logout`, {
      method: 'POST',
      credentials: 'include',
    });
  } catch {
    /* ignore network */
  }
  clearBadToken();
}

export async function getHealth() {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error(`Health ${res.status}`);
  return res.json();
}

export async function api(path, options = {}) {
  const token = getStoredToken();
  const authHeader = token ? { Authorization: `Bearer ${token}` } : {};
  const headers = {
    'X-Org-Slug': getOrgSlug(),
    ...authHeader,
    ...(options.body ? { 'Content-Type': 'application/json' } : {}),
    ...options.headers,
  };
  // Compatibilidad explícita para herramientas locales; nunca se activa por defecto.
  if (!token && import.meta.env.DEV && import.meta.env.VITE_ALLOW_HEADER_AUTH === 'true') {
    headers['X-User-Email'] = 'agencia@autoridad360.local';
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
    credentials: 'include',
  });
  if (!res.ok) {
    let detail = '';
    try {
      detail = await res.text();
    } catch {
      detail = res.statusText;
    }
    if (res.status === 401 && token) {
      const refreshed = await refreshAccessToken();
      if (refreshed?.access_token) {
        const retryHeaders = {
          ...headers,
          Authorization: `Bearer ${refreshed.access_token}`,
        };
        const retry = await fetch(`${API_BASE}${path}`, {
          ...options,
          headers: retryHeaders,
          credentials: 'include',
        });
        if (retry.ok) {
          if (retry.status === 204) return null;
          const retryText = await retry.text();
          return retryText ? JSON.parse(retryText) : null;
        }
      }
      clearBadToken();
    }
    throw new Error(detail || `API ${res.status}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

/** Alias usado por AICopilotDrawer y otros componentes legacy. */
export const fetchApi = api;

/** Une cuota + pilares al shape que espera la UI. */
export function normalizeProfile(raw) {
  if (!raw) return null;
  const quotaBySlug = Object.fromEntries(
    (raw.quota?.pillars || []).map((q) => [q.slug, q])
  );
  const pctBySlug = Object.fromEntries(
    (raw.editorial_percentages || []).map((e) => [e.pillar_slug, e.target_pct])
  );
  const pillars = (raw.pillars || []).map((p) => {
    const q = quotaBySlug[p.slug] || {};
    const target = Number(pctBySlug[p.slug] ?? q.target_pct ?? 0);
    const actual = Number(q.actual_pct ?? 0);
    const deficit = Number(q.deficit_pct ?? Math.max(0, target - actual));
    const boost = Number(q.quota_boost ?? 1);
    const needsBoost = Boolean(q.needs_boost ?? deficit >= 2);
    return {
      ...p,
      target_percentage: target,
      current_month_pct: actual,
      current_month_count: q.count ?? q.article_count ?? 0,
      deficit_pct: deficit,
      quota_status: needsBoost ? 'below_quota' : 'ok',
      quota_boost: boost,
      needs_boost: needsBoost,
    };
  });
  const markets = (raw.market_percentages || []).map((m, i) => ({
    id: i + 1,
    market_code: m.market_code,
    market_name:
      m.market_code === 'MX'
        ? 'México'
        : m.market_code === 'US'
          ? 'Estados Unidos'
          : m.market_code,
    target_percentage: Number(m.target_pct),
  }));
  return {
    ...raw,
    target_audiences: raw.audiences || raw.target_audiences || [],
    services: raw.services || [],
    search_themes: Array.isArray(raw.search_themes) ? raw.search_themes : [],
    deficit_pillars: raw.quota?.deficit_pillars || [],
    pillars,
    markets,
  };
}

/** Extrae slides del carrusel aunque body_json venga como objeto o el LLM use text/content. */
export function normalizeCarouselSlides(carousel) {
  if (!carousel) return [];
  let raw = carousel.body_json;
  if (typeof raw === 'string') {
    try {
      raw = JSON.parse(raw);
    } catch {
      raw = null;
    }
  }
  let slides = null;
  if (Array.isArray(raw)) slides = raw;
  else if (raw && Array.isArray(raw.slides)) slides = raw.slides;
  else if (typeof carousel.body_text === 'string' && carousel.body_text.trim().startsWith('[')) {
    try {
      const parsed = JSON.parse(carousel.body_text);
      if (Array.isArray(parsed)) slides = parsed;
      else if (parsed?.slides) slides = parsed.slides;
    } catch {
      slides = null;
    }
  }
  if (!Array.isArray(slides) || !slides.length) {
    const text = (carousel.body_text || '').trim();
    if (!text) return [];
    return [{ slide: 1, title: 'Carrusel', content: text.slice(0, 500) }];
  }
  return slides.map((s, i) => {
    if (typeof s === 'string') {
      return { slide: i + 1, title: `Diapositiva ${i + 1}`, content: s };
    }
    const title = s?.title || s?.headline || `Diapositiva ${i + 1}`;
    const content = s?.content || s?.text || s?.body || '';
    return {
      slide: Number(s?.slide) || i + 1,
      title,
      content,
    };
  });
}

/** Aplana pieces[] a campos por formato para la UI multi-formato. */
export function normalizePackage(pkg, preferredLang = null) {
  if (!pkg) return null;
  const allPieces = pkg.pieces || [];
  const lang = preferredLang ? String(preferredLang).toLowerCase() : null;
  const matched = lang
    ? allPieces.filter((p) => String(p.language || '').toLowerCase() === lang)
    : [];
  const pieces = matched.length ? matched : allPieces;
  const byType = (t) => pieces.find((p) => p.format_type === t);
  const linkedin = byType('linkedin');
  const video = byType('video_script');
  const carousel = byType('carousel');
  const newsletter = byType('newsletter');
  return {
    ...pkg,
    language: linkedin?.language || video?.language || pieces[0]?.language || pkg.language || preferredLang || 'es',
    linkedin_post: linkedin?.body_text || '',
    linkedin_piece_id: linkedin?.id,
    video_script: video?.body_text || '',
    video_piece_id: video?.id,
    carousel_slides: normalizeCarouselSlides(carousel),
    carousel_piece_id: carousel?.id,
    newsletter_edition: newsletter?.body_text || '',
    newsletter_piece_id: newsletter?.id,
    pieces,
  };
}

export function normalizeUsage(raw) {
  if (!raw) return null;
  const total = Number(raw.total_calls || 0);
  const local = Number(raw.local_calls || 0);
  const failed = Number(raw.failed || 0);
  const localPct = total ? Math.round((local / total) * 100) : 0;
  return {
    ...raw,
    summary: {
      total_requests: total,
      failed_requests: failed,
      success_requests: Number(raw.success || 0),
      local_requests: local,
      paid_requests: Math.max(0, total - local),
      local_pct: localPct,
      total_tokens: 0,
      avg_latency_ms: 0,
      total_cost_usd: Number(raw.total_cost_usd || 0).toFixed(4),
    },
  };
}

export function normalizeReport(raw) {
  if (!raw) return null;
  return {
    ...raw,
    markdown_report: raw.markdown_report || raw.markdown || raw.markdown_content || '',
  };
}

/** Adapta /metrics/dashboard anidado al shape plano de la UI. */
export function normalizeDashboard(raw) {
  if (!raw) return null;
  const op = raw.operational || {};
  const com = raw.commercial || {};
  const funnel = com.funnel || {};
  const editorial = raw.editorial || {};
  const pillars = editorial.pillars || [];
  return {
    ...raw,
    total_articles: raw.total_articles ?? raw.articles_total ?? 0,
    total_content_pieces:
      raw.total_content_pieces ??
      (Number(op.pieces_approved || 0) + Number(op.pieces_pending || 0)),
    total_leads: raw.total_leads ?? funnel.total ?? 0,
    qualified_leads: raw.qualified_leads ?? com.qualified_leads ?? funnel.qualified ?? 0,
    converted_leads: raw.converted_leads ?? funnel.converted ?? 0,
    conversion_rate_pct: Number(com.conversion_rate_pct ?? raw.conversion_rate_pct ?? 0),
    slots_total: op.slots_total ?? 0,
    slots_pending_approval: op.slots_pending_approval ?? 0,
    pillar_breakdown: pillars.map((p) => ({
      pillar_name: p.name || p.pillar_name,
      pillar_slug: p.slug || p.pillar_slug,
      pieces: p.pieces ?? 0,
      leads: p.total_leads ?? p.leads ?? 0,
      qualified: p.qualified_leads ?? p.qualified ?? 0,
      total_engagement: (p.likes || 0) + (p.comments || 0) + (p.total_engagement || 0),
    })),
  };
}

export { API_BASE };

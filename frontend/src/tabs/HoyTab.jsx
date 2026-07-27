import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  ArrowRight,
  Check,
  Copy,
  Download,
  ExternalLink,
  Globe2,
  ImagePlus,
  Megaphone,
  Plus,
  RefreshCw,
  Search,
  X,
} from 'lucide-react';
import { resolveMediaUrl } from '../components/FormatPreview';

const PLATFORM_LABELS = {
  linkedin: 'LinkedIn',
  youtube: 'YouTube',
  x: 'X',
  twitter: 'X',
  tiktok: 'TikTok',
  instagram: 'Instagram',
  facebook: 'Facebook',
  web: 'Web',
  regulacion: 'Regulación',
};

const TREND_FILTERS = [
  { id: 'todos', label: 'Todos' },
  { id: 'linkedin', label: 'LinkedIn' },
  { id: 'instagram', label: 'Instagram' },
  { id: 'facebook', label: 'Facebook' },
  { id: 'tiktok', label: 'TikTok' },
  { id: 'youtube', label: 'YouTube' },
  { id: 'web', label: 'Web' },
  { id: 'regulacion', label: 'Regulación' },
  { id: 'ia', label: 'IA y PI' },
  { id: 'latam', label: 'Latam' },
  { id: 'eeuu', label: 'EE. UU.' },
  { id: 'mexico', label: 'México' },
  { id: 'colombia', label: 'Colombia' },
];

const SOCIAL_NOTE_ORDER = ['linkedin', 'instagram', 'facebook', 'tiktok', 'youtube'];

const DEFAULT_SOCIAL_NOTES = {
  linkedin: {
    hook: 'Análisis breve del día',
    post: 'Publica dato + opinión + pregunta a GC. Ideal: martes a jueves.',
    cta: 'Invita a conversar en comentarios.',
    where: 'Cierre del post + primer comentario',
    avoid: 'Pitch en la primera línea',
    format: 'Post + imagen 1:1',
  },
  instagram: {
    hook: 'Carrusel de la señal del día',
    post: 'Idea central → 3 hallazgos → CTA.',
    cta: 'Guarda y comparte con tu equipo legal.',
    where: 'Caption + sticker de enlace',
    avoid: 'Muro de texto',
    format: 'Carrusel 4:5',
  },
  facebook: {
    hook: 'Explica la noticia en lenguaje claro',
    post: 'Contexto + riesgo + qué preguntar mañana.',
    cta: 'Enlace a artículo o contacto.',
    where: 'Cierre + primer comentario',
    avoid: 'Clickbait',
    format: 'Post + imagen',
  },
  tiktok: {
    hook: 'Gancho en 3 segundos',
    post: '30–45s: qué pasó, riesgo, 1 acción.',
    cta: 'Pregunta al cierre.',
    where: 'Texto en pantalla + CTA verbal',
    avoid: 'Jerga densa al inicio',
    format: 'Video 9:16',
  },
  youtube: {
    hook: 'Microanálisis de la señal',
    post: '3–5 min: contexto → riesgo GC → acción.',
    cta: 'CTA en descripción y comentario fijado.',
    where: 'Segundos 3–8 + descripción',
    avoid: 'Promesas garantizadas',
    format: 'Short / microanálisis',
  },
};

const SCORE_ROWS = [
  ['relevance', 'Relevancia estratégica'],
  ['impact', 'Impacto empresarial'],
  ['reliability', 'Confiabilidad de la fuente'],
  ['freshness', 'Vigencia'],
  ['content_potential', 'Potencial editorial'],
  ['mx_us_relevance', 'Mercado objetivo'],
  ['conversion', 'Conversión'],
];

function opportunityLabel(score) {
  const n = Number(score) || 0;
  if (n >= 80) return 'Alta oportunidad';
  if (n >= 60) return 'Oportunidad media';
  return 'Explorar';
}

function buildReasons(art, scores) {
  const reasons = [];
  const pillar = art.matched_pillar_name || art.matched_pillar;
  if (pillar) reasons.push(`Alta relación con ${pillar}.`);
  if ((scores.mx_us_relevance || 0) >= 40 || /mx|us|ee\.?\s*uu|europa|eu/i.test(`${art.title} ${art.summary || ''}`)) {
    reasons.push('Tema relevante para empresas de Estados Unidos / México–EE. UU.');
  }
  if ((scores.reliability || 0) >= 40 || art.source_name) {
    reasons.push(`Fuente ${art.source_name ? `verificable (${art.source_name})` : 'jurídica o comercial verificable'}.`);
  }
  if ((scores.content_potential || 0) >= 30 || (Number(art.total_score || art.top10_score) || 0) >= 70) {
    reasons.push('Potencial para artículo legal, LinkedIn y video ejecutivo.');
  }
  if (art.quota_priority) {
    reasons.push('Prioridad de cuota editorial: refuerza un pilar bajo meta.');
  }
  if (!reasons.length) {
    reasons.push('Seleccionada por relevancia, mercado, autoridad de fuente y potencial comercial.');
  }
  return reasons.slice(0, 5);
}

function buildTags(art) {
  const tags = [];
  if (art.matched_pillar_name || art.matched_pillar) {
    tags.push({ label: art.matched_pillar_name || art.matched_pillar, tone: 'accent' });
  }
  if (art.category) tags.push({ label: art.category, tone: 'muted' });
  if (art.quota_priority) tags.push({ label: 'México–EE. UU.', tone: 'success' });
  if (art.status && art.status !== 'collected') tags.push({ label: art.status, tone: 'muted' });
  return tags.slice(0, 5);
}

function scoreValue(scores, key, total) {
  const raw = Number(scores?.[key]);
  if (Number.isFinite(raw) && raw > 0) return Math.round(Math.min(100, raw));
  const seed = {
    relevance: 0.92,
    impact: 0.85,
    reliability: 0.8,
    freshness: 0.78,
    content_potential: 0.72,
    mx_us_relevance: 0.7,
    conversion: 0.55,
  }[key] || 0.7;
  return Math.round(Math.min(100, (Number(total) || 50) * seed));
}

function relativeAge(iso) {
  if (!iso) return 'Hoy';
  try {
    const mins = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
    if (mins < 60) return `${mins || 1} min`;
    const hours = Math.round(mins / 60);
    if (hours < 48) return `${hours} h`;
    return `${Math.round(hours / 24)} d`;
  } catch {
    return 'Hoy';
  }
}

function isFreshIso(iso, maxAgeHours = 72) {
  if (!iso) return true;
  try {
    const ageMs = Date.now() - new Date(iso).getTime();
    return Number.isFinite(ageMs) && ageMs >= 0 && ageMs <= maxAgeHours * 3600 * 1000;
  } catch {
    return true;
  }
}

function looksStaleTitle(title) {
  const years = String(title || '').match(/\b(20[0-2]\d)\b/g);
  if (!years?.length) return false;
  const current = new Date().getFullYear();
  return years.every((y) => Number(y) < current);
}

function normalizePlatformKey(value) {
  const raw = String(value || '').toLowerCase();
  if (!raw) return 'web';
  if (raw.includes('linkedin')) return 'linkedin';
  if (raw.includes('instagram')) return 'instagram';
  if (raw.includes('facebook') || raw.includes('meta')) return 'facebook';
  if (raw.includes('tiktok')) return 'tiktok';
  if (raw.includes('youtube')) return 'youtube';
  if (raw.includes('twitter') || raw === 'x' || raw.includes('x /')) return 'x';
  if (raw.includes('regula') || raw.includes('law') || raw.includes('legal')) return 'regulacion';
  return 'web';
}

function PlatformBrandIcon({ platform }) {
  const key = normalizePlatformKey(platform);
  const uid = React.useId().replace(/:/g, '');
  const common = {
    width: 18,
    height: 18,
    viewBox: '0 0 24 24',
    'aria-hidden': true,
    focusable: 'false',
  };

  if (key === 'linkedin') {
    return (
      <svg {...common}>
        <rect width="24" height="24" rx="4" fill="#0A66C2" />
        <path
          fill="#fff"
          d="M7.05 9.25H4.7V19h2.35V9.25zM5.87 5A1.37 1.37 0 1 0 5.88 7.74 1.37 1.37 0 0 0 5.87 5zM19.3 12.7c0-2.2-1.18-3.62-3.47-3.62-1.6 0-2.31.88-2.71 1.5V9.25h-2.35c.03.7 0 9.75 0 9.75h2.35v-5.44c0-.29.02-.58.11-.79.23-.58.76-1.18 1.65-1.18 1.16 0 1.63.89 1.63 2.19V19H19.3v-6.3z"
        />
      </svg>
    );
  }

  if (key === 'instagram') {
    const gradId = `ig-${uid}`;
    return (
      <svg {...common}>
        <defs>
          <radialGradient id={gradId} cx="30%" cy="107%" r="150%">
            <stop offset="0%" stopColor="#fdf497" />
            <stop offset="5%" stopColor="#fdf497" />
            <stop offset="45%" stopColor="#fd5949" />
            <stop offset="60%" stopColor="#d6249f" />
            <stop offset="90%" stopColor="#285AEB" />
          </radialGradient>
        </defs>
        <rect width="24" height="24" rx="6" fill={`url(#${gradId})`} />
        <path
          fill="none"
          stroke="#fff"
          strokeWidth="1.8"
          d="M12 7.6a4.4 4.4 0 1 0 0 8.8 4.4 4.4 0 0 0 0-8.8z"
        />
        <rect x="6.4" y="6.4" width="11.2" height="11.2" rx="3.2" fill="none" stroke="#fff" strokeWidth="1.8" />
        <circle cx="16.7" cy="7.4" r="1.05" fill="#fff" />
      </svg>
    );
  }

  if (key === 'facebook') {
    return (
      <svg {...common}>
        <rect width="24" height="24" rx="4" fill="#1877F2" />
        <path
          fill="#fff"
          d="M15.9 12.9h-2.1v7.1h-2.95v-7.1H9.2V10.5h1.65V9.05c0-1.37.65-3.5 3.5-3.5h2.56v2.56h-1.86c-.3 0-.74.15-.74.8v1.59h2.64l-.35 2.4z"
        />
      </svg>
    );
  }

  if (key === 'tiktok') {
    return (
      <svg {...common}>
        <rect width="24" height="24" rx="5" fill="#111" />
        <path
          fill="#25F4EE"
          d="M16.6 7.2c-.7-.42-1.24-1.05-1.52-1.8H13.3v9.05a2.35 2.35 0 1 1-1.62-2.23V9.95a4.55 4.55 0 1 0 3.32 4.35V9.55c.7.52 1.55.83 2.48.9V8.2a3.4 3.4 0 0 1-.88-.99z"
        />
        <path
          fill="#FE2C55"
          d="M17.48 8.2v2.25c-.93-.07-1.78-.38-2.48-.9v4.75a4.55 4.55 0 1 1-4.42-4.55v2.25a2.35 2.35 0 1 0 1.62 2.23V5.4h1.78c.28.75.82 1.38 1.52 1.8.28.17.58.3.88.4.32.1.66.15 1.02.17.18.01.36.01.54 0z"
        />
        <path
          fill="#fff"
          d="M14.78 9.55v4.75a2.35 2.35 0 1 1-1.62-2.23V5.4h1.78c.28.75.82 1.38 1.52 1.8.28.17.58.3.88.4v2.25c-.93-.07-1.78-.38-2.48-.9-.02 0-.05 0-.08 0z"
        />
      </svg>
    );
  }

  if (key === 'youtube') {
    return (
      <svg {...common}>
        <rect width="24" height="24" rx="5" fill="#FF0000" />
        <path fill="#fff" d="M10 8.2v7.6L16.4 12 10 8.2z" />
      </svg>
    );
  }

  if (key === 'x') {
    return (
      <svg {...common}>
        <rect width="24" height="24" rx="5" fill="#000" />
        <path
          fill="#fff"
          d="M16.95 6.4h1.72l-3.76 4.3 4.42 6.9h-3.46l-2.71-3.72-3.1 3.72H8.34l4.02-4.83L8.1 6.4h3.55l2.45 3.4 2.85-3.4zm-.6 10.08h.95L10.78 7.5h-1.02l6.59 8.98z"
        />
      </svg>
    );
  }

  if (key === 'regulacion') {
    return (
      <svg {...common}>
        <rect width="24" height="24" rx="5" fill="#2563EB" />
        <path
          fill="#fff"
          d="M8 5.5h6.2L17.5 9v9.5a1 1 0 0 1-1 1H8a1 1 0 0 1-1-1v-12a1 1 0 0 1 1-1zm5.8.8v2.9h2.9l-2.9-2.9zM9.2 12.2h5.6v1.2H9.2v-1.2zm0 2.6h5.6v1.2H9.2v-1.2zm0-5.2h3.2v1.2H9.2V9.6z"
        />
      </svg>
    );
  }

  // Web / default — globe line art like the mock
  return (
    <svg {...common} fill="none">
      <circle cx="12" cy="12" r="8.2" stroke="#D7DEE9" strokeWidth="1.7" />
      <path
        d="M4.2 12h15.6M12 3.8c2.2 2.3 3.3 5 3.3 8.2s-1.1 5.9-3.3 8.2c-2.2-2.3-3.3-5-3.3-8.2s1.1-5.9 3.3-8.2z"
        stroke="#D7DEE9"
        strokeWidth="1.7"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function urgencyFromScore(score) {
  const n = Number(score) || 0;
  if (n >= 85) return 'Alta';
  if (n >= 65) return 'Media';
  return null;
}

function cardMatchesFilter(card, filterId) {
  if (!filterId || filterId === 'todos') return true;
  const blob = `${card.platformKey} ${card.platform} ${(card.tags || []).join(' ')} ${card.title}`.toLowerCase();
  const map = {
    linkedin: 'linkedin',
    instagram: 'instagram',
    facebook: 'facebook',
    tiktok: 'tiktok',
    youtube: 'youtube',
    web: 'web',
    regulacion: /regula|legal|law|gobern/,
    ia: /\bia\b|inteligencia|pi\b|propiedad/,
    latam: /latam|américa|america|latino/,
    eeuu: /ee\.?\s*uu|usa|united states|estados unidos/,
    mexico: /m[eé]xico|mx\b/,
    colombia: /colombia/,
  };
  const rule = map[filterId];
  if (!rule) return true;
  if (typeof rule === 'string') return blob.includes(rule) || card.platformKey === rule;
  return rule.test(blob);
}

function buildSocialNotes(adTrendNotes) {
  const byPlatform = {};
  for (const note of adTrendNotes?.ad_notes || []) {
    if (!note || typeof note !== 'object') continue;
    const key = normalizePlatformKey(note.platform);
    if (!SOCIAL_NOTE_ORDER.includes(key)) continue;
    byPlatform[key] = {
      hook: note.hook || note.headline || note.angle || '',
      post: note.post || note.copy || note.how || note.tip || note.summary || '',
      cta: note.cta || '',
      where: note.where || '',
      avoid: note.avoid || '',
      format: note.format || '',
      newsTitle: note.news_title || note.theme || '',
      newsUrl: note.news_url || (Array.isArray(note.urls) ? note.urls[0] : '') || '',
      imageUrl: note.image_url || null,
      imageRatio: note.image_ratio || null,
      urgency: note.urgency || null,
    };
  }

  return SOCIAL_NOTE_ORDER.map((key) => {
    const fallback = DEFAULT_SOCIAL_NOTES[key] || {};
    const raw = byPlatform[key] || {};
    return {
      key,
      label: PLATFORM_LABELS[key] || key,
      hook: raw.hook || fallback.hook || '',
      post: raw.post || fallback.post || '',
      cta: raw.cta || fallback.cta || '',
      where: raw.where || fallback.where || '',
      avoid: raw.avoid || fallback.avoid || '',
      format: raw.format || fallback.format || '',
      newsTitle: raw.newsTitle || '',
      newsUrl: raw.newsUrl || '',
      imageUrl: raw.imageUrl || null,
      imageRatio: raw.imageRatio || null,
      urgency: raw.urgency || null,
      tip: [raw.hook || fallback.hook, raw.cta || fallback.cta].filter(Boolean).join(' · '),
    };
  });
}

/**
 * Centro de mando editorial — descubrimiento del día.
 */
export default function HoyTab({
  top10 = [],
  onUseSuggestion,
  onCreateFromTrend,
  onRefreshTop10,
  onPatrol,
  loadingTop10 = false,
  isSearching = false,
  top10Error = '',
  adTrendNotes = null,
  adTrendMessage = null,
  adTrendBusy = false,
  onRefreshAdTrendNotes,
  onGenerateAdTrendNotes,
  onGenerateAdNoteImage,
  onOpenSources,
  onRefreshIntelligence,
  intelligenceBusy = false,
  signalsCount = 0,
  flowCounts = null,
  onOpenLive,
}) {
  const [dismissed, setDismissed] = useState(() => new Set());
  const [analysisOpen, setAnalysisOpen] = useState(true);
  const [copiedNoteKey, setCopiedNoteKey] = useState(null);
  const [imageBusyKey, setImageBusyKey] = useState(null);
  const [imageErrorByKey, setImageErrorByKey] = useState({});
  /** Solo mostrar imagen tras pulsar «Crear imagen» en esta sesión. */
  const [revealedImages, setRevealedImages] = useState({});
  const [focusedId, setFocusedId] = useState(null);
  const [trendFilter, setTrendFilter] = useState('todos');
  const [trendsExpanded, setTrendsExpanded] = useState(false);
  const [creatingTrendId, setCreatingTrendId] = useState(null);
  const priorityRef = useRef(null);

  const ranked = useMemo(
    () => (top10 || []).filter((a) => !dismissed.has(a.id || a.article_id)),
    [top10, dismissed]
  );

  const articleKey = (art) => art?.id ?? art?.article_id ?? null;

  const leadArticle = useMemo(() => {
    if (!ranked.length) return null;
    if (focusedId != null) {
      const hit = ranked.find((a) => String(articleKey(a)) === String(focusedId));
      if (hit) return hit;
    }
    return ranked[0];
  }, [ranked, focusedId]);

  const remainingArticles = useMemo(() => {
    const leadKey = articleKey(leadArticle);
    return ranked.filter((a) => String(articleKey(a)) !== String(leadKey)).slice(0, 9);
  }, [ranked, leadArticle]);

  const trends = adTrendNotes?.trends || [];
  const busy = intelligenceBusy || loadingTop10 || isSearching || adTrendBusy;

  const leadScore = Number(leadArticle?.top10_score ?? leadArticle?.total_score) || 0;
  const leadScores = leadArticle?.scores || {};
  const reasons = leadArticle ? buildReasons(leadArticle, leadScores) : [];
  const tags = leadArticle ? buildTags(leadArticle) : [];
  const leadRank =
    ranked.findIndex((a) => String(articleKey(a)) === String(articleKey(leadArticle))) + 1;

  const selectOpportunity = (art) => {
    const id = articleKey(art);
    if (id == null) return;
    setFocusedId(id);
    setAnalysisOpen(true);
    requestAnimationFrame(() => {
      priorityRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  };

  const refreshAll = () => {
    if (onRefreshIntelligence) onRefreshIntelligence();
    else {
      onRefreshTop10?.();
      onPatrol?.();
      onGenerateAdTrendNotes?.();
    }
  };

  const trendCards = useMemo(() => {
    const catalog = [...ranked, ...remainingArticles];
    const byId = new Map();
    const byUrl = new Map();
    for (const art of catalog) {
      const id = art?.id ?? art?.article_id;
      if (id != null) byId.set(String(id), art);
      const u = (art?.source_url || art?.url || '').split('?')[0].toLowerCase();
      if (u) byUrl.set(u, art);
    }

    const fromTrends = (trends || [])
      .map((t, i) => {
        const platformKey = normalizePlatformKey(t.platform);
        const title = t.summary || t.title || t.theme || 'Tendencia detectada';
        const url = (t.urls && t.urls[0]) || null;
        const urlKey = (url || '').split('?')[0].toLowerCase();
        const articleId = t.article_id ?? t.articleId ?? null;
        const article =
          (articleId != null ? byId.get(String(articleId)) : null)
          || (urlKey ? byUrl.get(urlKey) : null)
          || null;
        const detected = t.detected_at || null;
        const growthPct = t.growth_pct != null ? Math.round(Number(t.growth_pct)) : null;
        const urgency = t.urgency || null;
        return {
          id: `trend-${i}`,
          platformKey,
          platform: PLATFORM_LABELS[platformKey] || t.platform || 'Web',
          title,
          age: relativeAge(detected || adTrendNotes?.generated_at),
          detectedAt: detected,
          growthPct,
          urgency,
          tags: [t.theme, t.market].filter(Boolean).slice(0, 3),
          url,
          articleId: articleId || article?.id || article?.article_id || null,
          article,
        };
      })
      .filter((c) => {
        if (looksStaleTitle(c.title)) return false;
        if (/linkedin\.com\/pulse/i.test(c.url || '') && !c.detectedAt) return false;
        if (c.detectedAt && !isFreshIso(c.detectedAt, 72)) return false;
        return true;
      });

    if (fromTrends.length) return fromTrends.slice(0, 12);

    return remainingArticles
      .filter((art) => isFreshIso(art.published_at, 72) && !looksStaleTitle(art.title))
      .slice(0, 12)
      .map((art, i) => {
        const score = Number(art.top10_score ?? art.total_score) || 0;
        const platformKey = normalizePlatformKey(art.source_name || art.category);
        const growthPct = score >= 70 ? Math.round(40 + score * 1.2) : null;
        return {
          id: art.id || art.article_id || `sig-${i}`,
          platformKey,
          platform: PLATFORM_LABELS[platformKey] || art.source_name || 'Web',
          title: art.title,
          age: relativeAge(art.published_at),
          detectedAt: art.published_at,
          growthPct,
          urgency: growthPct == null ? urgencyFromScore(score) : null,
          tags: [art.category, art.matched_pillar_name || art.matched_pillar].filter(Boolean).slice(0, 3),
          url: art.source_url || art.url || null,
          articleId: art.id || art.article_id || null,
          article: art,
        };
      });
  }, [trends, remainingArticles, ranked, adTrendNotes]);

  const filteredTrendCards = useMemo(
    () => trendCards.filter((c) => cardMatchesFilter(c, trendFilter)),
    [trendCards, trendFilter]
  );

  const visibleTrendCards = trendsExpanded
    ? filteredTrendCards
    : filteredTrendCards.slice(0, 8);

  const socialNotes = useMemo(() => buildSocialNotes(adTrendNotes), [adTrendNotes]);

  useEffect(() => {
    setRevealedImages({});
    setImageErrorByKey({});
    setImageBusyKey(null);
  }, [adTrendNotes?.generated_at]);

  const handleCreateTrendContent = async (card) => {
    if (!card || creatingTrendId) return;
    setCreatingTrendId(card.id);
    try {
      if (typeof onCreateFromTrend === 'function') {
        await onCreateFromTrend(card);
        return;
      }
      if (card.article) {
        onUseSuggestion?.(card.article);
        return;
      }
      // Sin artículo: no abrir la URL (eso no es «crear contenido»)
    } finally {
      setCreatingTrendId(null);
    }
  };

  const handleCreateNoteImage = async (platformKey) => {
    if (!onGenerateAdNoteImage || imageBusyKey) return;
    setImageBusyKey(platformKey);
    setImageErrorByKey((prev) => {
      const next = { ...prev };
      delete next[platformKey];
      return next;
    });
    try {
      const note = await onGenerateAdNoteImage(platformKey);
      const url = note?.image_url || null;
      if (!url) throw new Error('La API no devolvió image_url');
      setRevealedImages((prev) => ({ ...prev, [platformKey]: url }));
    } catch (e) {
      setImageErrorByKey((prev) => ({
        ...prev,
        [platformKey]: e?.message || 'No se pudo crear la imagen',
      }));
    } finally {
      setImageBusyKey(null);
    }
  };

  const dailyBrief = useMemo(() => {
    const items = ranked.slice(0, 5).map((art, idx) => {
      const score = Math.round(Number(art.top10_score ?? art.total_score) || 0);
      const why =
        art.matched_pillar_name ||
        art.matched_pillar ||
        art.category ||
        (art.quota_priority ? 'Prioridad de cuota editorial' : 'Alta relevancia del día');
      return {
        id: articleKey(art),
        rank: idx + 1,
        title: art.title,
        source: art.source_name || 'Fuente',
        age: relativeAge(art.published_at),
        score,
        why,
        article: art,
      };
    });
    const bullets = [];
    if (items[0]) {
      bullets.push(
        `Prioridad #1: «${items[0].title.slice(0, 90)}${items[0].title.length > 90 ? '…' : ''}» (${items[0].source}).`
      );
    }
    const pillars = [
      ...new Set(
        ranked
          .slice(0, 8)
          .map((a) => a.matched_pillar_name || a.matched_pillar || a.category)
          .filter(Boolean)
      ),
    ].slice(0, 3);
    if (pillars.length) {
      bullets.push(`Pilares/temas del día: ${pillars.join(' · ')}.`);
    }
    const freshCount = ranked.filter((a) => isFreshIso(a.published_at, 36)).length;
    bullets.push(
      freshCount > 0
        ? `${freshCount} señal(es) con publicación en las últimas 36 h listas para Estudio.`
        : 'Aún no hay señales datadas de las últimas 36 h — actualiza inteligencia o patrulla tipologías.'
    );
    return { items, bullets: bullets.slice(0, 3), asOf: new Date().toLocaleDateString('es-CO', {
      weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
    }) };
  }, [ranked]);

  const discoverCount = flowCounts?.discover ?? Math.max(signalsCount, top10?.length || 0);
  const createCount = flowCounts?.create ?? 0;
  const reviewCount = flowCounts?.review ?? 0;
  const distributeCount = flowCounts?.distribute ?? 0;

  return (
    <section className="cmd-hoy">
      <nav className="cmd-flow" aria-label="Flujo editorial">
        {[
          { key: 'discover', label: 'Descubrir', count: discoverCount, active: true, onClick: null },
          { key: 'create', label: 'Crear', count: createCount, active: false, onClick: () => leadArticle && onUseSuggestion?.(leadArticle) },
          { key: 'review', label: 'Revisar', count: reviewCount, active: false, onClick: null },
          { key: 'distribute', label: 'Distribuir', count: distributeCount, active: false, onClick: null },
        ].map((step) => (
          <button
            key={step.key}
            type="button"
            className={`cmd-flow__step${step.active ? ' is-active' : ''}`}
            onClick={step.onClick || undefined}
            disabled={!step.active && !step.onClick}
          >
            <span className="cmd-flow__num">{step.count}</span>
            {step.label}
          </button>
        ))}
      </nav>

      <header className="cmd-hoy__header">
        <div>
          <span className="page-eyebrow">Centro editorial</span>
          <h2 className="cmd-hoy__title">La mejor oportunidad editorial de hoy</h2>
          <p className="cmd-hoy__lede">
            Seleccionada entre {Math.max(discoverCount, ranked.length) || '—'} señales según relevancia, mercado,
            autoridad de fuente y potencial comercial.
          </p>
        </div>
        <div className="cmd-hoy__actions">
          <button
            type="button"
            className="btn btn-secondary"
            disabled={busy}
            onClick={() => onOpenSources?.() || onRefreshAdTrendNotes?.()}
          >
            Configurar fuentes
          </button>
          <button type="button" className="btn btn-primary" disabled={busy} onClick={refreshAll}>
            <RefreshCw size={15} className={busy ? 'animate-spin' : ''} aria-hidden="true" />
            {busy ? 'Actualizando inteligencia…' : 'Actualizar inteligencia'}
          </button>
        </div>
      </header>

      {top10Error && (
        <div className="status-banner status-banner--error" role="alert">
          <div>
            <strong>No se pudo actualizar el ranking</strong>
            <p>{top10Error}</p>
          </div>
          <button type="button" className="btn btn-secondary" onClick={onRefreshTop10}>
            Reintentar
          </button>
        </div>
      )}

      {loadingTop10 && !leadArticle && (
        <div className="cmd-priority cmd-priority--skeleton" aria-busy="true">
          <div className="skeleton" style={{ width: 140, height: 160 }} />
          <div style={{ flex: 1 }}>
            <div className="skeleton" style={{ width: '28%', height: 14, marginBottom: 12 }} />
            <div className="skeleton" style={{ width: '88%', height: 28, marginBottom: 10 }} />
            <div className="skeleton" style={{ width: '70%', height: 16 }} />
          </div>
        </div>
      )}

      {!top10Error && !loadingTop10 && !leadArticle && (
        <div className="empty-state">
          <strong>Sin señales del día</strong>
          <span>
            No hay noticias con fecha de publicación en las últimas ~36 h. Actualiza la inteligencia
            o patrulla tipologías para traer el briefing de hoy.
          </span>
          <button type="button" className="btn btn-primary" disabled={busy} onClick={refreshAll}>
            Actualizar inteligencia
          </button>
          <button type="button" className="btn btn-secondary" disabled={busy} onClick={onPatrol}>
            Patrullar tipologías
          </button>
        </div>
      )}

      {leadArticle && (
        <article className="cmd-priority" ref={priorityRef}>
          <div className="cmd-priority__top">
            <span className="cmd-priority__eyebrow">
              {leadRank > 1 ? `Oportunidad #${leadRank}` : 'Recomendación prioritaria'}
            </span>
            <span className="cmd-priority__score">
              <Check size={14} aria-hidden="true" />
              {Math.round(leadScore)}/100 — {opportunityLabel(leadScore)}
            </span>
          </div>

          <div className="cmd-priority__body">
            <div className="cmd-priority__visual" aria-hidden="true">
              <Globe2 size={42} />
            </div>
            <div className="cmd-priority__main">
              <h3 className="cmd-priority__headline">{leadArticle.title}</h3>
              <p className="cmd-priority__summary">
                {leadArticle.summary || leadArticle.excerpt ||
                  `Prioridad alineada con ${leadArticle.matched_pillar_name || leadArticle.matched_pillar || 'tu perfil editorial'}.`}
              </p>
              {tags.length > 0 && (
                <div className="cmd-priority__tags">
                  {tags.map((t) => (
                    <span key={t.label} className={`cmd-tag cmd-tag--${t.tone}`}>{t.label}</span>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div className="cmd-priority__grid">
            <div>
              <h4 className="cmd-priority__section-title">Por qué debe publicarse</h4>
              <ul className="cmd-reasons">
                {reasons.map((r) => (
                  <li key={r}>
                    <Check size={14} aria-hidden="true" />
                    <span>{r}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <div className="cmd-priority__section-head">
                <h4 className="cmd-priority__section-title">Análisis de oportunidad</h4>
                <button
                  type="button"
                  className="cmd-linkish"
                  onClick={() => setAnalysisOpen((v) => !v)}
                >
                  {analysisOpen ? 'Ocultar' : 'Ver'}
                </button>
              </div>
              {analysisOpen && (
                <ul className="cmd-scorebars">
                  {SCORE_ROWS.map(([key, label]) => {
                    const value = scoreValue(leadScores, key, leadScore);
                    return (
                      <li key={key}>
                        <div className="cmd-scorebars__label">
                          <span>{label}</span>
                          <strong>{value}</strong>
                        </div>
                        <div className="cmd-scorebars__track" aria-hidden="true">
                          <span style={{ width: `${value}%` }} />
                        </div>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          </div>

          <div className="cmd-priority__cta">
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => onUseSuggestion?.(leadArticle)}
            >
              <Plus size={16} aria-hidden="true" />
              Crear paquete de contenido
            </button>
            {(leadArticle.url || leadArticle.source_url) && (
              <a
                className="btn btn-secondary"
                href={leadArticle.url || leadArticle.source_url}
                target="_blank"
                rel="noopener noreferrer"
              >
                Fuente <ExternalLink size={14} />
              </a>
            )}
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => {
                const id = articleKey(leadArticle);
                setDismissed((prev) => new Set(prev).add(id));
                setFocusedId(null);
              }}
            >
              <X size={15} aria-hidden="true" />
              Descartar
            </button>
          </div>
        </article>
      )}

      {dailyBrief.items.length > 0 && (
        <section className="cmd-brief" aria-label="Informe del día">
          <div className="cmd-brief__head">
            <div>
              <span className="cmd-brief__eyebrow">Informe del día</span>
              <h3 className="cmd-brief__title">Lectura editorial · {dailyBrief.asOf}</h3>
            </div>
            <button type="button" className="cmd-linkish" onClick={refreshAll} disabled={busy}>
              Actualizar <RefreshCw size={13} className={busy ? 'animate-spin' : ''} />
            </button>
          </div>
          <ul className="cmd-brief__bullets">
            {dailyBrief.bullets.map((b) => (
              <li key={b}>{b}</li>
            ))}
          </ul>
          <ol className="cmd-brief__list">
            {dailyBrief.items.map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  className="cmd-brief__row"
                  onClick={() => selectOpportunity(item.article)}
                >
                  <span className="score-tag">#{item.rank}</span>
                  <div className="cmd-brief__copy">
                    <strong>{item.title}</strong>
                    <span>
                      {item.source} · {item.age} · {item.score}/100 · {item.why}
                    </span>
                  </div>
                  <ArrowRight size={14} aria-hidden="true" />
                </button>
              </li>
            ))}
          </ol>
          <div className="cmd-brief__cta">
            {leadArticle ? (
              <button type="button" className="btn btn-primary" onClick={() => onUseSuggestion?.(leadArticle)}>
                <Plus size={14} /> Crear prioridad en Estudio
              </button>
            ) : null}
            <button type="button" className="btn btn-secondary" onClick={() => onOpenLive?.()}>
              Ver Live News
            </button>
          </div>
        </section>
      )}

      <section className="cmd-trends">
        <div className="cmd-trends__head">
          <div>
            <span className="cmd-trends__pulse" aria-hidden="true" />
            <h3 className="cmd-trends__title">Tendencias y señales</h3>
          </div>
        </div>

        {!adTrendBusy && !filteredTrendCards.length && (
          <p className="cmd-muted">
            {adTrendNotes?.disclaimer
              || adTrendMessage
              || 'Sin señales datadas del día en redes. Actualiza inteligencia para volver a investigar.'}
          </p>
        )}

        <div className="cmd-trends__filters" role="tablist" aria-label="Filtrar señales">
          {TREND_FILTERS.map((f) => (
            <button
              key={f.id}
              type="button"
              role="tab"
              aria-selected={trendFilter === f.id}
              className={`cmd-trends__chip${trendFilter === f.id ? ' is-active' : ''}`}
              onClick={() => setTrendFilter(f.id)}
            >
              {f.label}
            </button>
          ))}
        </div>

        {adTrendBusy && !visibleTrendCards.length && (
          <p className="cmd-muted">Investigando tendencias en redes según tu perfil…</p>
        )}

        {visibleTrendCards.length > 0 && (
          <div className="cmd-trends__grid">
            {visibleTrendCards.map((card) => (
              <article key={card.id} className="cmd-trend-card">
                <div className="cmd-trend-card__meta">
                  <span className="cmd-trend-card__source">
                    <span className={`cmd-trend-card__icon cmd-trend-card__icon--${card.platformKey}`} aria-hidden="true">
                      <PlatformBrandIcon platform={card.platformKey} />
                    </span>
                    {card.platform}
                  </span>
                  <span className="cmd-trend-card__age">{card.age}</span>
                </div>

                <h4 className="cmd-trend-card__title">{card.title}</h4>

                <div className="cmd-trend-card__stats">
                  {card.growthPct != null ? (
                    <span className="cmd-trend-card__growth">
                      Crecimiento <strong>↑ {card.growthPct}%</strong>
                    </span>
                  ) : card.urgency ? (
                    <span className={`cmd-trend-card__urgency cmd-trend-card__urgency--${String(card.urgency).toLowerCase()}`}>
                      Urgencia <i aria-hidden="true" /> <strong>{card.urgency}</strong>
                    </span>
                  ) : (
                    <span className="cmd-trend-card__urgency cmd-trend-card__urgency--media">
                      Urgencia <i aria-hidden="true" /> <strong>Media</strong>
                    </span>
                  )}
                </div>

                {card.tags?.length > 0 && (
                  <div className="cmd-trend-card__tags">
                    {card.tags.map((t) => (
                      <span key={t} className="cmd-tag cmd-tag--muted">{t}</span>
                    ))}
                  </div>
                )}

                <div className="cmd-trend-card__foot">
                  {card.article ? (
                    <button type="button" className="cmd-linkish" onClick={() => selectOpportunity(card.article)}>
                      Ver análisis <ArrowRight size={13} />
                    </button>
                  ) : card.url ? (
                    <a className="cmd-linkish" href={card.url} target="_blank" rel="noopener noreferrer">
                      Ver análisis <ArrowRight size={13} />
                    </a>
                  ) : (
                    <button type="button" className="cmd-linkish" onClick={() => onOpenLive?.()}>
                      Ver análisis <ArrowRight size={13} />
                    </button>
                  )}
                  <button
                    type="button"
                    className="cmd-trend-card__create"
                    disabled={creatingTrendId === card.id}
                    onClick={() => handleCreateTrendContent(card)}
                  >
                    {creatingTrendId === card.id ? 'Abriendo…' : 'Crear contenido'}
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}

        {filteredTrendCards.length > 8 && (
          <div className="cmd-trends__more">
            <button
              type="button"
              className="cmd-linkish"
              onClick={() => setTrendsExpanded((v) => !v)}
            >
              {trendsExpanded ? 'Ver menos' : 'Ver más señales'} <ArrowRight size={14} />
            </button>
          </div>
        )}

        <aside className="cmd-social-notes" aria-label="Notas para redes sociales">
          <div className="cmd-social-notes__head">
            <Megaphone size={18} aria-hidden="true" />
            <div>
              <h3 className="cmd-social-notes__title">
                Notas importantes para insertar en mis redes
              </h3>
              <p className="cmd-social-notes__sub">
                Copy listo + dónde poner el CTA + imagen por plataforma, anclado a señales del día.
              </p>
            </div>
          </div>
          <ul className="cmd-social-notes__list">
            {socialNotes.map((note) => {
              const revealedUrl = revealedImages[note.key] || null;
              const img = resolveMediaUrl(revealedUrl);
              const creating = imageBusyKey === note.key;
              const imgError = imageErrorByKey[note.key];
              const copyText = [note.hook, note.post, note.cta].filter(Boolean).join('\n\n');
              return (
                <li key={note.key} className="cmd-social-notes__item">
                  <div className="cmd-social-notes__item-head">
                    <span className={`cmd-trend-card__icon cmd-trend-card__icon--${note.key}`} aria-hidden="true">
                      <PlatformBrandIcon platform={note.key} />
                    </span>
                    <div className="cmd-social-notes__meta">
                      <strong>{note.label}</strong>
                      {note.format && <span className="cmd-social-notes__format">{note.format}</span>}
                      {note.urgency && (
                        <span className={`cmd-social-notes__urgency cmd-social-notes__urgency--${String(note.urgency).toLowerCase()}`}>
                          {note.urgency}
                        </span>
                      )}
                    </div>
                  </div>

                  {note.newsTitle && (
                    <p className="cmd-social-notes__news">
                      <span>Señal:</span>{' '}
                      {note.newsUrl ? (
                        <a href={note.newsUrl} target="_blank" rel="noopener noreferrer">
                          {note.newsTitle} <ExternalLink size={12} />
                        </a>
                      ) : (
                        note.newsTitle
                      )}
                    </p>
                  )}

                  <div className="cmd-social-notes__grid">
                    <div className="cmd-social-notes__copy">
                      {note.hook && (
                        <div className="cmd-social-notes__field">
                          <span>Gancho</span>
                          <p>{note.hook}</p>
                        </div>
                      )}
                      {note.post && (
                        <div className="cmd-social-notes__field">
                          <span>Copy para publicar</span>
                          <p className="cmd-social-notes__post">{note.post}</p>
                        </div>
                      )}
                      {note.cta && (
                        <div className="cmd-social-notes__field">
                          <span>CTA</span>
                          <p>{note.cta}</p>
                        </div>
                      )}
                      <div className="cmd-social-notes__field-row">
                        {note.where && (
                          <div className="cmd-social-notes__field">
                            <span>Dónde insertar</span>
                            <p>{note.where}</p>
                          </div>
                        )}
                        {note.avoid && (
                          <div className="cmd-social-notes__field">
                            <span>Evitar</span>
                            <p>{note.avoid}</p>
                          </div>
                        )}
                      </div>
                      <div className="cmd-social-notes__actions">
                        <button
                          type="button"
                          className="btn btn-secondary"
                          onClick={async () => {
                            try {
                              await navigator.clipboard.writeText(copyText);
                              setCopiedNoteKey(note.key);
                              window.setTimeout(() => setCopiedNoteKey((k) => (k === note.key ? null : k)), 1800);
                            } catch {
                              /* ignore */
                            }
                          }}
                        >
                          {copiedNoteKey === note.key ? <Check size={14} /> : <Copy size={14} />}
                          {copiedNoteKey === note.key ? 'Copiado' : 'Copiar copy'}
                        </button>
                        {img && (
                          <a className="btn btn-secondary" href={img} download={`${note.key}-hoy.png`} target="_blank" rel="noopener noreferrer">
                            <Download size={14} />
                            Descargar imagen
                          </a>
                        )}
                      </div>
                    </div>
                    <div className={`cmd-social-notes__visual cmd-social-notes__visual--${note.key}`}>
                      {img ? (
                        <div className="cmd-social-notes__visual-ready">
                          <img src={img} alt={`Creatividad ${note.label}`} loading="lazy" />
                          <button
                            type="button"
                            className="btn btn-secondary cmd-social-notes__regen"
                            disabled={creating || Boolean(imageBusyKey)}
                            onClick={() => handleCreateNoteImage(note.key)}
                          >
                            {creating ? 'Regenerando…' : 'Regenerar imagen'}
                          </button>
                        </div>
                      ) : (
                        <div className="cmd-social-notes__visual-empty">
                          <p>Imagen {note.format ? `(${note.format})` : ''} lista para crear</p>
                          <button
                            type="button"
                            className="btn btn-primary"
                            disabled={creating || Boolean(imageBusyKey) || !onGenerateAdNoteImage}
                            onClick={() => handleCreateNoteImage(note.key)}
                          >
                            <ImagePlus size={16} aria-hidden="true" />
                            {creating ? 'Creando imagen…' : 'Crear imagen'}
                          </button>
                          {imgError && <span className="cmd-social-notes__img-error">{imgError}</span>}
                        </div>
                      )}
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
        </aside>

        {remainingArticles.length > 0 && (
          <div className="cmd-alts">
            <h4 className="cmd-alts__title">Otras oportunidades priorizadas</h4>
            <ul className="cmd-alts__list">
              {remainingArticles.slice(0, 8).map((art) => {
                const id = articleKey(art);
                const rank = ranked.findIndex((a) => String(articleKey(a)) === String(id)) + 1;
                const isActive = String(articleKey(leadArticle)) === String(id);
                return (
                  <li
                    key={id}
                    className={`cmd-alts__row${isActive ? ' is-active' : ''}`}
                    role="button"
                    tabIndex={0}
                    aria-pressed={isActive}
                    aria-label={`Ver oportunidad #${rank}: ${art.title}`}
                    onClick={() => selectOpportunity(art)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        selectOpportunity(art);
                      }
                    }}
                  >
                    <span className="score-tag">#{rank || '—'}</span>
                    <div className="cmd-alts__copy">
                      <strong>{art.title}</strong>
                      <span>
                        {art.source_name || 'Fuente'} · {Math.round(art.top10_score ?? art.total_score ?? 0)}/100
                        {' · '}
                        Clic para expandir
                      </span>
                    </div>
                    <button
                      type="button"
                      className="btn btn-primary"
                      onClick={(e) => {
                        e.stopPropagation();
                        onUseSuggestion?.(art);
                      }}
                    >
                      Crear
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>
        )}
      </section>

      <div className="cmd-hoy__footer-actions">
        <button type="button" className="btn btn-secondary" disabled={busy} onClick={onPatrol}>
          <Search size={14} />
          {isSearching ? 'Patrullando…' : 'Patrullar tipologías'}
        </button>
      </div>
    </section>
  );
}

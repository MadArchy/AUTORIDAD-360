import React, { useMemo, useState } from 'react';
import {
  ArrowRight,
  BarChart3,
  Check,
  ExternalLink,
  Globe2,
  Plus,
  RefreshCw,
  Search,
  X,
} from 'lucide-react';

const PLATFORM_LABELS = {
  linkedin: 'LinkedIn',
  youtube: 'YouTube',
  x: 'X / Twitter',
  tiktok: 'TikTok',
  instagram: 'Instagram',
  web: 'Web',
  regulacion: 'Regulación',
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
  // Fallback proporcional al total cuando aún no hay desglose LLM
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
  if (!iso) return 'Reciente';
  try {
    const mins = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
    if (mins < 60) return `${mins || 1} min`;
    const hours = Math.round(mins / 60);
    if (hours < 48) return `${hours} h`;
    return `${Math.round(hours / 24)} d`;
  } catch {
    return 'Reciente';
  }
}

/**
 * Centro de mando editorial — descubrimiento del día.
 */
export default function HoyTab({
  top10 = [],
  onUseSuggestion,
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
  onOpenSources,
  onRefreshIntelligence,
  intelligenceBusy = false,
  signalsCount = 0,
  flowCounts = null,
  onOpenLive,
}) {
  const [dismissed, setDismissed] = useState(() => new Set());
  const [analysisOpen, setAnalysisOpen] = useState(true);

  const ranked = useMemo(
    () => (top10 || []).filter((a) => !dismissed.has(a.id || a.article_id)),
    [top10, dismissed]
  );
  const leadArticle = ranked[0];
  const remainingArticles = ranked.slice(1, 10);
  const trends = adTrendNotes?.trends || [];
  const busy = intelligenceBusy || loadingTop10 || isSearching || adTrendBusy;

  const leadScore = Number(leadArticle?.top10_score ?? leadArticle?.total_score) || 0;
  const leadScores = leadArticle?.scores || {};
  const reasons = leadArticle ? buildReasons(leadArticle, leadScores) : [];
  const tags = leadArticle ? buildTags(leadArticle) : [];

  const refreshAll = () => {
    if (onRefreshIntelligence) onRefreshIntelligence();
    else {
      onRefreshTop10?.();
      onPatrol?.();
      onGenerateAdTrendNotes?.();
    }
  };

  const trendCards = useMemo(() => {
    if (trends.length) {
      return trends.slice(0, 4).map((t, i) => ({
        id: `trend-${i}`,
        platform: PLATFORM_LABELS[t.platform] || t.platform || 'Web',
        title: t.summary || t.title || t.theme || 'Tendencia detectada',
        age: t.detected_at ? relativeAge(t.detected_at) : (adTrendNotes?.generated_at ? relativeAge(adTrendNotes.generated_at) : 'Hoy'),
        growth: t.growth_pct != null ? `↑ ${Math.round(Number(t.growth_pct))}%` : null,
        mentions: t.mentions != null ? `${Number(t.mentions).toLocaleString('es-CO')} menciones` : (t.theme || null),
        tags: [t.theme, t.market].filter(Boolean).slice(0, 2),
        url: (t.urls && t.urls[0]) || null,
      }));
    }
    return remainingArticles.slice(0, 4).map((art, i) => ({
      id: art.id || art.article_id || `sig-${i}`,
      platform: art.source_name || 'Señal',
      title: art.title,
      age: relativeAge(art.published_at),
      growth: art.top10_score || art.total_score ? `${Math.round(art.top10_score ?? art.total_score)}/100` : null,
      mentions: art.matched_pillar_name || art.matched_pillar || null,
      tags: [art.category, art.matched_pillar_name || art.matched_pillar].filter(Boolean).slice(0, 2),
      url: art.source_url || art.url || null,
      article: art,
    }));
  }, [trends, remainingArticles, adTrendNotes]);

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
          <strong>Aún no hay ranking</strong>
          <span>Actualiza la inteligencia o patrulla tipologías para encontrar una señal editorial.</span>
          <button type="button" className="btn btn-primary" disabled={busy} onClick={refreshAll}>
            Actualizar inteligencia
          </button>
        </div>
      )}

      {leadArticle && (
        <article className="cmd-priority">
          <div className="cmd-priority__top">
            <span className="cmd-priority__eyebrow">Recomendación prioritaria</span>
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
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setAnalysisOpen(true)}
            >
              <BarChart3 size={15} aria-hidden="true" />
              Ver análisis
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
                const id = leadArticle.id || leadArticle.article_id;
                setDismissed((prev) => new Set(prev).add(id));
              }}
            >
              <X size={15} aria-hidden="true" />
              Descartar
            </button>
          </div>
        </article>
      )}

      <section className="cmd-trends">
        <div className="cmd-trends__head">
          <div>
            <span className="cmd-trends__pulse" aria-hidden="true" />
            <h3 className="cmd-trends__title">Tendencias y señales</h3>
          </div>
          <button type="button" className="cmd-linkish" onClick={() => onOpenLive?.()}>
            Ver todas las señales <ArrowRight size={14} />
          </button>
        </div>

        {adTrendBusy && !trendCards.length && (
          <p className="cmd-muted">Investigando tendencias en redes según tu perfil…</p>
        )}

        {!adTrendBusy && !trendCards.length && (
          <p className="cmd-muted">
            {adTrendMessage || 'Actualiza la inteligencia para ver tendencias y señales prioritarias.'}
          </p>
        )}

        {trendCards.length > 0 && (
          <div className="cmd-trends__grid">
            {trendCards.map((card) => (
              <article key={card.id} className="cmd-trend-card">
                <div className="cmd-trend-card__meta">
                  <span>{card.platform}</span>
                  <span>{card.age}</span>
                </div>
                <h4 className="cmd-trend-card__title">{card.title}</h4>
                <div className="cmd-trend-card__stats">
                  {card.growth ? <span className="cmd-trend-card__growth">{card.growth}</span> : null}
                  {card.mentions ? <span>{card.mentions}</span> : null}
                </div>
                {card.tags?.length > 0 && (
                  <div className="cmd-priority__tags">
                    {card.tags.map((t) => (
                      <span key={t} className="cmd-tag cmd-tag--muted">{t}</span>
                    ))}
                  </div>
                )}
                <div className="cmd-trend-card__foot">
                  {card.article ? (
                    <button type="button" className="cmd-linkish" onClick={() => onUseSuggestion?.(card.article)}>
                      Crear en Estudio <ArrowRight size={13} />
                    </button>
                  ) : card.url ? (
                    <a className="cmd-linkish" href={card.url} target="_blank" rel="noopener noreferrer">
                      Ver señales <ArrowRight size={13} />
                    </a>
                  ) : (
                    <button type="button" className="cmd-linkish" onClick={() => onOpenLive?.()}>
                      Ver señales <ArrowRight size={13} />
                    </button>
                  )}
                </div>
              </article>
            ))}
          </div>
        )}

        {remainingArticles.length > 4 && trends.length > 0 && (
          <div className="cmd-alts">
            <h4 className="cmd-alts__title">Otras oportunidades priorizadas</h4>
            <ul className="cmd-alts__list">
              {remainingArticles.slice(0, 5).map((art, idx) => (
                <li key={art.id || art.article_id} className="cmd-alts__row">
                  <span className="score-tag">#{idx + 2}</span>
                  <div className="cmd-alts__copy">
                    <strong>{art.title}</strong>
                    <span>
                      {art.source_name || 'Fuente'} · {Math.round(art.top10_score ?? art.total_score ?? 0)}/100
                    </span>
                  </div>
                  <button type="button" className="btn btn-primary" onClick={() => onUseSuggestion?.(art)}>
                    Crear
                  </button>
                </li>
              ))}
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

import React from 'react';
import { Layers, ExternalLink, Search } from 'lucide-react';

/**
 * Única pantalla de descubrimiento: ranking del perfil.
 */
export default function HoyTab({
  deficitPillars = [],
  top10 = [],
  onUseSuggestion,
  onRefreshTop10,
  onPatrol,
  loadingTop10 = false,
  isSearching = false,
}) {
  return (
    <section className="hoy-panel glass-panel">
      <header className="hoy-hero" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '16px', flexWrap: 'wrap' }}>
        <div>
          <h2 className="hoy-title">Hoy</h2>
          <p className="hoy-lede">
            Noticias priorizadas para el perfil. Elige una, genera y publica.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          <button type="button" className="btn btn-secondary" disabled={loadingTop10 || isSearching} onClick={onRefreshTop10}>
            {loadingTop10 ? 'Actualizando…' : 'Actualizar ranking'}
          </button>
          <button type="button" className="btn" disabled={loadingTop10 || isSearching} onClick={onPatrol}>
            <Search size={14} style={{ marginRight: 6 }} />
            {isSearching ? 'Patrullando…' : 'Patrullar tipologías'}
          </button>
        </div>
      </header>

      {deficitPillars.length > 0 && (
        <div className="hoy-quota" style={{ marginBottom: '16px' }}>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '8px' }}>
            <Layers size={14} style={{ verticalAlign: 'middle', marginRight: 6 }} />
            Pilares bajo meta (boost activo):
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
            {deficitPillars.map((p) => (
              <span key={p.slug} className="status-badge status-pending" style={{ fontSize: '0.78rem' }}>
                {p.name} (−{Number(p.deficit_pct).toFixed(0)}%)
              </span>
            ))}
          </div>
        </div>
      )}

      <h3 style={{ fontSize: '1.05rem', fontWeight: 800, marginBottom: '12px' }}>Top noticias del perfil</h3>

      {!top10?.length && (
        <p style={{ color: 'var(--text-secondary)', marginBottom: '20px' }}>
          Aún no hay ranking. Usa “Actualizar fuentes” arriba o “Patrullar tipologías”.
        </p>
      )}

      {top10?.length > 0 && (
        <ol style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {top10.slice(0, 10).map((art, idx) => (
            <li
              key={art.id || art.article_id}
              className="glass-card"
              style={{ padding: '14px 16px', display: 'grid', gridTemplateColumns: 'auto 1fr auto', gap: '12px', alignItems: 'center' }}
            >
              <span className="score-tag" style={{ minWidth: '52px', textAlign: 'center' }}>
                #{idx + 1}
              </span>
              <div style={{ minWidth: 0 }}>
                <strong style={{ fontSize: '0.95rem', display: 'block', lineHeight: 1.35 }}>{art.title}</strong>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '6px', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    {art.source_name || 'Fuente'} · {art.top10_score ?? art.total_score}/100
                  </span>
                  {(art.matched_pillar_name || art.matched_pillar || art.category) && (
                    <span className="status-badge status-verified" style={{ fontSize: '0.7rem' }}>
                      {art.matched_pillar_name || art.matched_pillar || art.category}
                    </span>
                  )}
                  {art.quota_priority && (
                    <span className="status-badge status-pending" style={{ fontSize: '0.7rem' }}>
                      Prioridad cuota
                    </span>
                  )}
                  {art.status && art.status !== 'verified' && (
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{art.status}</span>
                  )}
                </div>
              </div>
              <div style={{ display: 'flex', gap: '6px', flexShrink: 0 }}>
                <button type="button" className="btn btn-primary" onClick={() => onUseSuggestion?.(art)}>
                  Usar
                </button>
                {art.url || art.source_url ? (
                  <a
                    href={art.url || art.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn btn-secondary"
                    style={{ padding: '8px 10px', textDecoration: 'none' }}
                    aria-label="Abrir fuente"
                  >
                    <ExternalLink size={14} />
                  </a>
                ) : null}
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

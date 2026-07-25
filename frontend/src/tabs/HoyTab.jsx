import React, { useState } from 'react';
import { Layers, ExternalLink, Search, Megaphone, RefreshCw, ChevronDown, ChevronUp } from 'lucide-react';

const PLATFORM_LABELS = {
  linkedin: 'LinkedIn',
  youtube: 'YouTube',
  x: 'X / Twitter',
  tiktok: 'TikTok',
  instagram: 'Instagram',
};

/**
 * Única pantalla de descubrimiento: ranking del perfil + notas de tendencias/publicidad.
 */
export default function HoyTab({
  deficitPillars = [],
  top10 = [],
  onUseSuggestion,
  onRefreshTop10,
  onPatrol,
  loadingTop10 = false,
  isSearching = false,
  adTrendNotes = null,
  adTrendMessage = null,
  adTrendBusy = false,
  onRefreshAdTrendNotes,
  onGenerateAdTrendNotes,
}) {
  const [notesOpen, setNotesOpen] = useState(true);
  const trends = adTrendNotes?.trends || [];
  const formats = adTrendNotes?.formats_working || [];
  const adNotes = adTrendNotes?.ad_notes || [];
  const hasNotes = Boolean(adTrendNotes && (trends.length || adNotes.length));

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

      <div className="glass-card" style={{ padding: '14px 16px', marginBottom: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          <button
            type="button"
            onClick={() => setNotesOpen((v) => !v)}
            style={{
              background: 'none',
              border: 'none',
              padding: 0,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              color: 'inherit',
              textAlign: 'left',
            }}
          >
            <Megaphone size={16} />
            <strong style={{ fontSize: '1.05rem' }}>Notas · tendencias y publicidad</strong>
            {notesOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            <button
              type="button"
              className="btn btn-secondary"
              disabled={adTrendBusy}
              onClick={onRefreshAdTrendNotes}
            >
              Recargar
            </button>
            <button
              type="button"
              className="btn btn-primary"
              disabled={adTrendBusy}
              onClick={onGenerateAdTrendNotes}
            >
              <RefreshCw size={14} style={{ marginRight: 6 }} />
              {adTrendBusy ? 'Investigando redes…' : 'Actualizar notas'}
            </button>
          </div>
        </div>

        {notesOpen && (
          <div style={{ marginTop: '14px' }}>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '12px' }}>
              Sugerencias editoriales orgánicas para tus redes (LinkedIn, YouTube, X, TikTok, Instagram).
              No son compra de anuncios pagados.
            </p>

            {adTrendBusy && (
              <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                Buscando tendencias en redes según los temas del perfil…
              </p>
            )}

            {!adTrendBusy && !hasNotes && (
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                {adTrendMessage || 'Genera notas según tu perfil para ver tendencias y dónde insertar CTAs.'}
              </p>
            )}

            {adTrendNotes?.generated_at && (
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '10px' }}>
                Actualizado: {new Date(adTrendNotes.generated_at).toLocaleString()}
                {(adTrendNotes.meta?.hits_count != null) ? ` · ${adTrendNotes.meta.hits_count} hallazgos` : ''}
              </p>
            )}

            {trends.length > 0 && (
              <div style={{ marginBottom: '16px' }}>
                <h4 style={{ fontSize: '0.9rem', marginBottom: '8px' }}>Tendencias detectadas</h4>
                <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {trends.map((t, i) => (
                    <li key={`${t.platform}-${i}`} style={{ fontSize: '0.88rem', lineHeight: 1.4 }}>
                      <span className="status-badge status-verified" style={{ fontSize: '0.68rem', marginRight: 6 }}>
                        {PLATFORM_LABELS[t.platform] || t.platform || 'Red'}
                      </span>
                      {t.theme ? <em style={{ color: 'var(--text-muted)', marginRight: 6 }}>{t.theme} ·</em> : null}
                      {t.summary || t.title || '—'}
                      <span style={{ display: 'inline-flex', gap: 6, marginLeft: 8, flexWrap: 'wrap' }}>
                        {(t.urls || []).slice(0, 2).map((u) => (
                          <a key={u} href={u} target="_blank" rel="noopener noreferrer" aria-label="Abrir ejemplo">
                            <ExternalLink size={12} />
                          </a>
                        ))}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {formats.length > 0 && (
              <div style={{ marginBottom: '16px' }}>
                <h4 style={{ fontSize: '0.9rem', marginBottom: '8px' }}>Formatos que encajan</h4>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                  {formats.map((f, i) => (
                    <span key={i} className="status-badge status-pending" style={{ fontSize: '0.75rem' }} title={f.why || ''}>
                      {f.format}{f.platform ? ` · ${PLATFORM_LABELS[f.platform] || f.platform}` : ''}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {adNotes.length > 0 && (
              <div>
                <h4 style={{ fontSize: '0.9rem', marginBottom: '8px' }}>Dónde / cómo insertar el CTA</h4>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '10px' }}>
                  {adNotes.map((n) => (
                    <div
                      key={n.platform}
                      style={{
                        border: '1px solid var(--border-subtle, rgba(0,0,0,0.08))',
                        borderRadius: '8px',
                        padding: '12px',
                        background: 'var(--surface-2, transparent)',
                      }}
                    >
                      <strong style={{ fontSize: '0.85rem', display: 'block', marginBottom: '8px' }}>
                        {PLATFORM_LABELS[n.platform] || n.platform}
                      </strong>
                      <p style={{ fontSize: '0.78rem', margin: '0 0 6px', color: 'var(--text-secondary)' }}>
                        <strong>Dónde:</strong> {n.where}
                      </p>
                      <p style={{ fontSize: '0.78rem', margin: '0 0 6px', color: 'var(--text-secondary)' }}>
                        <strong>Cómo:</strong> {n.how}
                      </p>
                      <p style={{ fontSize: '0.78rem', margin: 0, color: 'var(--text-muted)' }}>
                        <strong>Evitar:</strong> {n.avoid}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

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

import React, { useState } from 'react';
import { Search, Layers, ExternalLink, MoreHorizontal } from 'lucide-react';

/**
 * Paso 1 — Elegir noticia (al usarla se generan formatos).
 */
export default function Top10Tab({
  top10,
  loading,
  isSearching,
  onRecalculate,
  onPatrol,
  onDerive,
  onNotify,
  goToTab,
}) {
  const [showMore, setShowMore] = useState(false);

  return (
    <section className="glass-panel" style={{ padding: '24px' }}>
      <div className="flow-step-banner">
        <span>Paso 1 de 3 · Elegir y generar</span>
        <button type="button" className="btn btn-secondary" onClick={() => goToTab?.('hoy')}>
          Ver Hoy
        </button>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px', gap: '12px', flexWrap: 'wrap' }}>
        <div>
          <h2 style={{ fontSize: '1.35rem', fontWeight: 800, marginBottom: '6px' }}>Elige una noticia</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', margin: 0 }}>
          Al usar una noticia, autorizas generar LinkedIn, video, carrusel y newsletter.
        </p>
        </div>
        <div style={{ position: 'relative' }}>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => setShowMore((v) => !v)}
            aria-expanded={showMore}
          >
            <MoreHorizontal size={16} /> Más acciones
          </button>
          {showMore && (
            <div className="more-actions-menu">
              <button
                type="button"
                className="more-actions-item"
                disabled={loading || isSearching}
                onClick={() => {
                  setShowMore(false);
                  onPatrol?.();
                }}
              >
                <Search size={14} />
                {isSearching ? 'Patrullando…' : 'Patrullar tipologías'}
              </button>
              <button
                type="button"
                className="more-actions-item"
                disabled={loading || isSearching}
                onClick={() => {
                  setShowMore(false);
                  onRecalculate?.();
                }}
              >
                Recalcular scoring
              </button>
            </div>
          )}
        </div>
      </div>

      {!top10?.length && (
        <p style={{ color: 'var(--text-secondary)' }}>
          Aún no hay Top 10. Usa “Actualizar fuentes” arriba o recalcular desde Más acciones.
        </p>
      )}

      <div className="grid-cards">
        {top10.map((art, idx) => (
          <div key={art.id} className="glass-card" style={{ padding: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
              <span className="score-tag">
                #{idx + 1} · {art.top10_score}/100
              </span>
              <span className={`status-badge status-${art.verification_status}`}>
                {art.verification_status}
              </span>
            </div>

            <h3 style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: '8px', lineHeight: 1.4 }}>
              {art.title}
            </h3>

            <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '12px' }}>
              {art.source_name}
              {art.category ? ` · ${String(art.category).replace(/_/g, ' ')}` : ''}
            </div>

            <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', marginBottom: '16px', lineHeight: 1.5 }}>
              {art.content_full
                ? `${art.content_full.substring(0, 160)}...`
                : 'Sin vista previa disponible.'}
            </p>

            <div style={{ display: 'flex', gap: '8px', marginTop: 'auto' }}>
              <button
                className="btn btn-primary"
                style={{ flex: 1, padding: '8px 12px', fontSize: '0.85rem' }}
                onClick={() => {
                  const title = (art.title || '').toLowerCase();
                  if (
                    title.includes('shipping') ||
                    title.includes('incoterm') ||
                    title.includes('global business navigator') ||
                    title.includes('acd_test')
                  ) {
                    onNotify?.(
                      'Elige una noticia de tipología IA (regulación, legal, PI, ciber…).',
                      'warn'
                    );
                    return;
                  }
                  onDerive?.(art);
                }}
              >
                <Layers size={14} /> Usar esta noticia
              </button>
              <a
                href={art.url}
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-secondary"
                aria-label={`Abrir fuente: ${art.title}`}
                style={{ padding: '8px 10px', textDecoration: 'none' }}
              >
                <ExternalLink size={14} />
              </a>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

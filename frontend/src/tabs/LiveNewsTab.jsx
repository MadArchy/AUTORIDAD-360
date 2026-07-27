import React, { useState } from 'react';
import { Search, ArrowUpRight, ExternalLink, Sparkles, Newspaper } from 'lucide-react';
import AICopilotDrawer from '../components/AICopilotDrawer';

const STATUS_LABELS = {
  collected: 'Recolectada',
  classified: 'Clasificada',
  verified: 'Verificada',
  approved: 'Aprobada',
  published: 'Publicada',
  rejected: 'Rechazada',
  pending: 'Pendiente',
};

function statusClass(status) {
  const key = String(status || '').toLowerCase();
  if (key === 'verified' || key === 'approved' || key === 'published') return 'status-verified';
  if (key === 'rejected') return 'status-rejected';
  return 'status-pending';
}

function formatDate(value) {
  if (!value) return 'Sin fecha';
  try {
    return new Date(value).toLocaleDateString('es-CO', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  } catch {
    return 'Sin fecha';
  }
}

export default function LiveNewsTab({
  categories = [],
  selectedCategory,
  setSelectedCategory,
  searchQuery,
  onSearchInput,
  articles = [],
  articlesTotalHint,
  isBusy,
  fetchError = '',
  onFetchArticles,
  onUseInFlow,
  workedArticleIds,
  onClearFilters,
}) {
  const [copilotArticle, setCopilotArticle] = useState(null);
  const searching = isBusy?.('search');
  const totalAll = categories.reduce((acc, c) => acc + (c.count || 0), 0);
  const resultCount = articlesTotalHint ?? articles.length;
  const hasFilters = Boolean(searchQuery || selectedCategory);
  const isWorked = (art) => {
    const id = Number(art?.id ?? art?.article_id);
    if (!Number.isFinite(id) || !workedArticleIds) return false;
    return typeof workedArticleIds.has === 'function'
      ? workedArticleIds.has(id)
      : Boolean(workedArticleIds[id]);
  };

  const selectCategory = (value) => {
    setSelectedCategory(value);
    onFetchArticles(value, searchQuery);
  };

  return (
    <section className="live-news glass-panel">
      <AICopilotDrawer
        isOpen={Boolean(copilotArticle)}
        onClose={() => setCopilotArticle(null)}
        targetItem={copilotArticle}
        itemType="article"
        onApplyRefinement={(newContent) => {
          if (copilotArticle) {
            copilotArticle.full_text = newContent;
          }
        }}
      />

      <header className="page-header live-news__header">
        <div>
          <span className="page-eyebrow">Inventario editorial</span>
          <h2 className="page-title">Noticias en vivo</h2>
          <p className="page-description">
            Escanea el inventario, filtra por tipología y lleva la señal más clara al Estudio.
          </p>
        </div>
        <div className="live-news__stats">
          <span className="meta-chip">{resultCount} visibles</span>
          {totalAll > 0 && <span className="meta-chip">{totalAll} en base</span>}
        </div>
      </header>

      <div className="live-news__toolbar editorial-card">
        <div className="live-news__search">
          <Search size={16} aria-hidden="true" />
          <input
            type="search"
            placeholder="Buscar título, resumen, fuente o texto…"
            value={searchQuery}
            onChange={(e) => onSearchInput(e.target.value)}
            className="form-control"
            aria-label="Buscar noticias"
          />
          <button
            type="button"
            className="btn btn-secondary"
            disabled={searching}
            onClick={() => onFetchArticles(selectedCategory, searchQuery)}
          >
            {searching ? 'Buscando…' : 'Buscar'}
          </button>
        </div>

        <div className="live-news__filters" role="tablist" aria-label="Categorías">
          <button
            type="button"
            role="tab"
            aria-selected={!selectedCategory}
            className={`live-news__chip ${!selectedCategory ? 'is-active' : ''}`}
            onClick={() => selectCategory('')}
          >
            Todas
            <span>{totalAll || resultCount}</span>
          </button>
          {categories.map((c) => (
            <button
              key={c.category}
              type="button"
              role="tab"
              aria-selected={selectedCategory === c.category}
              className={`live-news__chip ${selectedCategory === c.category ? 'is-active' : ''}`}
              onClick={() => selectCategory(c.category)}
              title={c.display_name}
            >
              {c.display_name}
              <span>{c.count}</span>
            </button>
          ))}
        </div>

        {(hasFilters || searching) && (
          <div className="live-news__toolbar-meta">
            <p>
              {searching
                ? 'Buscando en base de datos…'
                : `${resultCount} resultado${resultCount === 1 ? '' : 's'}${
                    searchQuery ? ` para “${searchQuery}”` : ''
                  }${selectedCategory ? ` · ${selectedCategory}` : ''}`}
            </p>
            {hasFilters && (
              <button type="button" className="btn btn-secondary" onClick={onClearFilters}>
                Limpiar filtros
              </button>
            )}
          </div>
        )}
      </div>

      {fetchError && (
        <div className="status-banner status-banner--error" role="alert">
          <div>
            <strong>No se pudo cargar el inventario</strong>
            <p>{fetchError}</p>
          </div>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => onFetchArticles(selectedCategory, searchQuery)}
          >
            Reintentar
          </button>
        </div>
      )}

      {searching && articles.length === 0 && (
        <div className="live-news__grid" aria-busy="true" aria-label="Cargando noticias">
          {[1, 2, 3, 4].map((n) => (
            <div key={n} className="live-news__card live-news__card--skeleton">
              <div className="skeleton" style={{ width: '28%', height: 18 }} />
              <div className="skeleton" style={{ width: '92%', height: 24, marginTop: 14 }} />
              <div className="skeleton" style={{ width: '78%', height: 14, marginTop: 10 }} />
              <div className="skeleton" style={{ width: '55%', height: 14, marginTop: 8 }} />
            </div>
          ))}
        </div>
      )}

      {!fetchError && !searching && articles.length === 0 && (
        <div className="empty-state">
          <Newspaper size={28} aria-hidden="true" />
          <strong>No hay noticias con ese criterio</strong>
          <span>Prueba otra palabra, limpia los filtros o actualiza las fuentes.</span>
          {hasFilters ? (
            <button type="button" className="btn btn-secondary" onClick={onClearFilters}>
              Limpiar filtros
            </button>
          ) : null}
        </div>
      )}

      {articles.length > 0 && (
        <div className="live-news__grid">
          {articles.map((art) => {
            const status = art.verification_status || art.status;
            const sourceUrl = art.url || art.source_url;
            const worked = isWorked(art);
            return (
              <article
                key={art.id}
                className={`live-news__card${worked ? ' live-news__card--worked' : ''}`}
                data-worked={worked ? 'true' : undefined}
              >
                <div className="live-news__card-top">
                  <span className="score-tag">{art.category || 'sin-categoría'}</span>
                  <div className="live-news__card-flags">
                    {worked ? (
                      <span className="live-news__worked-badge" title="Ya trabajaste esta noticia en Estudio">
                        En Estudio
                      </span>
                    ) : null}
                    <span className={`status-badge ${statusClass(status)}`}>
                      {STATUS_LABELS[status] || status || 'Sin estado'}
                    </span>
                  </div>
                </div>

                <h3 className="live-news__title">{art.title}</h3>

                {(art.summary || art.excerpt) && (
                  <p className="live-news__excerpt">
                    {(art.summary || art.excerpt || '').slice(0, 190)}
                    {(art.summary || art.excerpt || '').length > 190 ? '…' : ''}
                  </p>
                )}

                <div className="live-news__meta">
                  <span>{art.source_name || 'Fuente'}</span>
                  <span>{formatDate(art.published_at)}</span>
                  {(art.news_type_name || art.news_type) && (
                    <span>{art.news_type_name || art.news_type}</span>
                  )}
                </div>

                <div className="live-news__actions">
                  <button
                    type="button"
                    className={worked ? 'btn btn-secondary' : 'btn btn-primary'}
                    onClick={() => onUseInFlow(art)}
                  >
                    <ArrowUpRight size={14} aria-hidden="true" />
                    {worked ? 'Abrir en Estudio' : 'Crear en Estudio'}
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => setCopilotArticle(art)}
                  >
                    <Sparkles size={13} aria-hidden="true" />
                    Copiloto
                  </button>
                  {sourceUrl ? (
                    <a
                      href={sourceUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn btn-secondary"
                    >
                      Fuente <ExternalLink size={12} aria-hidden="true" />
                    </a>
                  ) : null}
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}

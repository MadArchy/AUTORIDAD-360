import React, { useMemo, useState } from 'react';
import {
  Search,
  ArrowUpRight,
  ExternalLink,
  Sparkles,
  Newspaper,
  Eye,
  Database,
} from 'lucide-react';
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

const CAT_TONES = ['blue', 'green', 'purple', 'pink', 'orange', 'cyan', 'amber'];

function statusClass(status) {
  const key = String(status || '').toLowerCase();
  if (key === 'verified' || key === 'approved' || key === 'published') return 'status-verified';
  if (key === 'rejected') return 'status-rejected';
  return 'status-pending';
}

function formatDate(value) {
  if (!value) return 'Sin fecha';
  try {
    return new Date(value).toLocaleDateString('es-MX', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });
  } catch {
    return 'Sin fecha';
  }
}

function categoryTone(name) {
  const raw = String(name || 'x');
  let hash = 0;
  for (let i = 0; i < raw.length; i += 1) hash = (hash + raw.charCodeAt(i) * (i + 1)) % 997;
  return CAT_TONES[hash % CAT_TONES.length];
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

  const toneByCategory = useMemo(() => {
    const map = {};
    for (const c of categories) {
      map[c.category] = categoryTone(c.display_name || c.category);
      map[c.display_name] = map[c.category];
    }
    return map;
  }, [categories]);

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
        </div>
        <div className="live-news__stats">
          <span className="meta-chip meta-chip--stat">
            <Eye size={13} aria-hidden="true" />
            {resultCount} visibles
          </span>
          {totalAll > 0 && (
            <span className="meta-chip meta-chip--stat">
              <Database size={13} aria-hidden="true" />
              {totalAll} en base
            </span>
          )}
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
            onKeyDown={(e) => {
              if (e.key === 'Enter') onFetchArticles(selectedCategory, searchQuery);
            }}
          />
          <button
            type="button"
            className="btn btn-primary"
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
          {categories.map((c) => {
            const tone = toneByCategory[c.category] || 'blue';
            return (
              <button
                key={c.category}
                type="button"
                role="tab"
                aria-selected={selectedCategory === c.category}
                className={`live-news__chip live-news__chip--${tone} ${
                  selectedCategory === c.category ? 'is-active' : ''
                }`}
                onClick={() => selectCategory(c.category)}
                title={c.display_name}
              >
                <i className={`live-news__dot live-news__dot--${tone}`} aria-hidden="true" />
                {c.display_name}
                <span>{c.count}</span>
              </button>
            );
          })}
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
          {[1, 2, 3, 4, 5].map((n) => (
            <div key={n} className="live-news__card live-news__card--skeleton">
              <div className="skeleton" style={{ width: '40%', height: 16 }} />
              <div className="skeleton" style={{ width: '92%', height: 22, marginTop: 14 }} />
              <div className="skeleton" style={{ width: '70%', height: 12, marginTop: 10 }} />
              <div className="skeleton" style={{ width: '100%', height: 36, marginTop: 18 }} />
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
            const catLabel = art.category || 'sin-categoría';
            const tone = toneByCategory[catLabel] || categoryTone(catLabel);
            return (
              <article
                key={art.id}
                className={`live-news__card${worked ? ' live-news__card--worked' : ''}`}
                data-worked={worked ? 'true' : undefined}
              >
                <div className="live-news__card-top">
                  <span className={`live-news__cat live-news__cat--${tone}`}>
                    <i className={`live-news__dot live-news__dot--${tone}`} aria-hidden="true" />
                    {catLabel}
                  </span>
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

                <div className="live-news__meta">
                  <span>{art.source_name || 'Fuente'}</span>
                  <span>{formatDate(art.published_at)}</span>
                </div>

                {(art.summary || art.excerpt) && (
                  <p className="live-news__excerpt">
                    {(art.summary || art.excerpt || '').slice(0, 160)}
                    {(art.summary || art.excerpt || '').length > 160 ? '…' : ''}
                  </p>
                )}

                <div className="live-news__actions">
                  <button
                    type="button"
                    className={worked ? 'btn btn-secondary live-news__cta' : 'btn btn-primary live-news__cta'}
                    onClick={() => onUseInFlow(art)}
                  >
                    {worked ? 'Abrir en Estudio' : 'Crear en Estudio'}
                    <ArrowUpRight size={15} aria-hidden="true" />
                  </button>
                  <div className="live-news__actions-row">
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
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}

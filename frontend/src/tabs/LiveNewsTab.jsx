import React, { useState } from 'react';
import { Search, ArrowUpRight, ExternalLink, Sparkles } from 'lucide-react';
import AICopilotDrawer from '../components/AICopilotDrawer';

export default function LiveNewsTab({
  categories,
  selectedCategory,
  setSelectedCategory,
  searchQuery,
  onSearchInput,
  articles,
  articlesTotalHint,
  isBusy,
  onFetchArticles,
  onUseInFlow,
  onClearFilters,
}) {
  const [copilotArticle, setCopilotArticle] = useState(null);

  return (
    <section className="glass-panel" style={{ padding: '24px' }}>
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
      <div style={{ display: 'flex', gap: '16px', marginBottom: '12px', flexWrap: 'wrap', alignItems: 'center' }}>
        <select
          value={selectedCategory}
          onChange={(e) => {
            setSelectedCategory(e.target.value);
            onFetchArticles(e.target.value, searchQuery);
          }}
          style={{ padding: '10px 16px', borderRadius: '8px', background: 'var(--bg-card)', color: '#FFF', border: '1px solid rgba(255,255,255,0.1)' }}
        >
          <option value="">Todas las categorías ({categories.reduce((acc, c) => acc + c.count, 0)})</option>
          {categories.map((c) => (
            <option key={c.category} value={c.category}>{c.display_name} ({c.count})</option>
          ))}
        </select>

        <input
          type="text"
          placeholder="Buscar en título, resumen, fuente o texto…"
          value={searchQuery}
          onChange={(e) => onSearchInput(e.target.value)}
          style={{ flex: 1, minWidth: '240px', padding: '10px 16px', borderRadius: '8px', background: 'var(--bg-card)', color: '#FFF', border: '1px solid rgba(255,255,255,0.1)' }}
        />
        <button
          className="btn btn-secondary"
          disabled={isBusy('search')}
          onClick={() => onFetchArticles(selectedCategory, searchQuery)}
        >
          <Search size={14} /> {isBusy('search') ? 'Buscando…' : 'Buscar'}
        </button>
        {(searchQuery || selectedCategory) && (
          <button
            className="btn btn-secondary"
            onClick={() => {
              onClearFilters?.();
            }}
          >
            Limpiar
          </button>
        )}
      </div>
      <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '16px' }}>
        {isBusy('search')
          ? 'Buscando en base de datos…'
          : `${articlesTotalHint ?? articles.length} resultado(s)${searchQuery ? ` para “${searchQuery}”` : ''}${selectedCategory ? ` · categoría ${selectedCategory}` : ''}`}
      </p>

      <div className="grid-cards">
        {articles.length === 0 && !isBusy('search') && (
          <div className="glass-card" style={{ padding: '24px', color: 'var(--text-secondary)' }}>
            No hay noticias con ese criterio. Prueba otra palabra, limpia filtros o pulsa Recolectar RSS / Patrullar Web.
          </div>
        )}
        {articles.map((art) => (
          <div key={art.id} className="glass-card" style={{ padding: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
              <span className="score-tag">{art.category}</span>
              <span className={`status-badge status-${art.verification_status}`}>{art.verification_status}</span>
            </div>
            <h4 style={{ fontSize: '0.98rem', fontWeight: 600, marginBottom: '8px' }}>{art.title}</h4>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: '12px' }}>
              {art.source_name} • {art.published_at ? new Date(art.published_at).toLocaleDateString() : 'Sin fecha'}
              {art.news_type_name ? ` • ${art.news_type_name}` : art.news_type ? ` • ${art.news_type}` : ''}
            </p>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              <button
                className="btn btn-primary"
                style={{ padding: '6px 10px', fontSize: '0.78rem' }}
                onClick={() => onUseInFlow(art)}
              >
                <ArrowUpRight size={14} /> Usar en flujo
              </button>
              <button
                className="btn btn-secondary"
                style={{ padding: '6px 10px', fontSize: '0.78rem', background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(168, 85, 247, 0.2))', border: '1px solid rgba(168, 85, 247, 0.4)' }}
                onClick={() => setCopilotArticle(art)}
              >
                <Sparkles size={13} color="#a855f7" /> Copiloto IA
              </button>
              <a href={art.url} target="_blank" rel="noopener noreferrer" className="btn btn-secondary" style={{ padding: '6px 10px', fontSize: '0.78rem', textDecoration: 'none' }}>
                Fuente <ExternalLink size={12} />
              </a>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

import React from 'react';
import { CheckCircle2, XCircle, ExternalLink, Sparkles } from 'lucide-react';

export default function ApprovalTab({
  selectedArticleForApproval,
  goToTab,
  handleApproveArticle,
  handleRejectArticle,
  pendingBlogPosts,
  approvePendingBlog,
  publishPendingBlog,
  parseSummaryJson,
  triggerAnalyzeArticle,
  loading,
}) {
  return (
    <>
{!selectedArticleForApproval && (
        <section className="glass-panel" style={{ padding: '24px' }}>
          <div className="flow-step-banner">
            <span>Paso 3 de 4 · Aprobar</span>
            <button type="button" className="btn btn-secondary" onClick={() => goToTab('hoy')}>
              Ver Hoy
            </button>
          </div>
          <h2 style={{ fontSize: '1.3rem', fontWeight: 800, marginBottom: '8px' }}>Aprobar</h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '16px' }}>
            Todavía no hay artículo seleccionado. Empieza eligiendo una noticia.
          </p>
          <button className="btn btn-primary" onClick={() => goToTab('hoy')}>Ir a Hoy</button>
        </section>
      )}
      {selectedArticleForApproval && (
        <section className="glass-panel" style={{ padding: '24px' }}>
          <div className="flow-step-banner">
            <span>Paso 3 de 4 · Aprobar</span>
            <button type="button" className="btn btn-primary" onClick={() => goToTab('publish')}>
              Siguiente: Publicar
            </button>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
            <div>
              <h2 style={{ fontSize: '1.35rem', fontWeight: 800 }}>Aprobar contenido</h2>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                Revisa fuente y borrador antes de dar luz verde.
              </p>
            </div>
            <div style={{ display: 'flex', gap: '12px' }}>
              <button 
                id="btn-approve-article"
                className="btn btn-success" 
                onClick={() => handleApproveArticle(selectedArticleForApproval.id)}
              >
                <CheckCircle2 size={18} /> Aprobar
              </button>
              <button 
                id="btn-reject-article"
                className="btn btn-danger" 
                onClick={() => handleRejectArticle(selectedArticleForApproval.id)}
              >
                <XCircle size={18} /> Rechazar
              </button>
            </div>
          </div>

          {pendingBlogPosts?.length > 0 && (
            <div className="glass-card" style={{ padding: '16px', marginBottom: '16px' }}>
              <strong>Blogs pendientes de aprobación ({pendingBlogPosts.length})</strong>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '10px' }}>
                {pendingBlogPosts.slice(0, 8).map((b) => (
                  <div key={b.id} style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', alignItems: 'center' }}>
                    <span style={{ fontSize: '0.88rem' }}>{b.title}</span>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <button className="btn btn-secondary" style={{ padding: '4px 10px', fontSize: '0.75rem' }} onClick={() => approvePendingBlog(b.id)}>Aprobar</button>
                      <button className="btn btn-primary" style={{ padding: '4px 10px', fontSize: '0.75rem' }} onClick={() => publishPendingBlog(b.id)}>Publicar</button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Side-by-side Grid */}
          <div className="approval-grid">
            {/* Left Column: Original Source Article */}
            <div className="glass-card panel-column">
              <div className="column-header">
                <span>1. Noticia Original Almacenada</span>
                <span className="status-badge status-verified">FUENTE REAL</span>
              </div>

              <div className="source-citation">
                <span><strong>Fuente:</strong> {selectedArticleForApproval.source_name}</span>
                <a href={selectedArticleForApproval.url} target="_blank" rel="noopener noreferrer" className="source-link">
                  Ver Fuente Original <ExternalLink size={14} />
                </a>
              </div>

              <h3 style={{ fontSize: '1.2rem', fontWeight: 700 }}>{selectedArticleForApproval.title}</h3>

              <div style={{ background: 'rgba(0,0,0,0.3)', padding: '16px', borderRadius: '8px', fontSize: '0.9rem', lineHeight: 1.6, maxHeight: '400px', overflowY: 'auto' }}>
                <p style={{ whiteSpace: 'pre-wrap' }}>{selectedArticleForApproval.content_full || 'Sin contenido completo registrado.'}</p>
              </div>
            </div>

            {/* Right Column: AI Analysis & Fact Verification */}
            <div className="glass-card panel-column">
              <div className="column-header">
                <span>2. Análisis e Inspección Anti-Alucinación (IA)</span>
                <span className={`status-badge status-${selectedArticleForApproval.verification_status}`}>
                  {selectedArticleForApproval.verification_status}
                </span>
              </div>

              {selectedArticleForApproval.summary || selectedArticleForApproval.content_full ? (
                <div>
                  {(() => {
                    const raw = selectedArticleForApproval.summary || selectedArticleForApproval.content_full;
                    const summaryObj = parseSummaryJson(raw);
                    if (!summaryObj) {
                      return (
                        <p style={{ fontSize: '0.92rem', lineHeight: 1.55, color: 'var(--text-secondary)' }}>
                          {String(raw).slice(0, 800)}
                        </p>
                      );
                    }
                    return (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                        <div>
                          <strong style={{ color: 'var(--accent-cyan)' }}>Ángulo Editorial:</strong>
                          <p style={{ fontSize: '0.92rem', marginTop: '4px' }}>{summaryObj.editorial_angle}</p>
                        </div>

                        <div>
                          <strong style={{ color: 'var(--accent-purple)' }}>Resumen Ejecutivo:</strong>
                          <p style={{ fontSize: '0.92rem', marginTop: '4px', lineHeight: 1.5 }}>{summaryObj.executive_summary}</p>
                        </div>

                        <div>
                          <strong style={{ color: 'var(--accent-emerald)' }}>Afirmaciones Clave Verificadas:</strong>
                          <ul style={{ paddingLeft: '20px', marginTop: '6px', fontSize: '0.88rem' }}>
                            {summaryObj.key_claims?.map((claim, idx) => (
                              <li key={idx} style={{ marginBottom: '4px' }}>{claim}</li>
                            ))}
                          </ul>
                        </div>

                        {selectedArticleForApproval.verification_reason && (
                          <div style={{ padding: '10px 14px', background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.3)', borderRadius: '8px', fontSize: '0.85rem' }}>
                            <strong>Resultado de Auditoría:</strong> {selectedArticleForApproval.verification_reason}
                          </div>
                        )}
                      </div>
                    );
                  })()}
                </div>
              ) : (
                <div style={{ textAlign: 'center', padding: '40px 20px' }}>
                  <Sparkles size={40} style={{ color: 'var(--accent-purple)', marginBottom: '12px' }} />
                  <p style={{ marginBottom: '16px', color: 'var(--text-secondary)' }}>Este artículo aún no ha sido analizado por Ollama.</p>
                  <button 
                    className="btn btn-primary"
                    onClick={() => triggerAnalyzeArticle(selectedArticleForApproval.id)}
                    disabled={loading}
                  >
                    Ejecutar Análisis y Verificación Factual
                  </button>
                </div>
              )}
            </div>
          </div>
        </section>
      )}

    </>
  );
}

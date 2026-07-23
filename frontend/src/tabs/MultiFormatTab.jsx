import React from 'react';
import { ExternalLink, CheckCircle2, Linkedin, Video, Layers, Mail, Copy } from 'lucide-react';

export default function MultiFormatTab({
  selectedArticleForApproval,
  selectedLanguage,
  onLanguageChange,
  fetchMultiFormat,
  formatBusy,
  selectedFormatSubTab,
  setSelectedFormatSubTab,
  multiFormatError,
  multiFormatContent,
  loading,
  isBusy,
  notify,
  approveContentPiece,
  reuseContentPiece,
  attachPieceToFirstSlot,
  parseCarouselJson,
  goToTab
}) {
  const renderAIAuditPanel = (formatType) => {
    if (!multiFormatContent || !multiFormatContent.pieces) return null;
    const piece = multiFormatContent.pieces.find(p => p.format_type === formatType);
    if (!piece) return null;

    const { brand_review_json, factual_review_json } = piece;
    if (!brand_review_json && !factual_review_json) return null;

    const argAnalysis = brand_review_json?.argumentative_analysis || {};
    const argScore = argAnalysis.score ?? 'N/A';
    const isArgPass = argAnalysis.passed;

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', background: 'rgba(0,0,0,0.2)', padding: '16px', borderRadius: '10px', borderLeft: isArgPass ? '4px solid var(--accent-emerald)' : '4px solid var(--accent-amber)', marginTop: '16px' }}>
        <h4 style={{ fontSize: '0.95rem', fontWeight: 700, margin: 0, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
          Auditoría de Inteligencia Artificial (Editor AI)
        </h4>
        
        <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
            <div style={{ flex: 1, minWidth: '200px' }}>
                <strong style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Profundidad Argumentativa:</strong>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '6px' }}>
                    <span className="score-tag" style={{ background: isArgPass ? 'rgba(16,185,129,0.2)' : 'rgba(245,158,11,0.2)', color: isArgPass ? 'var(--accent-emerald)' : 'var(--accent-amber)', borderColor: isArgPass ? 'rgba(16,185,129,0.3)' : 'rgba(245,158,11,0.3)' }}>
                        Score: {argScore}/100
                    </span>
                    <span style={{ fontSize: '0.8rem', color: isArgPass ? '#10B981' : '#F59E0B', fontWeight: 600 }}>
                        {isArgPass ? 'Aprobado' : 'Superficial (Rechazado)'}
                    </span>
                </div>
                {argAnalysis.critique && (
                    <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '8px', lineHeight: 1.4 }}>
                        <em>"{argAnalysis.critique}"</em>
                    </p>
                )}
            </div>

            <div style={{ flex: 1, minWidth: '200px' }}>
                <strong style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Voz de Marca & Hype:</strong>
                <div style={{ marginTop: '4px' }}>
                    {brand_review_json?.passed ? (
                        <span style={{ fontSize: '0.85rem', color: '#10B981', display: 'flex', alignItems: 'center', gap: '4px', marginTop: '4px' }}><CheckCircle2 size={14}/> Tono profesional (0 issues)</span>
                    ) : (
                        <div style={{ fontSize: '0.85rem', color: '#EF4444', marginTop: '4px' }}>
                            Falló: {brand_review_json?.issues?.join(', ')}
                        </div>
                    )}
                </div>

                <strong style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'block', marginTop: '12px' }}>Factual & Anti-Alucinación:</strong>
                <div style={{ marginTop: '4px' }}>
                    {factual_review_json?.passed ? (
                        <span style={{ fontSize: '0.85rem', color: '#10B981', display: 'flex', alignItems: 'center', gap: '4px', marginTop: '4px' }}><CheckCircle2 size={14}/> Trazable a la fuente</span>
                    ) : (
                        <div style={{ fontSize: '0.85rem', color: '#EF4444', marginTop: '4px' }}>
                            Alucinación: {factual_review_json?.unsupported_claims?.length} claims sin soporte
                        </div>
                    )}
                </div>
            </div>
        </div>
      </div>
    );
  };

  return (
    <>
      {!selectedArticleForApproval && (
        <section className="glass-panel" style={{ padding: '24px' }}>
          <div className="flow-step-banner">
            <span>Paso 2 de 4 · Generar</span>
            <button type="button" className="btn btn-secondary" onClick={() => goToTab('hoy')}>
              Ver Hoy
            </button>
          </div>
          <h2 style={{ fontSize: '1.3rem', fontWeight: 800, marginBottom: '8px' }}>Generar formatos</h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '16px' }}>
            Primero elige una noticia. Luego genera LinkedIn, video, carrusel y newsletter.
          </p>
          <button className="btn btn-primary" onClick={() => goToTab('top10')}>
            Ir a Elegir
          </button>
        </section>
      )}
      {selectedArticleForApproval && (
        <section className="glass-panel" style={{ padding: '24px' }}>
          <div className="flow-step-banner">
            <span>Paso 2 de 4 · Generar</span>
            <button type="button" className="btn btn-primary" onClick={() => goToTab('approval')}>
              Siguiente: Aprobar
            </button>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '16px' }}>
            <div>
              <h2 style={{ fontSize: '1.35rem', fontWeight: 800 }}>Generar formatos</h2>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                Una noticia → LinkedIn, guion, carrusel y newsletter.
              </p>
            </div>

            <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
              <span style={{ fontSize: '0.88rem', color: 'var(--text-secondary)' }}>Idioma:</span>
              <select
                value={selectedLanguage}
                disabled={formatBusy || isBusy?.('multiformat')}
                onChange={(e) => onLanguageChange?.(e.target.value)}
                style={{
                  padding: '8px 14px',
                  borderRadius: '8px',
                  background: 'var(--bg-card)',
                  color: '#FFF',
                  border: '1px solid rgba(255,255,255,0.2)',
                  fontWeight: 600,
                  opacity: formatBusy || isBusy?.('multiformat') ? 0.6 : 1,
                }}
              >
                <option value="es">Español (MX)</option>
                <option value="en">English (US)</option>
              </select>
              {(formatBusy || isBusy?.('multiformat')) && (
                <span style={{ fontSize: '0.8rem', color: 'var(--accent-cyan)' }}>
                  Regenerando en {selectedLanguage === 'en' ? 'inglés' : 'español'}…
                </span>
              )}
              {multiFormatContent?.language && !(formatBusy || isBusy?.('multiformat')) && (
                <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                  Paquete: {multiFormatContent.language === 'en' ? 'EN' : 'ES'}
                </span>
              )}
            </div>
          </div>

          {/* Article Selector Banner */}
          <div className="source-citation" style={{ marginBottom: '20px' }}>
            <div>
              <strong style={{ color: '#FFF' }}>Noticia Seleccionada:</strong> {selectedArticleForApproval.title}
              <span style={{ marginLeft: '12px', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>({selectedArticleForApproval.source_name})</span>
            </div>
            <a href={selectedArticleForApproval.url} target="_blank" rel="noopener noreferrer" className="source-link">
              Ver Fuente Verificada <ExternalLink size={14} />
            </a>
          </div>

          {/* Persona Warning Banner */}
          <div style={{ background: 'rgba(16,185,129,0.15)', border: '1px solid rgba(16,185,129,0.4)', borderRadius: '10px', padding: '16px', marginBottom: '20px' }}>
            <span style={{ fontWeight: 800, color: '#10B981', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <CheckCircle2 size={18} /> GHOSTWRITING ACTIVO (Persona: Juan Vásquez)
            </span>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
              Los siguientes contenidos han sido redactados usando el System Prompt de tono directivo, analítico y libre de hype. Revísalos antes de mandarlos al calendario.
            </p>
          </div>

          {/* Sub-tabs for the 4 Formats */}
          <div style={{ display: 'flex', gap: '10px', marginBottom: '20px', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '10px' }}>
            <button 
              className={`btn ${selectedFormatSubTab === 'linkedin' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setSelectedFormatSubTab('linkedin')}
            >
              <Linkedin size={16} /> Publicación LinkedIn
            </button>
            <button 
              className={`btn ${selectedFormatSubTab === 'video' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setSelectedFormatSubTab('video')}
            >
              <Video size={16} /> Guion de Video (Teleprompter)
            </button>
            <button 
              className={`btn ${selectedFormatSubTab === 'carousel' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setSelectedFormatSubTab('carousel')}
            >
              <Layers size={16} /> Carrusel (Diapositivas 1-5)
            </button>
            <button 
              className={`btn ${selectedFormatSubTab === 'newsletter' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setSelectedFormatSubTab('newsletter')}
            >
              <Mail size={16} /> Edición Newsletter
            </button>
          </div>

          {/* Multi-format Output Views */}
          {multiFormatError && (
            <div className="glass-card" style={{ padding: '16px', marginBottom: '16px', borderLeft: '4px solid #EF4444', color: 'var(--text-secondary)' }}>
              No se pudo generar multi-formato: {multiFormatError}
              {selectedArticleForApproval?.id && (
                <div style={{ marginTop: '10px' }}>
                  <button className="btn btn-secondary" onClick={() => fetchMultiFormat(selectedArticleForApproval.id, selectedLanguage)}>
                    Reintentar
                  </button>
                </div>
              )}
            </div>
          )}
          {multiFormatContent ? (
            <div>
              {/* 1. LinkedIn */}
              {selectedFormatSubTab === 'linkedin' && (
                <div className="glass-card" style={{ padding: '24px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '14px', gap: '8px', flexWrap: 'wrap' }}>
                    <div>
                      <strong style={{ fontSize: '1.1rem', color: 'var(--accent-cyan)' }}>Post para LinkedIn (Perfil Juan Vásquez)</strong>
                      <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: 4 }}>
                        Sobre: {selectedArticleForApproval?.title || multiFormatContent.article_title || '—'}
                        {' · '}
                        modo: {(multiFormatContent.pieces || []).find((p) => p.format_type === 'linkedin')?.generation_mode || multiFormatContent.generation_mode || '—'}
                      </p>
                    </div>
                    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                      <button className="btn btn-secondary" style={{ padding: '4px 12px', fontSize: '0.8rem' }} onClick={() => { navigator.clipboard.writeText(multiFormatContent.linkedin_post); notify('Copiado', 'success'); }}>
                        <Copy size={14} /> Copiar
                      </button>
                      <button
                        className="btn btn-secondary"
                        style={{ padding: '4px 12px', fontSize: '0.8rem' }}
                        disabled={isBusy('multiformat')}
                        onClick={() => selectedArticleForApproval?.id && fetchMultiFormat(selectedArticleForApproval.id, selectedLanguage)}
                      >
                        Regenerar post
                      </button>
                      <button className="btn btn-primary" style={{ padding: '4px 12px', fontSize: '0.8rem' }} onClick={() => approveContentPiece(multiFormatContent.linkedin_piece_id)}>Aprobar</button>
                      <button className="btn btn-secondary" style={{ padding: '4px 12px', fontSize: '0.8rem' }} onClick={() => reuseContentPiece(multiFormatContent.linkedin_piece_id)}>Reutilizar</button>
                      <button className="btn btn-secondary" style={{ padding: '4px 12px', fontSize: '0.8rem' }} onClick={() => attachPieceToFirstSlot(multiFormatContent.linkedin_piece_id, 'linkedin')}>→ Calendario</button>
                    </div>
                  </div>
                  <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'var(--font-sans)', fontSize: '0.94rem', lineHeight: 1.6, background: 'rgba(0,0,0,0.3)', padding: '18px', borderRadius: '10px' }}>
                    {multiFormatContent.linkedin_post}
                  </pre>
                  {renderAIAuditPanel('linkedin')}
                </div>
              )}

              {/* 2. Video Script */}
              {selectedFormatSubTab === 'video' && (
                <div className="glass-card" style={{ padding: '24px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '14px', gap: '8px', flexWrap: 'wrap' }}>
                    <strong style={{ fontSize: '1.1rem', color: 'var(--accent-purple)' }}>Guion Técnico de Video / Teleprompter</strong>
                    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                      <button className="btn btn-secondary" style={{ padding: '4px 12px', fontSize: '0.8rem' }} onClick={() => { navigator.clipboard.writeText(multiFormatContent.video_script); notify('Copiado', 'success'); }}>
                        <Copy size={14} /> Copiar
                      </button>
                      <button className="btn btn-primary" style={{ padding: '4px 12px', fontSize: '0.8rem' }} onClick={() => approveContentPiece(multiFormatContent.video_piece_id)}>Aprobar</button>
                      <button className="btn btn-secondary" style={{ padding: '4px 12px', fontSize: '0.8rem' }} onClick={() => attachPieceToFirstSlot(multiFormatContent.video_piece_id, 'video_script')}>→ Calendario</button>
                    </div>
                  </div>
                  <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'var(--font-mono)', fontSize: '0.88rem', lineHeight: 1.6, background: 'rgba(0,0,0,0.3)', padding: '18px', borderRadius: '10px', color: '#E2E8F0' }}>
                    {multiFormatContent.video_script}
                  </pre>
                  {renderAIAuditPanel('video_script')}
                </div>
              )}

              {/* 3. Carousel Slides */}
              {selectedFormatSubTab === 'carousel' && (
                <div>
                  <div style={{ display: 'flex', gap: '8px', marginBottom: '12px', flexWrap: 'wrap' }}>
                    <button className="btn btn-primary" style={{ padding: '4px 12px', fontSize: '0.8rem' }} onClick={() => approveContentPiece(multiFormatContent.carousel_piece_id)}>Aprobar</button>
                    <button className="btn btn-secondary" style={{ padding: '4px 12px', fontSize: '0.8rem' }} onClick={() => attachPieceToFirstSlot(multiFormatContent.carousel_piece_id, 'carousel')}>→ Calendario</button>
                  </div>
                  {(() => {
                    const slides = parseCarouselJson(multiFormatContent.carousel_slides);
                    if (!slides.length) {
                      return (
                        <p style={{ color: 'var(--text-secondary)' }}>
                          Este paquete no tiene slides parseables. Vuelve a generar multi-formato.
                        </p>
                      );
                    }
                    return (
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: '16px' }}>
                        {slides.map((slide, idx) => (
                          <div key={slide.slide ?? idx} className="glass-card" style={{ padding: '20px', borderTop: '4px solid var(--accent-cyan)' }}>
                            <span style={{ fontSize: '0.75rem', fontWeight: 800, color: 'var(--accent-cyan)' }}>
                              DIAPOSITIVA {slide.slide || idx + 1} / {slides.length}
                            </span>
                            <h4 style={{ fontSize: '1rem', fontWeight: 700, margin: '8px 0' }}>{slide.title}</h4>
                            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                              {slide.content || slide.text || '—'}
                            </p>
                          </div>
                        ))}
                      </div>
                    );
                  })()}
                  {renderAIAuditPanel('carousel')}
                </div>
              )}

              {/* 4. Newsletter */}
              {selectedFormatSubTab === 'newsletter' && (
                <div className="glass-card" style={{ padding: '24px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '14px', gap: '8px', flexWrap: 'wrap' }}>
                    <strong style={{ fontSize: '1.1rem', color: 'var(--accent-emerald)' }}>Edición de Boletín Semanal</strong>
                    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                      <button className="btn btn-secondary" style={{ padding: '4px 12px', fontSize: '0.8rem' }} onClick={() => { navigator.clipboard.writeText(multiFormatContent.newsletter_edition); notify('Copiado', 'success'); }}>
                        <Copy size={14} /> Copiar Markdown
                      </button>
                      <button className="btn btn-primary" style={{ padding: '4px 12px', fontSize: '0.8rem' }} onClick={() => approveContentPiece(multiFormatContent.newsletter_piece_id)}>Aprobar</button>
                      <button className="btn btn-secondary" style={{ padding: '4px 12px', fontSize: '0.8rem' }} onClick={() => attachPieceToFirstSlot(multiFormatContent.newsletter_piece_id, 'newsletter')}>→ Calendario</button>
                    </div>
                  </div>
                  <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'var(--font-sans)', fontSize: '0.92rem', lineHeight: 1.6, background: 'rgba(0,0,0,0.3)', padding: '18px', borderRadius: '10px' }}>
                    {multiFormatContent.newsletter_edition}
                  </pre>
                  {renderAIAuditPanel('newsletter')}
                </div>
              )}
            </div>
          ) : (
            <p style={{ color: 'var(--text-secondary)' }}>
              {loading
                ? 'Generando multi-formato…'
                : multiFormatError
                  ? 'Revisa el error arriba o elige otro artículo del Top 10.'
                  : 'Selecciona un artículo del Top 10 y pulsa “Derivar 4 Formatos”.'}
            </p>
          )}
        </section>
      )}

    </>
  );
}

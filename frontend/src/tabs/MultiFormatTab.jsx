import React, { useEffect, useState } from 'react';
import { ExternalLink, CheckCircle2, Linkedin, Video, Layers, Mail, Copy, Save, Sparkles } from 'lucide-react';

const editorStyle = {
  width: '100%',
  minHeight: '220px',
  whiteSpace: 'pre-wrap',
  fontFamily: 'var(--font-sans)',
  fontSize: '0.94rem',
  lineHeight: 1.6,
  background: 'rgba(0,0,0,0.35)',
  color: '#FFF',
  padding: '18px',
  borderRadius: '10px',
  border: '1px solid rgba(255,255,255,0.15)',
  resize: 'vertical',
};

const SUBTAB_TO_FORMAT = {
  linkedin: 'linkedin',
  video: 'video_script',
  carousel: 'carousel',
  newsletter: 'newsletter',
};

const FORMAT_LABEL = {
  linkedin: 'LinkedIn',
  video: 'guion de video',
  carousel: 'carrusel',
  newsletter: 'newsletter',
};

export default function MultiFormatTab({
  selectedArticleForApproval,
  selectedLanguage,
  onLanguageChange,
  providerMode = 'local',
  onProviderModeChange,
  aiProviders = [],
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
  parseCarouselJson,
  goToTab,
  updateContentPiece,
}) {
  const [drafts, setDrafts] = useState({
    linkedin_post: '',
    video_script: '',
    newsletter_edition: '',
    carousel_slides: '',
  });
  const [saving, setSaving] = useState(null);

  useEffect(() => {
    if (!multiFormatContent) return;
    const slides = multiFormatContent.carousel_slides;
    setDrafts({
      linkedin_post: multiFormatContent.linkedin_post || '',
      video_script: multiFormatContent.video_script || '',
      newsletter_edition: multiFormatContent.newsletter_edition || '',
      carousel_slides: typeof slides === 'string'
        ? slides
        : JSON.stringify(slides || [], null, 2),
    });
  }, [
    multiFormatContent?.id,
    multiFormatContent?.linkedin_piece_id,
    multiFormatContent?.video_piece_id,
    multiFormatContent?.carousel_piece_id,
    multiFormatContent?.newsletter_piece_id,
    multiFormatContent?.language,
  ]);

  const setDraft = (key, value) => setDrafts((prev) => ({ ...prev, [key]: value }));

  const saveField = async (fieldKey, pieceId) => {
    if (!updateContentPiece) {
      notify?.('Guardado no disponible', 'error');
      return;
    }
    setSaving(fieldKey);
    try {
      await updateContentPiece(pieceId, drafts[fieldKey], fieldKey);
    } finally {
      setSaving(null);
    }
  };

  const pieceStatus = (formatType) =>
    (multiFormatContent?.pieces || []).find((p) => p.format_type === formatType)?.status;

  const statusBadge = (formatType) => {
    const st = pieceStatus(formatType);
    if (!st) return null;
    const ok = st === 'approved';
    return (
      <span
        className={`status-badge ${ok ? 'status-verified' : 'status-pending'}`}
        style={{ marginLeft: 8, fontSize: '0.72rem' }}
      >
        {st}
      </span>
    );
  };

  const hasFormatContent = (subTab) => {
    if (!multiFormatContent) return false;
    if (subTab === 'linkedin') return Boolean(multiFormatContent.linkedin_post);
    if (subTab === 'video') return Boolean(multiFormatContent.video_script);
    if (subTab === 'carousel') {
      const slides = multiFormatContent.carousel_slides;
      return Array.isArray(slides) ? slides.length > 0 : Boolean(slides);
    }
    if (subTab === 'newsletter') return Boolean(multiFormatContent.newsletter_edition);
    return false;
  };

  const formatsReady =
    hasFormatContent('linkedin') ||
    hasFormatContent('video') ||
    hasFormatContent('carousel') ||
    hasFormatContent('newsletter');
  const anyApproved = (multiFormatContent?.pieces || []).some((p) => p.status === 'approved');

  const generateFormat = (subTab, regenerate = false) => {
    if (!selectedArticleForApproval?.id) return;
    const fmt = SUBTAB_TO_FORMAT[subTab] || 'linkedin';
    fetchMultiFormat(selectedArticleForApproval.id, selectedLanguage, {
      showBanner: true,
      clearContent: false,
      formats: [fmt],
      regenerate,
      packageId: multiFormatContent?.id || null,
    });
  };

  const renderGenerateGate = (subTab) => (
    <div className="glass-card" style={{ padding: '28px', textAlign: 'center' }}>
      <Sparkles size={28} style={{ color: 'var(--accent-cyan)', marginBottom: 10, opacity: 0.8 }} />
      <p style={{ color: 'var(--text-secondary)', marginBottom: 16 }}>
        Este formato aún no está generado. Actívalo solo cuando lo necesites (más rápido).
      </p>
      <button
        type="button"
        className="btn btn-primary"
        disabled={formatBusy || isBusy?.('multiformat')}
        onClick={() => generateFormat(subTab, false)}
      >
        {formatBusy || isBusy?.('multiformat')
          ? 'Generando…'
          : `Generar ${FORMAT_LABEL[subTab] || 'formato'}`}
      </button>
    </div>
  );

  const renderAIAuditPanel = (formatType) => {
    if (!multiFormatContent || !multiFormatContent.pieces) return null;
    const piece = multiFormatContent.pieces.find(p => p.format_type === formatType);
    if (!piece) return null;

    // API devuelve brand_review / factual_review; algunos payloads usan *_json
    const brand_review_json = piece.brand_review_json || piece.brand_review || null;
    const factual_review_json = piece.factual_review_json || piece.factual_review || null;
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
            <span>Paso 1 de 3 · Elegir y generar</span>
            <button type="button" className="btn btn-secondary" onClick={() => goToTab('hoy')}>
              Ver Hoy
            </button>
          </div>
          <h2 style={{ fontSize: '1.3rem', fontWeight: 800, marginBottom: '8px' }}>Generar formatos</h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '16px' }}>
            Primero elige una noticia. Luego activa solo el formato que necesites (LinkedIn, video, etc.).
          </p>
          <button className="btn btn-primary" onClick={() => goToTab('hoy')}>
            Ir a Elegir tema
          </button>
        </section>
      )}
      {selectedArticleForApproval && (
        <section className="glass-panel" style={{ padding: '24px' }}>
          <div className="flow-step-banner">
            <span>
              {!formatsReady
                ? 'Paso 1 de 3 · Listo para generar'
                : anyApproved
                  ? 'Paso 2 de 3 · Aprobado · listo para publicar'
                  : 'Paso 2 de 3 · Revisar y aprobar'}
            </span>
            <button
              type="button"
              className="btn btn-primary"
              disabled={!formatsReady}
              onClick={() => goToTab('publish')}
            >
              Siguiente: Publicar
            </button>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '16px' }}>
            <div>
              <h2 style={{ fontSize: '1.35rem', fontWeight: 800 }}>Generar formatos</h2>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                Genera solo el formato de la pestaña activa. Cambia de pestaña y activa otro cuando lo necesites.
              </p>
            </div>

            <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
              <span style={{ fontSize: '0.88rem', color: 'var(--text-secondary)' }}>Modelo:</span>
              <select
                value={providerMode}
                disabled={formatBusy || isBusy?.('multiformat')}
                onChange={(e) => onProviderModeChange?.(e.target.value)}
                style={{
                  padding: '8px 14px',
                  borderRadius: '8px',
                  background: 'var(--bg-card)',
                  color: '#FFF',
                  border: '1px solid rgba(255,255,255,0.2)',
                  fontWeight: 600,
                  opacity: formatBusy || isBusy?.('multiformat') ? 0.6 : 1,
                }}
                title="Local = Ollama en tu PC. API = tu clave en Inteligencia Artificial."
              >
                <option value="local">IA local (Ollama)</option>
                <option value="cloud">API web (tu key)</option>
                <option value="auto">Auto (local → API)</option>
              </select>
              {providerMode === 'cloud' && !(aiProviders || []).some((p) => p.is_active && !p.is_local) && (
                <button
                  type="button"
                  className="btn btn-secondary"
                  style={{ padding: '6px 10px', fontSize: '0.78rem' }}
                  onClick={() => goToTab('aigateway')}
                >
                  Configurar API key
                </button>
              )}
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
                  Generando {FORMAT_LABEL[selectedFormatSubTab] || 'formato'}…
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

          {/* Multi-format Output Views — un formato a la vez */}
          {multiFormatError && (
            <div className="glass-card" style={{ padding: '16px', marginBottom: '16px', borderLeft: '4px solid #EF4444', color: 'var(--text-secondary)' }}>
              No se pudo generar: {multiFormatError}
              <div style={{ marginTop: '10px' }}>
                <button className="btn btn-secondary" onClick={() => generateFormat(selectedFormatSubTab, true)}>
                  Reintentar este formato
                </button>
              </div>
            </div>
          )}

          {selectedFormatSubTab === 'linkedin' && (
            hasFormatContent('linkedin') ? (
              <div className="glass-card" style={{ padding: '24px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '14px', gap: '8px', flexWrap: 'wrap' }}>
                  <div>
                    <strong style={{ fontSize: '1.1rem', color: 'var(--accent-cyan)' }}>
                      Post LinkedIn {statusBadge('linkedin')}
                    </strong>
                  </div>
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    <button className="btn btn-secondary" style={{ padding: '4px 12px', fontSize: '0.8rem' }} onClick={() => { navigator.clipboard.writeText(drafts.linkedin_post); notify('Copiado', 'success'); }}>
                      <Copy size={14} /> Copiar
                    </button>
                    <button className="btn btn-secondary" style={{ padding: '4px 12px', fontSize: '0.8rem' }} disabled={saving === 'linkedin_post'} onClick={() => saveField('linkedin_post', multiFormatContent.linkedin_piece_id)}>
                      <Save size={14} /> {saving === 'linkedin_post' ? 'Guardando…' : 'Guardar'}
                    </button>
                    <button className="btn btn-secondary" style={{ padding: '4px 12px', fontSize: '0.8rem' }} disabled={isBusy('multiformat')} onClick={() => generateFormat('linkedin', true)}>Regenerar</button>
                    <button className="btn btn-primary" style={{ padding: '4px 12px', fontSize: '0.8rem' }} onClick={() => approveContentPiece(multiFormatContent.linkedin_piece_id)}>Aprobar</button>
                  </div>
                </div>
                <textarea value={drafts.linkedin_post} onChange={(e) => setDraft('linkedin_post', e.target.value)} style={editorStyle} aria-label="Editar post LinkedIn" />
                {renderAIAuditPanel('linkedin')}
              </div>
            ) : renderGenerateGate('linkedin')
          )}

          {selectedFormatSubTab === 'video' && (
            hasFormatContent('video') ? (
              <div className="glass-card" style={{ padding: '24px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '14px', gap: '8px', flexWrap: 'wrap' }}>
                  <strong style={{ fontSize: '1.1rem', color: 'var(--accent-purple)' }}>Guion de Video {statusBadge('video_script')}</strong>
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    <button className="btn btn-secondary" style={{ padding: '4px 12px', fontSize: '0.8rem' }} onClick={() => { navigator.clipboard.writeText(drafts.video_script); notify('Copiado', 'success'); }}>
                      <Copy size={14} /> Copiar
                    </button>
                    <button className="btn btn-secondary" style={{ padding: '4px 12px', fontSize: '0.8rem' }} disabled={saving === 'video_script'} onClick={() => saveField('video_script', multiFormatContent.video_piece_id)}>
                      <Save size={14} /> {saving === 'video_script' ? 'Guardando…' : 'Guardar'}
                    </button>
                    <button className="btn btn-secondary" style={{ padding: '4px 12px', fontSize: '0.8rem' }} disabled={isBusy('multiformat')} onClick={() => generateFormat('video', true)}>Regenerar</button>
                    <button className="btn btn-primary" style={{ padding: '4px 12px', fontSize: '0.8rem' }} onClick={() => approveContentPiece(multiFormatContent.video_piece_id)}>Aprobar</button>
                  </div>
                </div>
                <textarea value={drafts.video_script} onChange={(e) => setDraft('video_script', e.target.value)} style={{ ...editorStyle, fontFamily: 'var(--font-mono)', fontSize: '0.88rem' }} aria-label="Editar guion" />
                {renderAIAuditPanel('video_script')}
              </div>
            ) : renderGenerateGate('video')
          )}

          {selectedFormatSubTab === 'carousel' && (
            hasFormatContent('carousel') ? (
              <div>
                <div style={{ display: 'flex', gap: '8px', marginBottom: '12px', flexWrap: 'wrap', alignItems: 'center' }}>
                  <strong style={{ marginRight: 8 }}>Carrusel {statusBadge('carousel')}</strong>
                  <button className="btn btn-secondary" style={{ padding: '4px 12px', fontSize: '0.8rem' }} disabled={saving === 'carousel_slides'} onClick={() => saveField('carousel_slides', multiFormatContent.carousel_piece_id)}>
                    <Save size={14} /> {saving === 'carousel_slides' ? 'Guardando…' : 'Guardar'}
                  </button>
                  <button className="btn btn-secondary" style={{ padding: '4px 12px', fontSize: '0.8rem' }} disabled={isBusy('multiformat')} onClick={() => generateFormat('carousel', true)}>Regenerar</button>
                  <button className="btn btn-primary" style={{ padding: '4px 12px', fontSize: '0.8rem' }} onClick={() => approveContentPiece(multiFormatContent.carousel_piece_id)}>Aprobar</button>
                </div>
                <textarea value={drafts.carousel_slides} onChange={(e) => setDraft('carousel_slides', e.target.value)} style={{ ...editorStyle, minHeight: '280px', fontFamily: 'var(--font-mono)', fontSize: '0.85rem', marginBottom: '16px' }} aria-label="Editar carrusel" />
                {(() => {
                  let slides = [];
                  try {
                    const parsed = JSON.parse(drafts.carousel_slides || '[]');
                    slides = parseCarouselJson(parsed);
                  } catch {
                    slides = parseCarouselJson(multiFormatContent.carousel_slides);
                  }
                  if (!slides.length) {
                    return (
                      <p style={{ color: 'var(--text-secondary)' }}>
                        Edita el JSON de slides arriba o regenera este formato.
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
            ) : renderGenerateGate('carousel')
          )}

          {selectedFormatSubTab === 'newsletter' && (
            hasFormatContent('newsletter') ? (
              <div className="glass-card" style={{ padding: '24px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '14px', gap: '8px', flexWrap: 'wrap' }}>
                  <strong style={{ fontSize: '1.1rem', color: 'var(--accent-emerald)' }}>Newsletter {statusBadge('newsletter')}</strong>
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    <button className="btn btn-secondary" style={{ padding: '4px 12px', fontSize: '0.8rem' }} onClick={() => { navigator.clipboard.writeText(drafts.newsletter_edition); notify('Copiado', 'success'); }}>
                      <Copy size={14} /> Copiar
                    </button>
                    <button className="btn btn-secondary" style={{ padding: '4px 12px', fontSize: '0.8rem' }} disabled={saving === 'newsletter_edition'} onClick={() => saveField('newsletter_edition', multiFormatContent.newsletter_piece_id)}>
                      <Save size={14} /> {saving === 'newsletter_edition' ? 'Guardando…' : 'Guardar'}
                    </button>
                    <button className="btn btn-secondary" style={{ padding: '4px 12px', fontSize: '0.8rem' }} disabled={isBusy('multiformat')} onClick={() => generateFormat('newsletter', true)}>Regenerar</button>
                    <button className="btn btn-primary" style={{ padding: '4px 12px', fontSize: '0.8rem' }} onClick={() => approveContentPiece(multiFormatContent.newsletter_piece_id)}>Aprobar</button>
                  </div>
                </div>
                <textarea value={drafts.newsletter_edition} onChange={(e) => setDraft('newsletter_edition', e.target.value)} style={editorStyle} aria-label="Editar newsletter" />
                {renderAIAuditPanel('newsletter')}
              </div>
            ) : renderGenerateGate('newsletter')
          )}
        </section>
      )}

    </>
  );
}

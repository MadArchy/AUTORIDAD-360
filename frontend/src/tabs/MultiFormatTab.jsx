import React, { useEffect, useMemo, useState } from 'react';
import {
  CheckCircle2,
  Copy,
  ExternalLink,
  Image as ImageIcon,
  Layers,
  Linkedin,
  Mail,
  Save,
  Sparkles,
  Video,
} from 'lucide-react';
import FormatPreview from '../components/FormatPreview';
import PieceCopilotPanel from '../components/PieceCopilotPanel';
import StudioDistribute from '../components/StudioDistribute';
import { api } from '../api';

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

const FIELD_BY_SUB = {
  linkedin: 'linkedin_post',
  video: 'video_script',
  carousel: 'carousel_slides',
  newsletter: 'newsletter_edition',
};

const PIECE_ID_BY_SUB = {
  linkedin: 'linkedin_piece_id',
  video: 'video_piece_id',
  carousel: 'carousel_piece_id',
  newsletter: 'newsletter_piece_id',
};

const API_FORMAT_BY_SUB = {
  linkedin: 'linkedin',
  video: 'video_script',
  carousel: 'carousel',
  newsletter: 'newsletter',
};

const PREVIEW_FORMAT_BY_SUB = {
  linkedin: 'linkedin',
  video: 'video',
  carousel: 'carousel',
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
  parseCarouselJson,
  goToTab,
  updateContentPiece,
  profile = null,
  pendingBlogPosts = [],
  publishedBlogPosts = [],
  editorialBlogPosts = [],
  onGenerateBlog,
  onApproveBlog,
  onPublishBlog,
  blogBusy = false,
  onImagesGenerated,
}) {
  const [drafts, setDrafts] = useState({
    linkedin_post: '',
    video_script: '',
    newsletter_edition: '',
    carousel_slides: '',
  });
  const [saving, setSaving] = useState(null);
  const [imagesBusy, setImagesBusy] = useState(false);

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

  const carouselSlides = useMemo(() => {
    try {
      const parsed = JSON.parse(drafts.carousel_slides || '[]');
      return parseCarouselJson?.(parsed) || (Array.isArray(parsed) ? parsed : []);
    } catch {
      return parseCarouselJson?.(multiFormatContent?.carousel_slides) || [];
    }
  }, [drafts.carousel_slides, multiFormatContent?.carousel_slides, parseCarouselJson]);

  const generateImagesForPiece = async (pieceId, subTab) => {
    if (!pieceId) {
      notify?.('Guarda o genera el formato primero', 'warn');
      return;
    }
    setImagesBusy(true);
    try {
      const data = await api(`/content/pieces/${pieceId}/generate-images`, {
        method: 'POST',
        body: JSON.stringify({ use_openai: true, include_article_context: true }),
      });
      if (subTab === 'carousel' && Array.isArray(data?.slides)) {
        setDrafts((prev) => ({
          ...prev,
          carousel_slides: JSON.stringify(data.slides, null, 2),
        }));
      }
      onImagesGenerated?.(data);
      const engine = data?.engine === 'openai+brand' ? 'IA + marca' : 'marca (tipográficas)';
      const based = data?.article_context?.article_title
        ? ` · basadas en la noticia`
        : '';
      notify?.(`Imágenes listas (${engine}${based}): ${data?.asset_ids?.length || 0}`, 'success');
    } catch (e) {
      notify?.(e.message || 'No se pudieron generar las imágenes', 'error');
    } finally {
      setImagesBusy(false);
    }
  };

  const authorName = profile?.full_name || 'Juan Vásquez';
  const authorTitle = profile?.title || 'Abogado · Legal Tech & IA';

  const renderGenerateGate = (subTab) => (
    <div className="glass-card" style={{ padding: '28px', textAlign: 'center' }}>
      <Sparkles size={28} style={{ color: 'var(--accent-cyan)', marginBottom: 10, opacity: 0.8 }} />
      <p style={{ color: 'var(--text-secondary)', marginBottom: 16 }}>
        Este formato aún no está generado. Actívalo cuando lo necesites; luego verás preview, chat IA y publicar.
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
    if (!multiFormatContent?.pieces) return null;
    const piece = multiFormatContent.pieces.find((p) => p.format_type === formatType);
    if (!piece) return null;
    const brand_review_json = piece.brand_review_json || piece.brand_review || null;
    const factual_review_json = piece.factual_review_json || piece.factual_review || null;
    if (!brand_review_json && !factual_review_json) return null;
    const argAnalysis = brand_review_json?.argumentative_analysis || {};
    const argScore = argAnalysis.score ?? 'N/A';
    const isArgPass = argAnalysis.passed;

    return (
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '12px',
          background: 'rgba(0,0,0,0.2)',
          padding: '16px',
          borderRadius: '10px',
          borderLeft: isArgPass ? '4px solid var(--accent-emerald)' : '4px solid var(--accent-amber)',
          marginTop: '16px',
        }}
      >
        <h4 style={{ fontSize: '0.95rem', fontWeight: 700, margin: 0 }}>Auditoría IA</h4>
        <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
          <div style={{ flex: '1 1 140px', minWidth: 0 }}>
            <strong style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Argumentación:</strong>
            <div style={{ marginTop: 6 }}>
              <span className="score-tag">Score: {argScore}/100</span>
            </div>
          </div>
          <div style={{ flex: '1 1 140px', minWidth: 0, fontSize: '0.85rem' }}>
            {brand_review_json?.passed ? (
              <span style={{ color: '#10B981', display: 'flex', alignItems: 'center', gap: 4 }}>
                <CheckCircle2 size={14} /> Marca OK
              </span>
            ) : (
              <span style={{ color: '#EF4444' }}>Marca: {brand_review_json?.issues?.join(', ')}</span>
            )}
            <div style={{ marginTop: 8 }}>
              {factual_review_json?.passed ? (
                <span style={{ color: '#10B981', display: 'flex', alignItems: 'center', gap: 4 }}>
                  <CheckCircle2 size={14} /> Factual OK
                </span>
              ) : (
                <span style={{ color: '#EF4444' }}>
                  Claims sin soporte: {factual_review_json?.unsupported_claims?.length}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  };

  const renderStudioFormat = (subTab) => {
    if (!hasFormatContent(subTab)) return renderGenerateGate(subTab);

    const fieldKey = FIELD_BY_SUB[subTab];
    const pieceIdKey = PIECE_ID_BY_SUB[subTab];
    const apiFormat = API_FORMAT_BY_SUB[subTab];
    const pieceId = multiFormatContent?.[pieceIdKey];
    const draft = drafts[fieldKey] || '';
    const previewFormat = PREVIEW_FORMAT_BY_SUB[subTab];
    const titleColor =
      subTab === 'linkedin'
        ? 'var(--accent-cyan)'
        : subTab === 'video'
          ? 'var(--accent-purple)'
          : subTab === 'newsletter'
            ? 'var(--accent-emerald)'
            : 'var(--accent-cyan)';

    return (
      <div>
        <div className="section-header" style={{ marginBottom: 14 }}>
          <div>
            <span className="section-eyebrow">Pieza · {pieceStatus(apiFormat) || 'borrador'}</span>
            <strong style={{ display: 'block', marginTop: 4, fontSize: '1.1rem', color: titleColor }}>
              {FORMAT_LABEL[subTab]} {statusBadge(apiFormat)}
            </strong>
          </div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {subTab !== 'carousel' && (
              <button
                type="button"
                className="btn btn-secondary"
                style={{ padding: '4px 12px', fontSize: '0.8rem' }}
                onClick={() => {
                  navigator.clipboard.writeText(draft);
                  notify?.('Copiado', 'success');
                }}
              >
                <Copy size={14} /> Copiar
              </button>
            )}
            <button
              type="button"
              className="btn btn-secondary"
              style={{ padding: '4px 12px', fontSize: '0.8rem' }}
              disabled={saving === fieldKey}
              onClick={() => saveField(fieldKey, pieceId)}
            >
              <Save size={14} /> {saving === fieldKey ? 'Guardando…' : 'Guardar'}
            </button>
            <button
              type="button"
              className="btn btn-primary"
              style={{ padding: '4px 12px', fontSize: '0.8rem' }}
              disabled={imagesBusy || !pieceId}
              onClick={() => generateImagesForPiece(pieceId, subTab)}
              title={
                selectedArticleForApproval?.title
                  ? `Genera creatividades según la noticia: ${selectedArticleForApproval.title}`
                  : 'Genera creatividades PNG según el contenido'
              }
            >
              <ImageIcon size={14} /> {imagesBusy ? 'Generando imágenes…' : 'Generar imágenes'}
            </button>
            {selectedArticleForApproval?.title ? (
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', maxWidth: 220 }}>
                Basado en: {selectedArticleForApproval.title.slice(0, 72)}
                {selectedArticleForApproval.title.length > 72 ? '…' : ''}
              </span>
            ) : null}
            <button
              type="button"
              className="btn btn-secondary"
              style={{ padding: '4px 12px', fontSize: '0.8rem' }}
              disabled={isBusy?.('multiformat')}
              onClick={() => generateFormat(subTab, true)}
            >
              Regenerar
            </button>
            <button
              type="button"
              className="btn btn-primary"
              style={{ padding: '4px 12px', fontSize: '0.8rem' }}
              onClick={() => approveContentPiece(pieceId)}
            >
              Aprobar
            </button>
          </div>
        </div>

        <div className="studio-editor-grid">
          <div className="editorial-card" style={{ padding: 18 }}>
            <div className="section-header">
              <span className="section-title">Editar</span>
              <span className="meta-chip">{draft.length.toLocaleString('es-CO')} caracteres</span>
            </div>
            <textarea
              value={draft}
              onChange={(e) => setDraft(fieldKey, e.target.value)}
              style={{
                ...editorStyle,
                ...(subTab === 'video' || subTab === 'carousel'
                  ? { fontFamily: 'var(--font-mono)', fontSize: '0.88rem' }
                  : {}),
                minHeight: subTab === 'carousel' ? 280 : 220,
              }}
              aria-label={`Editar ${FORMAT_LABEL[subTab]}`}
            />
            {renderAIAuditPanel(apiFormat)}
          </div>
          <div className="editorial-card studio-preview-panel">
            <div className="section-header">
              <span className="section-title">Vista previa</span>
              <span className="meta-chip">Red social</span>
            </div>
            <FormatPreview
              format={previewFormat}
              text={subTab === 'carousel' ? '' : draft}
              slides={subTab === 'carousel' ? carouselSlides : []}
              coverUrl={
                subTab === 'carousel'
                  ? null
                  : (
                      (multiFormatContent?.pieces || []).find((p) => p.format_type === apiFormat)
                        ?.body_json?.image_url
                      || (multiFormatContent?.pieces || []).find((p) => p.format_type === apiFormat)
                        ?.body_json?.creatives?.covers?.[0]?.image_url
                      || null
                    )
              }
              authorName={authorName}
              authorTitle={authorTitle}
            />
          </div>
        </div>

        <details className="studio-disclosure" open style={{ marginTop: 16 }}>
          <summary>Mejorar con IA</summary>
          <PieceCopilotPanel
            pieceId={pieceId}
            draftText={draft}
            providerMode={providerMode}
            notify={notify}
            disabled={formatBusy || isBusy?.('multiformat')}
            onApply={(refined) => setDraft(fieldKey, refined)}
          />
        </details>

        <details className="studio-disclosure" style={{ marginTop: 12 }}>
          <summary>Distribuir y publicar</summary>
          <StudioDistribute
          pieceId={pieceId}
          pieceStatus={pieceStatus(apiFormat)}
          articleId={selectedArticleForApproval?.id}
          pendingBlogPosts={pendingBlogPosts}
          publishedBlogPosts={publishedBlogPosts}
          editorialBlogPosts={editorialBlogPosts}
          onGenerateBlog={onGenerateBlog}
          onApproveBlog={onApproveBlog}
          onPublishBlog={onPublishBlog}
          blogBusy={blogBusy}
          notify={notify}
          onImagesGenerated={onImagesGenerated}
          initialAssetIds={
            (multiFormatContent?.pieces || []).find((p) => p.format_type === apiFormat)
              ?.creatives?.asset_ids
            || (multiFormatContent?.pieces || []).find((p) => p.format_type === apiFormat)
              ?.generation_json?.creatives?.asset_ids
            || carouselSlides.map((s) => s.media_asset_id).filter(Boolean)
          }
          initialAssets={
            carouselSlides
              .filter((s) => s.image_url)
              .map((s) => ({
                id: s.media_asset_id,
                storage_url: s.image_url,
                title: s.title,
              }))
          }
          />
        </details>
      </div>
    );
  };

  return (
    <>
      {!selectedArticleForApproval && (
        <section className="glass-panel" style={{ padding: '24px' }}>
          <div className="flow-step-banner">
            <span>Estudio · elige una noticia</span>
            <button type="button" className="btn btn-secondary" onClick={() => goToTab('hoy')}>
              Ver Hoy
            </button>
          </div>
          <span className="page-eyebrow">Línea de producción</span>
          <h2 className="page-title">Estudio de contenido</h2>
          <p className="page-description" style={{ marginBottom: '16px' }}>
            Genera formatos, previsualiza cómo se verían en redes, mejora con IA y publica o monta el blog desde aquí.
            Publicar y Blog ya no están menús aparte.
          </p>
          <button className="btn btn-primary" onClick={() => goToTab('hoy')}>
            Ir a Hoy
          </button>
        </section>
      )}

      {selectedArticleForApproval && (
        <section className="glass-panel" style={{ padding: '24px' }}>
          <div className="flow-step-banner">
            <span>
              {!formatsReady
                ? 'Estudio · listo para generar'
                : anyApproved
                  ? 'Estudio · aprobado · distribuir abajo'
                  : 'Estudio · revisar, chat IA y aprobar'}
            </span>
          </div>

          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '20px',
              flexWrap: 'wrap',
              gap: '16px',
            }}
          >
            <div>
              <span className="page-eyebrow">Línea de producción · {selectedArticleForApproval.source_name || 'noticia seleccionada'}</span>
              <h2 style={{ fontSize: '1.35rem', fontWeight: 800, marginTop: 4 }}>Estudio de contenido</h2>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                {selectedArticleForApproval.title}
              </p>
            </div>

            <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
              <span style={{ fontSize: '0.88rem', color: 'var(--text-secondary)' }}>Modelo:</span>
              <select
                value={providerMode}
                disabled={formatBusy || isBusy?.('multiformat')}
                onChange={(e) => onProviderModeChange?.(e.target.value)}
                className="form-control"
                style={{ width: 'auto', fontWeight: 600, opacity: formatBusy || isBusy?.('multiformat') ? 0.6 : 1 }}
                title="Local = Ollama. API = clave en Inteligencia Artificial."
              >
                <option value="local">IA local (Ollama)</option>
                <option value="cloud">API web (tu key)</option>
                <option value="auto">Auto (local → API)</option>
              </select>
              {providerMode === 'cloud' && !(aiProviders || []).some((p) => p.is_active && !p.is_local && (p.has_api_key || p.key_hint)) && (
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
            </div>
          </div>

          <div className="source-citation" style={{ marginBottom: '20px' }}>
            <div>
              <strong style={{ color: '#FFF' }}>Noticia:</strong> {selectedArticleForApproval.title}
              <span style={{ marginLeft: '12px', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                ({selectedArticleForApproval.source_name})
              </span>
            </div>
            {(selectedArticleForApproval.url || selectedArticleForApproval.source_url) && (
              <a
                href={selectedArticleForApproval.url || selectedArticleForApproval.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="source-link"
              >
                Ver fuente <ExternalLink size={14} />
              </a>
            )}
          </div>

          <div
            style={{
              display: 'flex',
              gap: '10px',
              marginBottom: '20px',
              borderBottom: '1px solid rgba(255,255,255,0.1)',
              paddingBottom: '10px',
              flexWrap: 'wrap',
            }}
          >
            <button
              type="button"
              className={`btn ${selectedFormatSubTab === 'linkedin' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setSelectedFormatSubTab('linkedin')}
            >
              <Linkedin size={16} /> LinkedIn
            </button>
            <button
              type="button"
              className={`btn ${selectedFormatSubTab === 'video' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setSelectedFormatSubTab('video')}
            >
              <Video size={16} /> Video
            </button>
            <button
              type="button"
              className={`btn ${selectedFormatSubTab === 'carousel' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setSelectedFormatSubTab('carousel')}
            >
              <Layers size={16} /> Carrusel
            </button>
            <button
              type="button"
              className={`btn ${selectedFormatSubTab === 'newsletter' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setSelectedFormatSubTab('newsletter')}
            >
              <Mail size={16} /> Newsletter
            </button>
          </div>

          {multiFormatError && (
            <div
              className="glass-card"
              style={{
                padding: '16px',
                marginBottom: '16px',
                borderLeft: '4px solid #EF4444',
                color: 'var(--text-secondary)',
              }}
            >
              No se pudo generar: {multiFormatError}
              <div style={{ marginTop: '10px' }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => generateFormat(selectedFormatSubTab, true)}
                >
                  Reintentar
                </button>
              </div>
            </div>
          )}

          {renderStudioFormat(selectedFormatSubTab)}
        </section>
      )}
    </>
  );
}

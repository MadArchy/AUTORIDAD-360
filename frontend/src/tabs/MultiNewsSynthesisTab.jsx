import React, { useEffect, useState } from 'react';
import {
  Layers,
  Sparkles,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Wand2,
  FileText,
} from 'lucide-react';
import {
  runAutoPilotSynthesis,
  generateMultiNewsSynthesis,
  getMultiNewsHistory,
} from '../api';

const AUTHOR = 'Juan Vásquez';
const PROVIDER_KEY = 'a360_multi_synth_provider_mode';

export default function MultiNewsSynthesisTab() {
  const [loading, setLoading] = useState(false);
  const [improving, setImproving] = useState(false);
  const [phase, setPhase] = useState('');
  const [result, setResult] = useState(null);
  const [improveNote, setImproveNote] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [draftHtml, setDraftHtml] = useState('');
  const [draftTitle, setDraftTitle] = useState('');
  const [providerMode, setProviderMode] = useState(() => {
    try {
      const saved = localStorage.getItem(PROVIDER_KEY);
      return ['local', 'cloud', 'auto'].includes(saved) ? saved : 'auto';
    } catch {
      return 'auto';
    }
  });

  const changeProviderMode = (mode) => {
    setProviderMode(mode);
    try {
      localStorage.setItem(PROVIDER_KEY, mode);
    } catch {
      /* ignore */
    }
  };

  const applyResult = (payload) => {
    setResult(payload);
    setDraftTitle(payload?.title || '');
    setDraftHtml(payload?.content_html || '');
  };

  const loadLatest = async () => {
    try {
      const history = await getMultiNewsHistory();
      const latest = Array.isArray(history) && history.length ? history[0] : null;
      if (!latest?.content_html && !latest?.title) return;
      applyResult({
        synthesis_id: latest.id,
        blog_post_id: latest.blog_post_id,
        title: latest.title,
        slug: latest.slug,
        central_focus: latest.central_focus,
        content_html: latest.content_html || '',
        sources_count: latest.sources_count || latest.source_article_ids?.length || 0,
        selected_article_ids: latest.source_article_ids || [],
        status: latest.status || 'pending',
        auto_pilot: true,
      });
    } catch {
      /* sin historial aún */
    }
  };

  useEffect(() => {
    loadLatest();
  }, []);

  const deliverBest = async () => {
    setErrorMsg('');
    setLoading(true);
    setPhase('Eligiendo las mejores señales…');
    try {
      setPhase(
        providerMode === 'cloud'
          ? 'Definiendo tesis con tu API…'
          : providerMode === 'local'
            ? 'Definiendo tesis con IA local…'
            : 'Definiendo el foco único…'
      );
      const payload = await runAutoPilotSynthesis({
        author_name: AUTHOR,
        provider_mode: providerMode,
      });
      setPhase('Fusionando en un solo artículo…');
      applyResult(payload);
      setImproveNote('');
    } catch (err) {
      setErrorMsg(err.message || 'No se pudo generar la síntesis automática.');
    } finally {
      setLoading(false);
      setPhase('');
    }
  };

  const improveArticle = async () => {
    if (!result?.selected_article_ids?.length) {
      setErrorMsg('Primero genera el artículo consolidado.');
      return;
    }
    const note = improveNote.trim();
    const focusBase = result.central_focus || result.suggested_focus || '';
    const refinedFocus = note
      ? `${focusBase} Mejora pedida: ${note}`
      : (
        `${focusBase} Reescribe como UN solo ensayo fusionado con criterio Juan: ` +
        `tesis clara, hechos ancla entretejidos (sin digest por noticia), bloque ` +
        `"Mi perspectiva" contundente y acciones concretas. Tono profesional soberano.`
      );

    setErrorMsg('');
    setImproving(true);
    setPhase('Mejorando el artículo consolidado…');
    try {
      const payload = await generateMultiNewsSynthesis({
        article_ids: result.selected_article_ids,
        central_focus: refinedFocus,
        author_name: AUTHOR,
        provider_mode: providerMode,
      });
      applyResult({
        ...payload,
        selected_article_ids: result.selected_article_ids,
        auto_pilot: true,
      });
      setImproveNote('');
    } catch (err) {
      setErrorMsg(err.message || 'No se pudo mejorar el artículo.');
    } finally {
      setImproving(false);
      setPhase('');
    }
  };

  const busy = loading || improving;

  return (
    <section className="multi-synth glass-panel">
      <header className="page-header multi-synth__header">
        <div>
          <span className="page-eyebrow">Ensayo fusionado · criterio Juan</span>
          <h2 className="page-title">Un solo pensamiento, acreditado</h2>
          <p className="page-description">
            No es un resumen de cada noticia. El sistema elige señales, define una tesis
            y entrega un ensayo sólido con la perspectiva de Juan Vásquez.
          </p>
        </div>
        <div className="multi-synth__header-actions">
          <label className="multi-synth__provider">
            <span>Modelo</span>
            <select
              value={providerMode}
              disabled={busy}
              onChange={(e) => changeProviderMode(e.target.value)}
              className="form-control"
              title="Local = Ollama. API = clave en Inteligencia Artificial."
            >
              <option value="local">IA local (Ollama)</option>
              <option value="cloud">API web (tu key)</option>
              <option value="auto">Auto (local → API)</option>
            </select>
          </label>
          <button
            type="button"
            className="btn btn-primary"
            disabled={busy}
            onClick={deliverBest}
          >
            {loading ? (
              <RefreshCw size={16} className="animate-spin" aria-hidden="true" />
            ) : (
              <Sparkles size={16} aria-hidden="true" />
            )}
            {result ? 'Generar de nuevo' : 'Entregar mejor artículo'}
          </button>
        </div>
      </header>

      {errorMsg ? (
        <div className="status-banner status-banner--error" role="alert">
          <AlertCircle size={18} aria-hidden="true" />
          <div>
            <strong>No se completó la síntesis</strong>
            <p>{errorMsg}</p>
          </div>
        </div>
      ) : null}

      {busy ? (
        <div className="multi-synth__loading editorial-card" aria-busy="true">
          <RefreshCw size={22} className="animate-spin" aria-hidden="true" />
          <div>
            <strong>{phase || 'Trabajando…'}</strong>
            <p>Esto puede tomar un minuto según el motor de IA disponible.</p>
          </div>
        </div>
      ) : null}

      {!result && !busy ? (
        <div className="multi-synth__empty empty-state">
          <Layers size={28} aria-hidden="true" />
          <strong>Aún no hay artículo consolidado</strong>
          <span>
            Pulsa “Entregar mejor artículo” para recibir una sola pieza fusionada a partir
            del mejor foco detectado en el inventario.
          </span>
          <button type="button" className="btn btn-primary" onClick={deliverBest}>
            <Sparkles size={16} aria-hidden="true" />
            Entregar mejor artículo
          </button>
        </div>
      ) : null}

      {result ? (
        <article className="multi-synth__article editorial-card editorial-card--featured">
          <div className="multi-synth__meta">
            <span className="meta-chip meta-chip--stat">
              <FileText size={13} aria-hidden="true" />
              {result.sources_count || result.selected_article_ids?.length || 0} fuentes acreditadas
            </span>
            <span className="meta-chip">Criterio Juan Vásquez</span>
            <span className={`status-badge ${result.status === 'published' ? 'status-verified' : 'status-pending'}`}>
              {result.status === 'published' ? 'Publicado' : 'Pendiente de revisión'}
            </span>
          </div>

          <div className="multi-synth__focus">
            <span className="page-eyebrow">Tesis única</span>
            <p>{result.central_focus || result.suggested_focus}</p>
          </div>

          <label className="multi-synth__label" htmlFor="multi-synth-title">
            Título del ensayo
          </label>
          <input
            id="multi-synth-title"
            className="form-control"
            value={draftTitle}
            onChange={(e) => setDraftTitle(e.target.value)}
          />

          <label className="multi-synth__label" htmlFor="multi-synth-body">
            Ensayo fusionado
          </label>
          <div
            id="multi-synth-body"
            className="multi-synth__body multi-synth__body--essay"
            dangerouslySetInnerHTML={{ __html: draftHtml }}
          />

          <div className="multi-synth__improve">
            <div className="section-header">
              <div>
                <span className="section-eyebrow">Desarrollar</span>
                <h3 className="section-title">Mejorar este contenido</h3>
              </div>
            </div>
            <textarea
              className="form-control"
              rows={3}
              value={improveNote}
              onChange={(e) => setImproveNote(e.target.value)}
              placeholder="Ej.: más criterio legal, refuerza Mi perspectiva, menos hechos y más postura, acciones para GC…"
              disabled={busy}
            />
            <div className="multi-synth__actions">
              <button
                type="button"
                className="btn btn-primary"
                disabled={busy}
                onClick={improveArticle}
              >
                <Wand2 size={15} aria-hidden="true" />
                {improving ? 'Mejorando…' : 'Mejorar artículo'}
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                disabled={busy}
                onClick={deliverBest}
              >
                <RefreshCw size={15} aria-hidden="true" />
                Nuevo foco automático
              </button>
            </div>
            {result.slug ? (
              <p className="multi-synth__slug">
                <CheckCircle2 size={14} aria-hidden="true" />
                Borrador guardado · /blog/{result.slug}
              </p>
            ) : null}
          </div>
        </article>
      ) : null}
    </section>
  );
}

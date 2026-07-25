import React, { useCallback, useEffect, useState } from 'react';
import { BookOpen, CheckCircle2, Copy, ExternalLink, Image as ImageIcon, Send } from 'lucide-react';
import { api, getStoredUser } from '../api';
import { resolveMediaUrl } from './FormatPreview';

const PUBLIC_BLOG_URL =
  import.meta.env.VITE_PUBLIC_BLOG_URL || 'http://127.0.0.1:3002';
const PUBLIC_BLOG_POST_URL =
  import.meta.env.VITE_PUBLIC_BLOG_POST_URL ||
  `${PUBLIC_BLOG_URL.replace(/\/$/, '')}/blog/{slug}`;

function getPublicPostUrl(slug) {
  const encodedSlug = encodeURIComponent(slug);
  if (PUBLIC_BLOG_POST_URL.includes('{slug}')) {
    return PUBLIC_BLOG_POST_URL.replace('{slug}', encodedSlug);
  }
  return `${PUBLIC_BLOG_URL}/blog/${encodedSlug}`;
}

const SOCIAL_CHANNELS = ['linkedin', 'facebook', 'instagram'];

/**
 * Panel Distribuir: publicar pieza a redes + blog desde el Estudio.
 */
export default function StudioDistribute({
  pieceId,
  pieceStatus,
  articleId,
  pendingBlogPosts = [],
  publishedBlogPosts = [],
  editorialBlogPosts = [],
  onGenerateBlog,
  onApproveBlog,
  onPublishBlog,
  blogBusy = false,
  notify,
  onImagesGenerated,
  initialAssetIds = [],
  initialAssets = [],
}) {
  const [channels, setChannels] = useState(SOCIAL_CHANNELS);
  const [picked, setPicked] = useState(['linkedin']);
  const [pkg, setPkg] = useState(null);
  const [busy, setBusy] = useState(false);
  const [imgBusy, setImgBusy] = useState(false);
  const [accounts, setAccounts] = useState([]);
  const [assetIds, setAssetIds] = useState(initialAssetIds || []);
  const [assets, setAssets] = useState(initialAssets || []);

  useEffect(() => {
    setAssetIds(initialAssetIds || []);
    setAssets(initialAssets || []);
  }, [pieceId]);

  useEffect(() => {
    if (initialAssetIds?.length) setAssetIds(initialAssetIds);
    if (initialAssets?.length) setAssets(initialAssets);
  }, [initialAssetIds, initialAssets]);

  const loadLite = useCallback(async () => {
    try {
      const [ch, acc] = await Promise.all([
        api('/publish/channels'),
        api('/publish/accounts'),
      ]);
      const list = (ch.channels || []).map((c) => (typeof c === 'string' ? c : c.id || c.code)).filter(Boolean);
      const social = list.filter((c) => SOCIAL_CHANNELS.includes(c));
      if (social.length) setChannels(social);
      setAccounts(acc || []);
    } catch {
      /* keep defaults */
    }
  }, []);

  useEffect(() => {
    loadLite();
  }, [loadLite]);

  const toggle = (ch) => {
    setPicked((prev) => (prev.includes(ch) ? prev.filter((c) => c !== ch) : [...prev, ch]));
  };

  const generateCreatives = async () => {
    if (!pieceId) {
      notify?.('Genera el formato primero', 'warn');
      return;
    }
    setImgBusy(true);
    try {
      const data = await api(`/content/pieces/${pieceId}/generate-images`, {
        method: 'POST',
        body: JSON.stringify({ use_openai: true }),
      });
      setAssetIds(data?.asset_ids || []);
      setAssets(data?.assets || []);
      onImagesGenerated?.(data);
      notify?.(
        `Creatividades listas (${data?.engine === 'openai+brand' ? 'IA+marca' : 'marca'}): ${data?.asset_ids?.length || 0}`,
        'success'
      );
    } catch (e) {
      notify?.(e.message || 'No se pudieron generar las imágenes', 'error');
    } finally {
      setImgBusy(false);
    }
  };

  const createPackage = async () => {
    if (!pieceId) {
      notify?.('Genera y guarda el formato primero', 'warn');
      return;
    }
    if (pieceStatus !== 'approved') {
      notify?.('Aprueba la pieza antes de crear el paquete de publicación', 'warn');
      return;
    }
    if (!picked.length) {
      notify?.('Elige al menos un canal', 'warn');
      return;
    }
    setBusy(true);
    try {
      const created = await api('/publish/packages', {
        method: 'POST',
        body: JSON.stringify({
          source_type: 'content_piece',
          source_id: pieceId,
          channels: picked,
          media_asset_ids: assetIds.filter(Boolean),
        }),
      });
      setPkg(created);
      notify?.(
        assetIds.length
          ? `Paquete listo con ${assetIds.length} imagen(es)`
          : 'Paquete listo (sin imágenes; genera creatividades antes)',
        'success'
      );
    } catch (e) {
      notify?.(e.message || 'Error al crear paquete', 'error');
    } finally {
      setBusy(false);
    }
  };

  const confirmJob = async (jobId) => {
    setBusy(true);
    try {
      await api(`/publish/jobs/${jobId}/confirm`, {
        method: 'POST',
        body: JSON.stringify({ actor: getStoredUser()?.email || 'editor' }),
      });
      if (pkg?.id) setPkg(await api(`/publish/packages/${pkg.id}`));
      notify?.('Publicación asistida confirmada', 'success');
    } catch (e) {
      notify?.(e.message || 'No se pudo confirmar', 'error');
    } finally {
      setBusy(false);
    }
  };

  const executeJob = async (jobId) => {
    setBusy(true);
    try {
      await api(`/publish/jobs/${jobId}/execute`, {
        method: 'POST',
        body: JSON.stringify({ actor: getStoredUser()?.email || 'editor' }),
      });
      if (pkg?.id) setPkg(await api(`/publish/packages/${pkg.id}`));
      notify?.('Job ejecutado (nativo o dry-run)', 'success');
    } catch (e) {
      notify?.(e.message || 'No se pudo ejecutar', 'error');
    } finally {
      setBusy(false);
    }
  };

  const copyVariant = (text) => {
    navigator.clipboard.writeText(text || '');
    notify?.('Texto del canal copiado', 'success');
  };

  const articlePending = [
    ...(editorialBlogPosts || []),
    ...(pendingBlogPosts || []),
  ]
    .filter((p, i, arr) => arr.findIndex((x) => x.id === p.id) === i)
    .filter((p) => !articleId || Number(p.article_id) === Number(articleId));
  const articlePublished = (publishedBlogPosts || []).filter(
    (p) => !articleId || Number(p.article_id) === Number(articleId)
  );

  const plainPreview = (html) =>
    String(html || '')
      .replace(/<[^>]+>/g, ' ')
      .replace(/\s+/g, ' ')
      .trim()
      .slice(0, 420);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16, marginTop: 16 }}>
      <div className="glass-card" style={{ padding: 18 }}>
        <h4 style={{ margin: '0 0 8px', display: 'flex', alignItems: 'center', gap: 8 }}>
          <Send size={16} style={{ color: 'var(--accent-cyan)' }} /> Publicar en redes
        </h4>
        <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: 12 }}>
          Genera creatividades según el contenido, elige canales y crea el paquete. LinkedIn puede ir asistido (copiar) o nativo.
        </p>

        <div style={{ marginBottom: 12 }}>
          <button
            type="button"
            className="btn btn-secondary"
            disabled={imgBusy || !pieceId}
            onClick={generateCreatives}
            style={{ marginBottom: 10 }}
          >
            <ImageIcon size={14} style={{ marginRight: 6 }} />
            {imgBusy ? 'Generando creatividades…' : 'Generar creatividades de publicidad'}
          </button>
          {assets.length > 0 && (
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 8 }}>
              {assets.map((a) => {
                const src = resolveMediaUrl(a.storage_url);
                return (
                  <a
                    key={a.id || a.storage_url}
                    href={src}
                    target="_blank"
                    rel="noopener noreferrer"
                    title={a.title || 'Creatividad'}
                    style={{ display: 'block' }}
                  >
                    <img
                      src={src}
                      alt={a.title || 'Creatividad'}
                      style={{
                        width: 72,
                        height: 90,
                        objectFit: 'cover',
                        borderRadius: 8,
                        border: '1px solid rgba(255,255,255,0.15)',
                      }}
                    />
                  </a>
                );
              })}
            </div>
          )}
          {!assets.length && (
            <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', margin: '4px 0 0' }}>
              Sin imágenes aún. Genera creatividades antes de publicar para adjuntarlas al paquete.
            </p>
          )}
        </div>

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 12 }}>
          {channels.map((ch) => (
            <label key={ch} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.85rem' }}>
              <input type="checkbox" checked={picked.includes(ch)} onChange={() => toggle(ch)} />
              {ch}
            </label>
          ))}
        </div>
        {accounts.length === 0 && (
          <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: 10 }}>
            Sin cuentas conectadas: usarás modo asistido (copiar + confirmar).
          </p>
        )}
        <button
          type="button"
          className="btn btn-primary"
          disabled={busy || !pieceId}
          onClick={createPackage}
        >
          {busy ? 'Creando…' : 'Crear paquete de publicación'}
        </button>

        {pkg && (
          <div style={{ marginTop: 14, display: 'flex', flexDirection: 'column', gap: 10 }}>
            <strong style={{ fontSize: '0.9rem' }}>Paquete #{pkg.id}</strong>
            {(pkg.variants || []).map((v) => {
              const job = v.job;
              const mediaIds = v.media_asset_ids || v.media_asset_ids_json || [];
              return (
                <div
                  key={v.id}
                  style={{
                    padding: 12,
                    borderRadius: 8,
                    background: 'rgba(0,0,0,0.3)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 8,
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
                    <span style={{ fontSize: '0.85rem' }}>
                      <strong>{v.channel}</strong>
                      {job ? ` · ${job.status}` : ` · ${v.status || 'listo'}`}
                      {mediaIds.length ? ` · ${mediaIds.length} img` : ''}
                    </span>
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                      <button
                        type="button"
                        className="btn btn-secondary"
                        style={{ padding: '4px 8px', fontSize: '0.75rem' }}
                        onClick={() => copyVariant(v.body_text)}
                      >
                        <Copy size={12} /> Copiar
                      </button>
                      {job?.id && (
                        <>
                          <button
                            type="button"
                            className="btn btn-secondary"
                            style={{ padding: '4px 8px', fontSize: '0.75rem' }}
                            disabled={busy}
                            onClick={() => confirmJob(job.id)}
                          >
                            Confirmar asistido
                          </button>
                          <button
                            type="button"
                            className="btn btn-primary"
                            style={{ padding: '4px 8px', fontSize: '0.75rem' }}
                            disabled={busy}
                            onClick={() => executeJob(job.id)}
                          >
                            Ejecutar
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                  <pre
                    style={{
                      margin: 0,
                      whiteSpace: 'pre-wrap',
                      fontSize: '0.8rem',
                      color: 'var(--text-secondary)',
                      maxHeight: 100,
                      overflow: 'auto',
                    }}
                  >
                    {(v.body_text || '').slice(0, 500)}
                  </pre>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div className="glass-card" style={{ padding: 18 }}>
        <h4 style={{ margin: '0 0 8px', display: 'flex', alignItems: 'center', gap: 8 }}>
          <BookOpen size={16} style={{ color: 'var(--accent-emerald)' }} /> Artículo de blog
        </h4>
        <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: 12 }}>
          Genera un borrador, apruébalo y publícalo para exponerlo en el blog público ({PUBLIC_BLOG_URL}).
        </p>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
          <button
            type="button"
            className="btn btn-primary"
            disabled={!articleId || blogBusy}
            onClick={() => onGenerateBlog?.(articleId)}
          >
            {blogBusy ? 'Generando…' : 'Generar artículo de blog'}
          </button>
          <a
            className="btn btn-secondary"
            href={PUBLIC_BLOG_URL}
            target="_blank"
            rel="noopener noreferrer"
            style={{ textDecoration: 'none' }}
          >
            <ExternalLink size={14} /> Abrir blog
          </a>
        </div>

        {articlePending.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {articlePending.map((post) => (
              <div
                key={post.id}
                style={{
                  padding: 12,
                  borderRadius: 8,
                  background: 'rgba(0,0,0,0.25)',
                  border: '1px solid rgba(255,255,255,0.08)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, flexWrap: 'wrap' }}>
                  <strong style={{ fontSize: '0.9rem' }}>{post.title}</strong>
                  <span className={`status-badge status-${post.status === 'approved' ? 'verified' : 'pending'}`}>
                    {post.status}
                  </span>
                </div>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: '8px 0' }}>
                  {plainPreview(post.content_html || post.excerpt || '')}
                </p>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  {post.status === 'pending' && (
                    <button
                      type="button"
                      className="btn btn-secondary"
                      disabled={blogBusy}
                      onClick={() => onApproveBlog?.(post.id)}
                    >
                      <CheckCircle2 size={14} /> Aprobar
                    </button>
                  )}
                  {(post.status === 'approved' || post.status === 'pending') && (
                    <button
                      type="button"
                      className="btn btn-primary"
                      disabled={blogBusy}
                      onClick={() => onPublishBlog?.(post.id)}
                    >
                      Publicar y abrir
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {articlePublished.length > 0 && (
          <div style={{ marginTop: 12 }}>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: 8 }}>Publicados</p>
            {articlePublished.map((post) => (
              <div key={post.id} style={{ marginBottom: 8 }}>
                <a
                  href={getPublicPostUrl(post.slug)}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ fontSize: '0.85rem' }}
                >
                  {post.title}
                </a>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

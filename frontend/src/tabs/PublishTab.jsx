import React, { useCallback, useEffect, useState } from 'react';
import { CheckCircle2, Copy, Send } from 'lucide-react';
import { api, getStoredUser } from '../api';

const DEFAULT_CHANNELS = ['linkedin', 'facebook', 'instagram', 'blog'];

export default function PublishTab({ notify, publishedBlogPosts = [], goToTab }) {
  const [channels, setChannels] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [packages, setPackages] = useState([]);
  const [mediaAssets, setMediaAssets] = useState([]);
  const [pickedMedia, setPickedMedia] = useState([]);
  const [schedule, setSchedule] = useState(null);
  const [selected, setSelected] = useState(null);
  const [sourceType, setSourceType] = useState('blog_post');
  const [sourceId, setSourceId] = useState('');
  const [slotId, setSlotId] = useState('');
  const [pickedChannels, setPickedChannels] = useState(DEFAULT_CHANNELS);
  const [busy, setBusy] = useState(false);
  const [mediaTitle, setMediaTitle] = useState('');
  const [mediaUrl, setMediaUrl] = useState('');
  const [scheduleAt, setScheduleAt] = useState('');
  const [connectAccountId, setConnectAccountId] = useState('');
  const [connectToken, setConnectToken] = useState('');
  const [connectExternalId, setConnectExternalId] = useState('');
  const [ctaDrafts, setCtaDrafts] = useState({});

  const load = useCallback(async () => {
    try {
      const [ch, acc, pkgs, media, sched] = await Promise.all([
        api('/publish/channels'),
        api('/publish/accounts'),
        api('/publish/packages?limit=20'),
        api('/publish/media?limit=30'),
        api('/publish/schedule?days=14'),
      ]);
      setChannels(ch.channels || []);
      setAccounts(acc || []);
      setPackages(pkgs || []);
      setMediaAssets(media || []);
      setSchedule(sched || null);
    } catch (e) {
      notify?.(e.message || 'No se pudo cargar publicación');
    }
  }, [notify]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!selected?.variants) return;
    const next = {};
    for (const v of selected.variants) {
      next[v.id] = { cta_text: v.cta_text || '', cta_url: v.cta_url || '' };
    }
    setCtaDrafts(next);
  }, [selected?.id]);

  const saveVariantCta = async (variantId) => {
    const draft = ctaDrafts[variantId] || {};
    setBusy(true);
    try {
      await api(`/marketing/variants/${variantId}/cta`, {
        method: 'PATCH',
        body: JSON.stringify({
          cta_text: draft.cta_text || null,
          cta_url: draft.cta_url || null,
        }),
      });
      notify?.('CTA actualizado');
      if (selected?.id) {
        setSelected(await api(`/publish/packages/${selected.id}`));
      }
    } catch (e) {
      notify?.(e.message || 'Error al guardar CTA', 'error');
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    if (sourceType === 'blog_post' && publishedBlogPosts[0]?.id && !sourceId) {
      setSourceId(String(publishedBlogPosts[0].id));
    }
  }, [publishedBlogPosts, sourceType, sourceId]);

  const toggleChannel = (ch) => {
    setPickedChannels((prev) =>
      prev.includes(ch) ? prev.filter((c) => c !== ch) : [...prev, ch]
    );
  };

  const createPackage = async () => {
    const id = Number(sourceId);
    if (!id || pickedChannels.length === 0) {
      notify?.('Indica origen y al menos un canal');
      return;
    }
    setBusy(true);
    try {
      const pkg = await api('/publish/packages', {
        method: 'POST',
        body: JSON.stringify({
          source_type: sourceType,
          source_id: id,
          channels: pickedChannels,
          media_asset_ids: pickedMedia,
        }),
      });
      setSelected(pkg);
      await load();
      notify?.('Paquete multi-canal listo (modo asistido)');
    } catch (e) {
      notify?.(e.message || 'Error al crear paquete');
    } finally {
      setBusy(false);
    }
  };

  const createFromSlot = async () => {
    const id = Number(slotId);
    if (!id) {
      notify?.('Indica ID de slot de calendario');
      return;
    }
    setBusy(true);
    try {
      const pkg = await api(`/publish/from-slot/${id}`, {
        method: 'POST',
        body: JSON.stringify({
          channels: pickedChannels.length ? pickedChannels : null,
          media_asset_ids: pickedMedia,
        }),
      });
      setSelected(pkg);
      await load();
      notify?.(`Paquete creado desde slot #${id} (fecha del calendario)`);
    } catch (e) {
      notify?.(e.message || 'Error desde slot');
    } finally {
      setBusy(false);
    }
  };

  const registerMedia = async () => {
    if (!mediaTitle.trim() || !mediaUrl.trim()) {
      notify?.('Título y URL de media requeridos');
      return;
    }
    setBusy(true);
    try {
      const asset = await api('/publish/media', {
        method: 'POST',
        body: JSON.stringify({
          title: mediaTitle.trim(),
          storage_url: mediaUrl.trim(),
          kind: 'image',
        }),
      });
      setMediaTitle('');
      setMediaUrl('');
      setPickedMedia((prev) => [...prev, asset.id]);
      await load();
      notify?.('Asset de media registrado');
    } catch (e) {
      notify?.(e.message || 'Error al registrar media');
    } finally {
      setBusy(false);
    }
  };

  const scheduleJob = async (jobId) => {
    if (!scheduleAt) {
      notify?.('Elige fecha/hora de programación');
      return;
    }
    setBusy(true);
    try {
      await api(`/publish/jobs/${jobId}/schedule`, {
        method: 'POST',
        body: JSON.stringify({ scheduled_at: new Date(scheduleAt).toISOString() }),
      });
      if (selected?.id) {
        setSelected(await api(`/publish/packages/${selected.id}`));
      }
      await load();
      notify?.('Job programado');
    } catch (e) {
      notify?.(e.message || 'No se pudo programar');
    } finally {
      setBusy(false);
    }
  };

  const confirmJob = async (jobId) => {
    const actor = getStoredUser()?.email || 'editor';
    setBusy(true);
    try {
      await api(`/publish/jobs/${jobId}/confirm`, {
        method: 'POST',
        body: JSON.stringify({ actor }),
      });
      if (selected?.id) {
        const fresh = await api(`/publish/packages/${selected.id}`);
        setSelected(fresh);
      }
      await load();
      notify?.('Publicación confirmada');
    } catch (e) {
      notify?.(e.message || 'No se pudo confirmar');
    } finally {
      setBusy(false);
    }
  };

  const executeJob = async (jobId) => {
    const actor = getStoredUser()?.email || 'editor';
    setBusy(true);
    try {
      const result = await api(`/publish/jobs/${jobId}/execute`, {
        method: 'POST',
        body: JSON.stringify({ actor }),
      });
      if (selected?.id) {
        setSelected(await api(`/publish/packages/${selected.id}`));
      }
      await load();
      if (result.ok) {
        notify?.(`${result.mode}: ${result.message}`);
      } else {
        notify?.(result.message || 'Adaptador no aplicó; usa confirmar asistido', 'error');
      }
    } catch (e) {
      notify?.(e.message || 'Execute falló', 'error');
    } finally {
      setBusy(false);
    }
  };

  const connectAccount = async () => {
    const id = Number(connectAccountId);
    if (!id || !connectToken.trim()) {
      notify?.('Elige cuenta y pega access token');
      return;
    }
    setBusy(true);
    try {
      await api(`/publish/accounts/${id}/connect`, {
        method: 'POST',
        body: JSON.stringify({
          access_token: connectToken.trim(),
          external_account_id: connectExternalId.trim() || null,
          prefer_live: false,
        }),
      });
      setConnectToken('');
      await load();
      notify?.('Cuenta connected (token cifrado). Execute usa dry-run salvo PUBLISH_NATIVE_LIVE');
    } catch (e) {
      notify?.(e.message || 'No se pudo conectar', 'error');
    } finally {
      setBusy(false);
    }
  };

  const disconnectAccount = async (id) => {
    setBusy(true);
    try {
      await api(`/publish/accounts/${id}/disconnect`, { method: 'POST' });
      await load();
      notify?.('Cuenta en modo asistido');
    } catch (e) {
      notify?.(e.message || 'Disconnect falló', 'error');
    } finally {
      setBusy(false);
    }
  };

  const copyText = async (text) => {
    try {
      await navigator.clipboard.writeText(text || '');
      notify?.('Copiado al portapapeles');
    } catch {
      notify?.('No se pudo copiar');
    }
  };

  return (
    <section className="glass-panel" style={{ padding: 24 }}>
      <div className="flow-step-banner">
        <span>Paso 4 de 4 · Publicar</span>
        <button type="button" className="btn btn-primary" onClick={() => goToTab?.('hoy')}>
          Volver a Hoy
        </button>
      </div>
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ fontSize: '1.35rem', fontWeight: 800, marginBottom: 8 }}>
          Publicar en canales
        </h2>
        <p style={{ color: 'var(--text-secondary)', margin: 0, maxWidth: 640 }}>
          Crea el paquete, revisa el checklist de cada red y confirma la publicación.
        </p>
      </div>

      <div className="grid-cards" style={{ marginBottom: 24 }}>
        <article className="glass-card" style={{ padding: 20 }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: 12 }}>Nuevo paquete</h3>
          <label style={{ display: 'block', fontSize: '0.85rem', marginBottom: 6 }}>Origen</label>
          <select
            value={sourceType}
            onChange={(e) => {
              setSourceType(e.target.value);
              setSourceId('');
            }}
            style={{ width: '100%', marginBottom: 12 }}
          >
            <option value="blog_post">Post de blog</option>
            <option value="content_piece">Pieza de contenido</option>
          </select>
          {sourceType === 'blog_post' ? (
            <select
              value={sourceId}
              onChange={(e) => setSourceId(e.target.value)}
              style={{ width: '100%', marginBottom: 12 }}
            >
              <option value="">Selecciona post…</option>
              {publishedBlogPosts.map((p) => (
                <option key={p.id} value={p.id}>
                  #{p.id} — {p.title?.slice(0, 60)}
                </option>
              ))}
            </select>
          ) : (
            <input
              type="number"
              placeholder="ID de content_piece"
              value={sourceId}
              onChange={(e) => setSourceId(e.target.value)}
              style={{ width: '100%', marginBottom: 12 }}
            />
          )}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 14 }}>
            {(channels.length ? channels : DEFAULT_CHANNELS).map((ch) => (
              <label key={ch} style={{ fontSize: '0.85rem', display: 'flex', gap: 6, alignItems: 'center' }}>
                <input
                  type="checkbox"
                  checked={pickedChannels.includes(ch)}
                  onChange={() => toggleChannel(ch)}
                />
                {ch}
              </label>
            ))}
          </div>
          {mediaAssets.length > 0 && (
            <div style={{ marginBottom: 12 }}>
              <span style={{ fontSize: '0.8rem', display: 'block', marginBottom: 6 }}>Media a adjuntar</span>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {mediaAssets.slice(0, 8).map((m) => (
                  <label key={m.id} style={{ fontSize: '0.8rem', display: 'flex', gap: 4, alignItems: 'center' }}>
                    <input
                      type="checkbox"
                      checked={pickedMedia.includes(m.id)}
                      onChange={() =>
                        setPickedMedia((prev) =>
                          prev.includes(m.id) ? prev.filter((x) => x !== m.id) : [...prev, m.id]
                        )
                      }
                    />
                    #{m.id} {m.title?.slice(0, 24)}
                  </label>
                ))}
              </div>
            </div>
          )}
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
            <button type="button" className="btn btn-primary" disabled={busy} onClick={createPackage}>
              <Send size={14} /> Crear paquete
            </button>
          </div>
          <label style={{ display: 'block', fontSize: '0.85rem', marginBottom: 6 }}>
            O desde slot de calendario
          </label>
          <div style={{ display: 'flex', gap: 8 }}>
            <input
              type="number"
              placeholder="ID slot"
              value={slotId}
              onChange={(e) => setSlotId(e.target.value)}
              style={{ flex: 1 }}
            />
            <button type="button" className="btn btn-secondary" disabled={busy} onClick={createFromSlot}>
              Desde slot
            </button>
          </div>
        </article>

        <article className="glass-card" style={{ padding: 20 }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: 12 }}>Media (URL)</h3>
          <input
            placeholder="Título"
            value={mediaTitle}
            onChange={(e) => setMediaTitle(e.target.value)}
            style={{ width: '100%', marginBottom: 8 }}
          />
          <input
            placeholder="https://… o /media/…"
            value={mediaUrl}
            onChange={(e) => setMediaUrl(e.target.value)}
            style={{ width: '100%', marginBottom: 12 }}
          />
          <button type="button" className="btn btn-secondary" disabled={busy} onClick={registerMedia}>
            Registrar asset
          </button>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: 12 }}>
            Cuentas: {accounts.length || 0} · Paquetes: {packages.length || 0} · Media: {mediaAssets.length || 0}
          </p>
          <label style={{ display: 'block', fontSize: '0.85rem', margin: '14px 0 6px' }}>
            Programar job seleccionado
          </label>
          <input
            type="datetime-local"
            value={scheduleAt}
            onChange={(e) => setScheduleAt(e.target.value)}
            style={{ width: '100%', marginBottom: 8 }}
          />
          <details className="publish-accounts-fold" style={{ marginTop: 14 }}>
            <summary style={{ cursor: 'pointer', fontWeight: 700, fontSize: '0.9rem' }}>
              Cuentas (conectar API)
            </summary>
            <div style={{ marginTop: 10 }}>
              <select
                value={connectAccountId}
                onChange={(e) => setConnectAccountId(e.target.value)}
                style={{ width: '100%', marginBottom: 8 }}
              >
                <option value="">Cuenta…</option>
                {accounts.map((a) => (
                  <option key={a.id} value={a.id}>
                    #{a.id} {a.channel} · {a.status}
                    {a.native_ready ? ' · ready' : ''}
                  </option>
                ))}
              </select>
              <input
                placeholder="Access token (se cifra)"
                value={connectToken}
                onChange={(e) => setConnectToken(e.target.value)}
                style={{ width: '100%', marginBottom: 8 }}
              />
              <input
                placeholder="external_account_id (urn LinkedIn / page id)"
                value={connectExternalId}
                onChange={(e) => setConnectExternalId(e.target.value)}
                style={{ width: '100%', marginBottom: 8 }}
              />
              <button type="button" className="btn btn-secondary" disabled={busy} onClick={connectAccount}>
                Conectar cuenta
              </button>
              <ul style={{ fontSize: '0.75rem', marginTop: 10, paddingLeft: 16, color: 'var(--text-secondary)' }}>
                {accounts
                  .filter((a) => a.status === 'connected')
                  .map((a) => (
                    <li key={`c-${a.id}`} style={{ marginBottom: 4 }}>
                      {a.channel} connected{' '}
                      <button
                        type="button"
                        className="btn btn-secondary"
                        style={{ padding: '2px 6px', fontSize: '0.7rem' }}
                        onClick={() => disconnectAccount(a.id)}
                      >
                        Desconectar
                      </button>
                    </li>
                  ))}
              </ul>
            </div>
          </details>
        </article>
      </div>

      {schedule && (
        <div className="glass-card" style={{ padding: 16, marginBottom: 20 }}>
          <h3 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: 8 }}>
            Calendario unificado (14 días)
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <div>
              <strong style={{ fontSize: '0.8rem' }}>Slots editoriales</strong>
              <ul style={{ margin: '8px 0 0', paddingLeft: 18, fontSize: '0.8rem' }}>
                {(schedule.calendar_slots || []).slice(0, 8).map((s) => (
                  <li key={`s-${s.id}`}>
                    #{s.id} · {s.format_type} · {s.status} · {s.scheduled_at?.slice(0, 16)}
                  </li>
                ))}
                {(schedule.calendar_slots || []).length === 0 && <li>Sin slots en ventana</li>}
              </ul>
            </div>
            <div>
              <strong style={{ fontSize: '0.8rem' }}>Publish jobs</strong>
              <ul style={{ margin: '8px 0 0', paddingLeft: 18, fontSize: '0.8rem' }}>
                {(schedule.publish_jobs || []).slice(0, 8).map((j) => (
                  <li key={`j-${j.id}`}>
                    #{j.id} · {j.channel} · {j.status} · {j.scheduled_at?.slice(0, 16)}
                    {j.calendar_slot_id ? ` · slot ${j.calendar_slot_id}` : ''}
                  </li>
                ))}
                {(schedule.publish_jobs || []).length === 0 && <li>Sin jobs programados</li>}
              </ul>
            </div>
          </div>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(200px, 280px) 1fr', gap: 16 }}>
        <aside>
          <h3 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: 10 }}>Recientes</h3>
          <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
            {packages.map((p) => (
              <li key={p.id} style={{ marginBottom: 6 }}>
                <button
                  type="button"
                  className={`btn ${selected?.id === p.id ? 'btn-primary' : 'btn-secondary'}`}
                  style={{ width: '100%', textAlign: 'left', fontSize: '0.8rem' }}
                  onClick={async () => {
                    try {
                      setSelected(await api(`/publish/packages/${p.id}`));
                    } catch (e) {
                      notify?.(e.message);
                    }
                  }}
                >
                  #{p.id} · {p.status} · {p.source_type}
                </button>
              </li>
            ))}
            {packages.length === 0 && (
              <li style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>Sin paquetes aún</li>
            )}
          </ul>
        </aside>

        <div>
          {!selected && (
            <p style={{ color: 'var(--text-secondary)' }}>
              Crea o selecciona un paquete para ver variantes y jobs por canal.
            </p>
          )}
          {selected && (
            <>
              <h3 style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: 8 }}>
                Paquete #{selected.id} — {selected.title || selected.source_type}
              </h3>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: 16 }}>
                Estado: {selected.status}
                {selected.brief?.calendar_slot_id
                  ? ` · slot #${selected.brief.calendar_slot_id}`
                  : ''}
              </p>
              {(selected.variants || []).map((v) => {
                const checklist = v.payload?.assisted_checklist || [];
                const job = v.job;
                const copyBody = v.body_text || v.headline || '';
                return (
                  <article key={v.id} className="glass-card" style={{ padding: 16, marginBottom: 12 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, flexWrap: 'wrap' }}>
                      <strong style={{ textTransform: 'uppercase', fontSize: '0.85rem' }}>{v.channel}</strong>
                      <button
                        type="button"
                        className="btn btn-secondary"
                        style={{ padding: '4px 8px', fontSize: '0.75rem' }}
                        onClick={() => copyText(copyBody)}
                      >
                        <Copy size={12} /> Copiar
                      </button>
                    </div>
                    {v.headline && (
                      <p style={{ fontWeight: 600, margin: '8px 0 4px' }}>{v.headline}</p>
                    )}
                    <pre
                      style={{
                        whiteSpace: 'pre-wrap',
                        fontSize: '0.85rem',
                        margin: '8px 0',
                        color: 'var(--text-secondary)',
                        fontFamily: 'inherit',
                      }}
                    >
                      {copyBody || '—'}
                    </pre>
                    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 8, alignItems: 'flex-end' }}>
                      <input
                        type="text"
                        placeholder="CTA texto"
                        value={ctaDrafts[v.id]?.cta_text ?? v.cta_text ?? ''}
                        onChange={(e) =>
                          setCtaDrafts((prev) => ({
                            ...prev,
                            [v.id]: { ...(prev[v.id] || {}), cta_text: e.target.value },
                          }))
                        }
                        style={{
                          flex: 1,
                          minWidth: 140,
                          padding: '8px 10px',
                          borderRadius: 8,
                          background: 'rgba(0,0,0,0.25)',
                          color: '#fff',
                          border: '1px solid rgba(255,255,255,0.1)',
                        }}
                      />
                      <input
                        type="url"
                        placeholder="CTA URL (con UTM)"
                        value={ctaDrafts[v.id]?.cta_url ?? v.cta_url ?? ''}
                        onChange={(e) =>
                          setCtaDrafts((prev) => ({
                            ...prev,
                            [v.id]: { ...(prev[v.id] || {}), cta_url: e.target.value },
                          }))
                        }
                        style={{
                          flex: 2,
                          minWidth: 180,
                          padding: '8px 10px',
                          borderRadius: 8,
                          background: 'rgba(0,0,0,0.25)',
                          color: '#fff',
                          border: '1px solid rgba(255,255,255,0.1)',
                        }}
                      />
                      <button
                        type="button"
                        className="btn btn-secondary"
                        style={{ padding: '6px 10px', fontSize: '0.75rem' }}
                        disabled={busy}
                        onClick={() => saveVariantCta(v.id)}
                      >
                        Guardar CTA
                      </button>
                    </div>
                    {Array.isArray(v.media_asset_ids) && v.media_asset_ids.length > 0 && (
                      <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                        Media: {v.media_asset_ids.join(', ')}
                      </p>
                    )}
                    {checklist.length > 0 && (
                      <ul style={{ fontSize: '0.8rem', margin: '8px 0', paddingLeft: 18 }}>
                        {checklist.map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    )}
                    {job && (
                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          gap: 12,
                          marginTop: 10,
                          paddingTop: 10,
                          borderTop: '1px solid var(--border, #e5e5e5)',
                          flexWrap: 'wrap',
                        }}
                      >
                        <span style={{ fontSize: '0.9rem' }}>
                          Job #{job.id} · <strong>{job.status}</strong>
                          {job.scheduled_at ? ` · ${job.scheduled_at.slice(0, 16)}` : ''}
                        </span>
                        <div style={{ display: 'flex', gap: 8 }}>
                          {job.status !== 'published' && (
                            <button
                              type="button"
                              className="btn btn-secondary"
                              disabled={busy}
                              onClick={() => scheduleJob(job.id)}
                            >
                              Programar
                            </button>
                          )}
                          {job.status !== 'published' && (
                            <button
                              type="button"
                              className="btn btn-secondary"
                              disabled={busy}
                              onClick={() => executeJob(job.id)}
                            >
                              Execute nativo
                            </button>
                          )}
                          {job.status !== 'published' && (
                            <button
                              type="button"
                              className="btn btn-primary"
                              disabled={busy}
                              onClick={() => confirmJob(job.id)}
                            >
                              <CheckCircle2 size={14} /> Confirmar publicado
                            </button>
                          )}
                        </div>
                      </div>
                    )}
                  </article>
                );
              })}
            </>
          )}
        </div>
      </div>
    </section>
  );
}
